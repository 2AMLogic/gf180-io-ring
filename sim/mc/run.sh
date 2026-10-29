#!/usr/bin/env bash
# Monte Carlo campaign for the own-design GPIO: input thresholds, hysteresis, pull-up/pull-down,
# VOL/VOH (spec/io-ring.md, GPIO electrical targets) -> `klt yield` evidence for T1 item 6.
#   sim/mc/run.sh                       cold start: 22 `klt sim` Monte Carlo requests (300 samples each)
#                                       on the batch fleet, the seeded known-bad variants, a repeat run,
#                                       then `klt yield`; writes records/<UTC stamp>/
#   sim/mc/run.sh --resume RECORD_DIR   resubmit only the requests without a report, then collect
#   sim/mc/run.sh --dry-run             generate, `klt sim --dry-run` each request, check seed determinism
#   sim/mc/run.sh --negative KIND       negative control, must exit non-zero. KIND: rx | pull | nostat
# Two klt installs are needed (see README.md): KLT_SIM must match the fleet runner's klt version
# (the runner image is klt 0.8.0, so it defaults to a throwaway uvx env pinned to it) and KLT_YIELD
# must carry the klt_yield_native extension (defaults to `klt`). The grid is never run by looping
# ngspice here: every request goes to the Spot fleet with `--backend batch`. If a submit fails the run
# fails and says so; there is no local fallback.
# Exit 0: data valid and every row meets its target yield. Exit 3: data valid, a row misses its limit
# (the record says which; the spec is not relaxed). Exit 1: invalid data or a harness failure.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIM="$(dirname "$HERE")"
REPO="$(dirname "$SIM")"
KLT_SIM="${KLT_SIM:-uvx --from klayout-tools==0.8.0 klt}"; KLT_YIELD="${KLT_YIELD:-klt}"
MODE=run; KIND=""
case "${1:-}" in
  "") ;;
  --dry-run) MODE=dry ;;
  --resume) MODE=resume; RESUME_DIR="${2:-}"
            [ -d "$RESUME_DIR/requests" ] || { echo "mc: usage: --resume needs an existing record dir" >&2; exit 2; } ;;
  --negative) MODE=neg; KIND="${2:-}"
              case "$KIND" in rx|pull|nostat) ;; *) echo "mc: usage: --negative rx|pull|nostat" >&2; exit 2 ;; esac ;;
  *) echo "usage: run.sh [--dry-run | --resume DIR | --negative rx|pull|nostat]" >&2; exit 2 ;;
esac

ENVOUT="$("$SIM/check_env.sh")" || { echo "$ENVOUT"; exit 2; }
eval "$(printf '%s\n' "$ENVOUT" | sed "s/^\([A-Z_]*\)=\(.*\)$/\1='\2'/")"
GPIO="$REPO/design/gpio.spice"
[ -f "$GPIO" ] || { echo "mc: FAIL: missing $GPIO" >&2; exit 2; }
if [ "$MODE" != dry ]; then
  printf '%s' '{"measurements":[{"name":"x","samples":[1,2,3],"limits":{"min":0,"max":9}}]}' > "${TMPDIR:-/tmp}/mc-probe-$$.json"
  $KLT_YIELD yield "${TMPDIR:-/tmp}/mc-probe-$$.json" --format json >/dev/null 2>&1 \
    || { rm -f "${TMPDIR:-/tmp}/mc-probe-$$.json"; echo "mc: FAIL: KLT_YIELD ('$KLT_YIELD') cannot run klt yield (klt_yield_native missing?)" >&2; exit 2; }
  rm -f "${TMPDIR:-/tmp}/mc-probe-$$.json"
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
if [ "$MODE" = run ]; then OUT="$HERE/records/$STAMP"; mkdir -p "$OUT"
elif [ "$MODE" = resume ]; then OUT="$(cd "$RESUME_DIR" && pwd)"; STAMP="$(sed -n 's/^date_utc=//p' "$OUT/record.txt")"
else OUT="$(mktemp -d)"; fi

gen() {  # gen DIR [generator flags]: write requests, print the stems
  local d="$1"; shift
  python3 -I "$HERE/gen_requests.py" "$d" "$PDK_MODELDIR" "$GPIO" "$@"
}

submit() {  # submit REQDIR STEM REPORT: one request to the fleet, report to REPORT
  local rc try
  [ -s "$3" ] && python3 -I -c "import json,sys; json.load(open(sys.argv[1]))" "$3" 2>/dev/null && return 0
  # without --wait-for-capacity: a launch refused at the fleet's instance cap
  # (BATCH_MAX_CONCURRENT_INSTANCES) is retried with a fixed backoff, up to 60 tries; nothing runs locally
  for try in $(seq 1 60); do
    (cd "$1" && $KLT_SIM sim "$2.json" --backend batch --format json -o "$OUT/art/$2" > "$3" 2> "${3%.json}.stderr"); rc=$?
    if [ "$rc" != 0 ] && [ "$rc" != 3 ] && grep -q "exceeds BATCH_MAX_CONCURRENT_INSTANCES" "$3" "${3%.json}.stderr" 2>/dev/null; then
      sleep 60; continue
    fi
    break
  done
  case "$rc" in 0|3) ;; *) echo "mc: batch submit of $2 exited $rc (see ${3%.json}.stderr); not falling back to local" >&2; rm -f "$3"; return 1 ;; esac
}

if [ "$MODE" = dry ]; then
  STATUS=0
  gen "$OUT/requests" > "$OUT/requests.list" || exit 1
  gen "$OUT/neg-rx" --negative rx > /dev/null; gen "$OUT/neg-pull" --negative pull > /dev/null
  gen "$OUT/nostat" --no-stat > /dev/null; gen "$OUT/again" > /dev/null
  for d in requests neg-rx neg-pull nostat; do
    for f in "$OUT/$d"/*.json; do
      (cd "$OUT/$d" && $KLT_SIM sim --dry-run "$(basename "$f")") > "$OUT/dry-$d-$(basename "$f" .json).log" 2>&1 \
        || { echo "mc: FAIL: dry-run $d/$(basename "$f")" >&2; STATUS=1; }
    done
  done
  # same seed, same request -> identical derived per-sample seeds, nominal and known-bad alike
  s() { grep -h "rndseed=" "$1" | sed 's/^ *//'; }
  (cd "$OUT/again" && $KLT_SIM sim --dry-run xfer_5v_25C.json) > "$OUT/dry-again.log" 2>&1
  cmp -s <(s "$OUT/dry-requests-xfer_5v_25C.log") <(s "$OUT/dry-again.log") \
    && cmp -s <(s "$OUT/dry-requests-xfer_5v_25C.log") <(s "$OUT/dry-neg-rx-xfer_5v_25C.log") \
    || { echo "mc: FAIL: seeds differ between runs or between nominal and known-bad" >&2; STATUS=1; }
  [ "$STATUS" = 0 ] && echo "mc: dry-run OK: $(wc -l < "$OUT/requests.list") requests valid, seeds reproducible ($OUT)"
  exit $STATUS
fi

if [ "$MODE" = neg ]; then
  mkdir -p "$OUT/klt"
  case "$KIND" in nostat) gen "$OUT/requests" --no-stat > "$OUT/requests.list" ;; *) gen "$OUT/requests" --negative "$KIND" > "$OUT/requests.list" ;; esac
  while read -r stem; do submit "$OUT/requests" "$stem" "$OUT/klt/$stem.json" || exit 1; done < "$OUT/requests.list"
  python3 -I "$HERE/collect.py" "$OUT" --yield-cmd "$KLT_YIELD" --negative "$KIND"; RC=$?
  if [ "$RC" -ne 0 ]; then echo "mc: negative control $KIND failed as it must (collect rc=$RC)" >&2; exit 1; fi
  echo "mc: NEGATIVE CONTROL $KIND DID NOT FAIL" >&2; exit 0
fi

mkdir -p "$OUT/klt" "$OUT/negative" "$OUT/art"
if [ "$MODE" = run ]; then
  gen "$OUT/requests" > "$OUT/requests.list" || { echo "mc: FAIL: request generation" >&2; exit 1; }
  cp "$GPIO" "$OUT/gpio.spice.nominal"
  gen "$OUT/neg-rx" --negative rx > /dev/null; gen "$OUT/neg-pull" --negative pull > /dev/null
fi
SUBMITRC=0
while read -r stem; do submit "$OUT/requests" "$stem" "$OUT/klt/$stem.json" || SUBMITRC=1; done < "$OUT/requests.list"
for k in rx pull; do
  for f in "$OUT/neg-$k"/*.json; do
    stem="$(basename "$f" .json)"; submit "$OUT/neg-$k" "$stem" "$OUT/negative/$stem.json" || SUBMITRC=1
  done
done
# repeat run: the same request, resubmitted, must give identical samples (same seed, same engine build)
mkdir -p "$OUT/repeat"
submit "$OUT/requests" pulldown_5v_25C "$OUT/repeat/pulldown_5v_25C.json" || SUBMITRC=1
REPRO=$(python3 -I - "$OUT/klt/pulldown_5v_25C.json" "$OUT/repeat/pulldown_5v_25C.json" <<'PY'
import json, sys
v = lambda p: [(c["corner_id"], [m["value"] for m in c["measurements"]]) for c in json.load(open(p))["corners"]]
try:
    a, b = v(sys.argv[1]), v(sys.argv[2])
    print("identical" if a == b and a else "DIFFERENT")
except Exception as e:
    print("unreadable")
PY
)
echo "mc: repeat run of pulldown_5v_25C: $REPRO"

{ echo "- date (UTC): $STAMP"
  echo "- open_pdks revision (pinned, sim/toolchain.json): \`$OPEN_PDKS\`, variant \`$VARIANT\`"
  echo "- ngspice on the submitting host: \`$NGSPICE_VERSION\`"
  echo "- klt sim client: \`$($KLT_SIM --version 2>&1 | head -1)\` (batch fleet); klt yield: \`$($KLT_YIELD --version 2>&1 | head -1)\`"
  echo "- repo commit: \`$(git -C "$REPO" rev-parse HEAD 2>/dev/null)\`; netlist: \`design/gpio.spice\` (copied per request as gpio.spice)"
  echo "- Monte Carlo: n=300 per request, seed 20261027, vary=both, sw_stat_global=sw_stat_mismatch=1 (in each netlist)"
  echo "- repeat run of \`pulldown_5v_25C\` (same request, resubmitted): $REPRO"; } > "$OUT/meta.txt"

python3 -I "$HERE/collect.py" "$OUT" --yield-cmd "$KLT_YIELD"; CRC=$?
{ echo "date_utc=$STAMP"; echo "open_pdks=$OPEN_PDKS"; echo "variant=$VARIANT"; echo "submit_rc=$SUBMITRC"; echo "repeat=$REPRO"
  echo "result=$([ "$CRC" = 0 ] && [ "$SUBMITRC" = 0 ] && [ "$REPRO" = identical ] && echo PASS || { [ "$CRC" = 3 ] && echo ROWS_FAIL || echo INVALID; })"; } > "$OUT/record.txt"
if [ "$SUBMITRC" -ne 0 ] || [ "$CRC" = 1 ] || [ "$REPRO" != identical ]; then echo "mc: INVALID (record kept: $OUT)" >&2; exit 1; fi
echo "record: $OUT"; [ "$CRC" = 3 ] && { echo "mc: data valid, some rows miss their target yield"; exit 3; }
echo "mc: PASS"
