#!/usr/bin/env bash
# Characterize the foundry gf180mcu_fd_io__bi_t across the spec PVT set (comparison anchor).
#   sim/gpio-bi_t/run.sh                       cold start: 48 requests x 15 corners -> `klt sim`
#                                              batch fleet; writes records/<UTC stamp>/
#   sim/gpio-bi_t/run.sh --resume RECORD_DIR   finish an interrupted or fleet-refused run: resubmit only
#                                              the requests without a report.json, then collect
#   sim/gpio-bi_t/run.sh --dry-run             translate, generate, `klt sim --dry-run` each request
#   sim/gpio-bi_t/run.sh --negative KIND       negative control, must exit non-zero. KIND is one of
#                                              bad-include | bad-model-path | bad-load | bad-measure
#                                              1 = failed as it must; 3 = did not fail (the control
#                                              failed); 2 = usage or environment error
# The grid is never run by looping ngspice here: it is a `klt sim` request set, which goes to the
# Spot fleet. Only the single-corner negative controls run locally (--backend local). If the batch
# submit fails the run fails and says so; there is no local fallback.
# Exit 0 only if the env check passes, the cell translates and matches the PDK's own spice netlist,
# and every PVT point of every request has every measurement present and finite.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIM="$(dirname "$HERE")"
REPO="$(dirname "$SIM")"
MODE=run; KIND=""
case "${1:-}" in
  "") ;;
  --dry-run) MODE=dry ;;
  --resume) MODE=resume; RESUME_DIR="${2:-}"
            [ -d "$RESUME_DIR/requests" ] || { echo "bi_t: usage: --resume needs an existing record dir" >&2; exit 2; } ;;
  --negative) MODE=neg; KIND="${2:-}" ;;
  *) echo "usage: run.sh [--dry-run | --negative bad-include|bad-model-path|bad-load|bad-measure]" >&2; exit 2 ;;
esac

ENVOUT="$("$SIM/check_env.sh")" || { echo "$ENVOUT"; exit 2; }
eval "$(printf '%s\n' "$ENVOUT" | sed "s/^\([A-Z_]*\)=\(.*\)$/\1='\2'/")"
REF="$(dirname "$(dirname "$PDK_MODELDIR")")/libs.ref/gf180mcu_fd_io"
CDL="$REF/cdl/gf180mcu_fd_io.cdl"; SPICE="$REF/spice/gf180mcu_fd_io.spice"
for f in "$CDL" "$SPICE"; do [ -f "$f" ] || { echo "bi_t: FAIL: missing $f" >&2; exit 2; }; done

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
if [ "$MODE" = run ]; then OUT="$HERE/records/$STAMP"; mkdir -p "$OUT"
elif [ "$MODE" = resume ]; then OUT="$(cd "$RESUME_DIR" && pwd)"; STAMP="$(sed -n 's/^date_utc=//p' "$OUT/record.txt")"
else OUT="$(mktemp -d)"; fi
REQ="$OUT/requests"; KLTOUT="$OUT/klt"; mkdir -p "$REQ" "$KLTOUT"

if [ "$MODE" != resume ]; then
python3 -I "$HERE/cdl2ngspice.py" "$CDL" gf180mcu_fd_io__bi_t --check-against "$SPICE" > "$OUT/bi_t.sp" \
  || { echo "bi_t: FAIL: CDL translation or cross-check failed" >&2; exit 1; }
fi

if [ "$MODE" = neg ]; then
  python3 -I "$HERE/gen_requests.py" "$REQ" "$PDK_MODELDIR" "$OUT/bi_t.sp" --probe "$KIND" >/dev/null \
    || { echo "bi_t: usage: unknown negative-control kind '$KIND'" >&2; exit 2; }
  klt sim --backend local --format json --report-out "$OUT/probe-report.json" "$REQ/probe.json" \
    > "$OUT/probe.stdout" 2> "$OUT/probe.stderr"; RC=$?
  python3 -I "$HERE/collect.py" --probe "$OUT/probe-report.json"; CRC=$?
  if [ "$RC" -ne 0 ] || [ "$CRC" -ne 0 ]; then
    echo "bi_t: negative control $KIND failed as it must (klt rc=$RC, collect rc=$CRC)" >&2; exit 1
  fi
  echo "bi_t: NEGATIVE CONTROL $KIND DID NOT FAIL" >&2; exit 3
fi

if [ "$MODE" != resume ]; then
python3 -I "$HERE/gen_requests.py" "$REQ" "$PDK_MODELDIR" "$OUT/bi_t.sp" > "$OUT/requests.list" \
  || { echo "bi_t: FAIL: request generation" >&2; exit 1; }
fi

if [ "$MODE" = dry ]; then
  STATUS=0
  while read -r stem; do
    klt sim --dry-run "$REQ/$stem.json" > "$OUT/dry-$stem.log" 2>&1 \
      || { echo "bi_t: FAIL: dry-run $stem (see $OUT/dry-$stem.log)" >&2; STATUS=1; }
  done < "$OUT/requests.list"
  [ "$STATUS" = 0 ] && echo "bi_t: dry-run OK: $(wc -l < "$OUT/requests.list") requests valid ($OUT)"
  exit $STATUS
fi

mapfile -t FILES < <(sed "s|^|$REQ/|; s|\$|.json|" "$OUT/requests.list")
if [ "$MODE" = resume ]; then
  TODO=(); for f in "${FILES[@]}"; do stem="$(basename "$f" .json)"
    [ -f "$KLTOUT/$stem/report.json" ] || TODO+=("$f"); done
  FILES=("${TODO[@]}"); echo "bi_t: resuming ${#FILES[@]} request(s) without a report"
fi
# --batch-set is batch-only by construction: a refused or failed submit is an error entry, never a
# local re-run. Exit 3/4 (measure failed / request errored) is reported by collect.py below.
SUFFIX=""; [ "$MODE" = resume ] && SUFFIX=".resume-$(date -u +%H%M%S)"
SETRC=0
if [ "${#FILES[@]}" -gt 0 ]; then
klt sim --batch-set "${FILES[@]}" --max-in-flight 4 --capacity-retries 3 \
  -o "$KLTOUT" --format json > "$OUT/set-report$SUFFIX.json" 2> "$OUT/klt-sim$SUFFIX.stderr"
SETRC=$?
fi
if [ "$SETRC" -ne 0 ]; then
  echo "bi_t: batch set exited $SETRC (see $OUT/klt-sim.stderr, $OUT/set-report.json); not falling back to local" >&2
fi

{ echo "- date (UTC): $STAMP$([ "$MODE" = resume ] && echo " (completed by --resume: requests refused for fleet capacity were resubmitted; see set-report.resume-*.json)")"
  echo "- open_pdks revision (pinned, sim/toolchain.json): \`$OPEN_PDKS\`, variant \`$VARIANT\`"
  echo "- ngspice on the submitting host: \`$NGSPICE_VERSION\` (the fleet's own is per job below)"
  echo "- klt: \`$(klt --version 2>&1 | head -1)\`; backend: batch (\`klt sim --batch-set\`)"
  echo "- repo commit: \`$(git -C "$REPO" rev-parse HEAD 2>/dev/null)\`"
  echo "- cell netlist: \`bi_t.sp\`, translated from the pinned CDL by cdl2ngspice.py and cross-checked"
  echo "  device by device against the PDK's own spice netlist"
  echo "- models staged with each job (\`stage_model_inputs\`): the pinned revision's sm141064.ngspice"
} > "$OUT/meta.txt"

python3 -I "$HERE/collect.py" "$OUT" "$KLTOUT" "$REPO/spec/io-ring.md" "$OUT/meta.txt"; CRC=$?
{ echo "date_utc=$STAMP"; echo "open_pdks=$OPEN_PDKS"; echo "variant=$VARIANT"
  echo "ngspice=$NGSPICE_VERSION"; echo "batch_set_rc=$SETRC"
  echo "result=$([ "$CRC" = 0 ] && [ "$SETRC" = 0 ] && echo PASS || echo FAIL)"; } > "$OUT/record.txt"
if [ "$CRC" -ne 0 ] || [ "$SETRC" -ne 0 ]; then echo "bi_t: FAIL (record kept: $OUT)" >&2; exit 1; fi
echo "record: $OUT"; echo "bi_t: PASS"
