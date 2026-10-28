#!/usr/bin/env bash
# Verify the drawn GPIO cell (design/gpio.spice) against the ratified spec rows over the PVT set.
#   sim/gpio-corners/run.sh             cold start: 20 requests -> `klt sim` batch fleet; writes records/<UTC stamp>/
#   sim/gpio-corners/run.sh --dry-run   generate and `klt sim --dry-run` each request; no simulation
#   sim/gpio-corners/run.sh --resume RECORD_DIR   resubmit only the requests without a report, then collect
#   sim/gpio-corners/run.sh --probe     local single-corner debug probe of every deck (typical, 25 C)
# The grid is never run by looping ngspice here: each request is a `klt sim` corner matrix that the
# batch backend sends to the Spot fleet, submitted one at a time. If a submit fails the run fails and
# says so; there is no local fallback (only --probe, one corner per deck, runs locally).
# KLT_CLIENT: command that runs a klt the fleet runner accepts. The runner image is klt 0.8.0, so
# the default is a throwaway uvx env pinned to the same version, never the host-wide klt.
# Exit 0 only if the env check passes and every request has every corner and measurement finite.
# A spec row that misses its target does not fail the run: it is the result (see collect.py).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIM="$(dirname "$HERE")"
REPO="$(dirname "$SIM")"
KLT_CLIENT="${KLT_CLIENT:-uvx --from klayout-tools==0.8.0 klt}"
MODE=run
case "${1:-}" in
  "") ;;
  --dry-run) MODE=dry ;;
  --probe) MODE=probe ;;
  --resume) MODE=resume; RESUME_DIR="${2:-}"
            [ -d "$RESUME_DIR/requests" ] || { echo "gpio-corners: usage: --resume needs an existing record dir" >&2; exit 2; } ;;
  *) echo "usage: run.sh [--dry-run | --probe | --resume RECORD_DIR]" >&2; exit 2 ;;
esac

ENVOUT="$("$SIM/check_env.sh")" || { echo "$ENVOUT"; exit 2; }
eval "$(printf '%s\n' "$ENVOUT" | sed "s/^\([A-Z_]*\)=\(.*\)$/\1='\2'/")"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
if [ "$MODE" = run ]; then OUT="$HERE/records/$STAMP"; mkdir -p "$OUT"
elif [ "$MODE" = resume ]; then OUT="$(cd "$RESUME_DIR" && pwd)"; STAMP="$(sed -n 's/^date_utc=//p' "$OUT/record.txt")"
else OUT="$(mktemp -d)"; fi
REQ="$OUT/requests"; KLTOUT="$OUT/klt"; mkdir -p "$REQ" "$KLTOUT"

if [ "$MODE" != resume ]; then
  EXTRA=""; [ "$MODE" = probe ] && EXTRA="--probe"
  python3 -I "$HERE/gen_requests.py" "$REQ" "$PDK_MODELDIR" "$REPO/design" $EXTRA > "$OUT/requests.list" \
    || { echo "gpio-corners: FAIL: request generation" >&2; exit 1; }
fi

if [ "$MODE" = dry ]; then
  STATUS=0
  while read -r stem; do
    klt sim --dry-run "$REQ/$stem.json" > "$OUT/dry-$stem.log" 2>&1 \
      || { echo "gpio-corners: FAIL: dry-run $stem (see $OUT/dry-$stem.log)" >&2; STATUS=1; }
  done < "$OUT/requests.list"
  [ "$STATUS" = 0 ] && echo "gpio-corners: dry-run OK: $(wc -l < "$OUT/requests.list") requests valid ($OUT)"
  exit $STATUS
fi

if [ "$MODE" = probe ]; then
  while read -r stem; do
    klt sim --backend local --format json "$REQ/$stem.json" > "$KLTOUT/$stem.json" 2> "$OUT/$stem.stderr"
    echo "probe $stem: klt rc=$?"
  done < "$OUT/requests.list"
  echo "gpio-corners: probe reports in $KLTOUT"; exit 0
fi

SUBRC=0
while read -r stem; do
  [ -s "$KLTOUT/$stem.json" ] && python3 -I -c "import json,sys; json.load(open(sys.argv[1]))" "$KLTOUT/$stem.json" 2>/dev/null && continue
  # rc 0 pass, 4 = the corner matrix has a failing or errored unit; the envelope is on stdout either way.
  $KLT_CLIENT sim --backend batch --format json "$REQ/$stem.json" > "$KLTOUT/$stem.json" 2> "$OUT/klt-sim-$stem.stderr"
  RC=$?
  echo "gpio-corners: $stem: klt rc=$RC"
  case "$RC" in 0|3|4) ;; *) SUBRC=1; echo "gpio-corners: submit failed for $stem (see $OUT/klt-sim-$stem.stderr); not falling back to local" >&2 ;; esac
done < "$OUT/requests.list"

{ echo "- date (UTC): $STAMP"
  echo "- open_pdks revision (pinned, sim/toolchain.json): \`$OPEN_PDKS\`, variant \`$VARIANT\`"
  echo "- ngspice on the submitting host: \`$NGSPICE_VERSION\` (the fleet's own is per request below)"
  echo "- klt client: \`$($KLT_CLIENT --version 2>&1 | tail -1)\`; backend: batch (one \`klt sim\` request at a time)"
  echo "- repo commit: \`$(git -C "$REPO" rev-parse HEAD 2>/dev/null)\`; DUT: \`design/gpio.spice\`, \`design/dvdd_pad.spice\`"
  echo "- models staged with each job (\`stage_model_inputs\`): the pinned revision's sm141064.ngspice"
} > "$OUT/meta.txt"

python3 -I "$HERE/collect.py" "$OUT" "$REPO/spec/io-ring.md" "$OUT/meta.txt"; CRC=$?
{ echo "date_utc=$STAMP"; echo "open_pdks=$OPEN_PDKS"; echo "variant=$VARIANT"
  echo "ngspice=$NGSPICE_VERSION"; echo "submit_rc=$SUBRC"
  echo "result=$([ "$CRC" = 0 ] && [ "$SUBRC" = 0 ] && echo PASS || echo FAIL)"; } > "$OUT/record.txt"
if [ "$CRC" -ne 0 ] || [ "$SUBRC" -ne 0 ]; then echo "gpio-corners: FAIL (record kept: $OUT)" >&2; exit 1; fi
echo "record: $OUT"; echo "gpio-corners: PASS (run complete; rows that miss their target are listed in record.md)"
