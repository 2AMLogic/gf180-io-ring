#!/usr/bin/env bash
# ESD pad-clamp diode bench: 3 diode process sections x 3 temperatures, both clamp
# diodes and 33 areas inside each unit. Three `klt sim` requests (forward dc, reverse dc,
# ac capacitance at 0 V and 5.5 V; 9, 9 and 18 units), plain .meas cards only (no analysis_steps).
#   sim/esd_clamp/run.sh                    run; on success write records/<UTC stamp>/
#   sim/esd_clamp/run.sh --backend local    override the klt backend (default: klt's own,
#                                           i.e. $KLT_SIM_BACKEND, so the batch fleet on a
#                                           dispatch worker)
#   sim/esd_clamp/run.sh --bad-model-path   negative control: must exit non-zero. 1 = klt rejected
#                                           the bad request (the control worked); 3 = klt accepted
#                                           it (the control failed); 2 = usage or environment error
# A failed unit, a failed submit or a failed wording check fails the run and writes
# no record. There is no local-grid fallback for a failed batch submit.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIM="$(dirname "$HERE")"
PY="python3 -I $HERE/esd_clamp.py"
BAD=0; BACKEND=""
while [ $# -gt 0 ]; do
  case "$1" in
    --bad-model-path) BAD=1 ;;
    --backend) BACKEND="${2:-}"; shift ;;
    *) echo "usage: run.sh [--backend NAME] [--bad-model-path]" >&2; exit 2 ;;
  esac; shift
done
ENVOUT="$("$SIM/check_env.sh")" || { echo "$ENVOUT"; exit 2; }
eval "$(printf '%s\n' "$ENVOUT" | sed "s/^\([A-Z_]*\)=\(.*\)$/\1='\2'/")"
$PY selftest || exit 2
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
EFF="${BACKEND:-${KLT_SIM_BACKEND:-local}}"
# pdk_root pins the local PDK revision; off-host backends use the image's PDK
# and refuse a caller-local pdk_root, so it is only passed for local runs.
PDKROOT=""; case "$EFF" in local|local-parallel) PDKROOT="$(dirname "$(dirname "$(dirname "$PDK_MODELDIR")")")" ;; esac
if [ "$BAD" = 1 ]; then
  $PY gen --out "$WORK" --pdk-root "$WORK/does-not-exist" --backend local --bad-lib || exit 2
  if klt sim "$WORK/request_fwd.json" --dry-run --format json >"$WORK/dry.json" 2>"$WORK/dry.err"; then
    echo "esd_clamp: FAIL: negative control was accepted" >&2; exit 3
  fi
  echo "esd_clamp: negative control rejected as expected: $(head -c 200 "$WORK/dry.err")" >&2
  exit 1
fi
$PY gen --out "$WORK" ${PDKROOT:+--pdk-root "$PDKROOT"} ${BACKEND:+--backend "$BACKEND"} || exit 2
for K in fwd leak cap; do
  klt sim "$WORK/request_$K.json" --dry-run --format json >/dev/null || { echo "esd_clamp: FAIL: request_$K does not validate" >&2; exit 1; }
done
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
for K in fwd leak cap; do
  klt sim "$WORK/request_$K.json" --format json --report-out "$WORK/report_$K.json.gz" -o "$WORK/out_$K" >"$WORK/klt_$K.out" 2>"$WORK/klt_$K.err"
  RC=$?
  if [ "$RC" -ne 0 ]; then
    echo "esd_clamp: FAIL: klt sim ($K) exit $RC" >&2; tail -20 "$WORK/klt_$K.err" >&2
    exit 1
  fi
done
$PY derive --fwd "$WORK/report_fwd.json.gz" --leak "$WORK/report_leak.json.gz" --cap "$WORK/report_cap.json.gz" \
  --grid "$WORK/grid.json" --out "$WORK" \
  --meta "date_utc=$STAMP" "open_pdks=$OPEN_PDKS" "variant=$VARIANT" "ngspice_local=$NGSPICE_VERSION" \
  || { echo "esd_clamp: FAIL: derivation or wording check failed" >&2; exit 1; }
OUT="$HERE/records/$STAMP"; mkdir -p "$OUT"
for f in esd_clamp.spice grid.json request_fwd.json request_leak.json request_cap.json \
         report_fwd.json.gz report_leak.json.gz report_cap.json.gz record.md summary.json; do
  cp "$WORK/$f" "$OUT/$f"
done
echo "record: $OUT"
cat "$WORK/summary.json"
