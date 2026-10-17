#!/usr/bin/env bash
# Model smoke bench, single typical-corner operating point (local ngspice, no grid).
#   sim/smoke/run.sh                  run, write a dated record under records/
#   sim/smoke/run.sh --bad-model-path negative control: must exit non-zero
# Exit 0 only if the env check passes, the log has no model/include error, and
# all four currents are finite and non-zero (ngspice can exit 0 on a missing include).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIM="$(dirname "$HERE")"
BAD=0; [ "${1:-}" = "--bad-model-path" ] && BAD=1
ENVOUT="$("$SIM/check_env.sh")" || { echo "$ENVOUT"; exit 2; }
eval "$(printf '%s\n' "$ENVOUT" | sed "s/^\([A-Z_]*\)=\(.*\)$/\1='\2'/")"
MODELDIR="$PDK_MODELDIR"; [ "$BAD" = 1 ] && MODELDIR="$PDK_MODELDIR/does-not-exist"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
[ "$BAD" = 1 ] && OUT="$(mktemp -d)" || { OUT="$HERE/records/$STAMP"; mkdir -p "$OUT"; }
sed "s|@MODELDIR@|$MODELDIR|g" "$HERE/smoke.spice" > "$OUT/smoke.spice"
ngspice -b -o "$OUT/ngspice.log" "$OUT/smoke.spice" >/dev/null 2>&1; RC=$?
STATUS=0
if grep -qiE "could not find|can't open|cannot open|no such file|fatal|^error|unknown (model|subckt)|Error on line" "$OUT/ngspice.log"; then
  echo "smoke: FAIL: model/include error in log ($OUT/ngspice.log)" >&2; STATUS=1
fi
grep '^SMOKE ' "$OUT/ngspice.log" > "$OUT/measurements.txt"
N="$(wc -l < "$OUT/measurements.txt")"
[ "$N" -eq 4 ] || { echo "smoke: FAIL: expected 4 measurements, got $N" >&2; STATUS=1; }
while read -r _ name _ val; do
  if ! awk -v v="$val" 'BEGIN{ if (v+0==v && v!="nan" && v!="inf" && v!="-inf" && (v>0||v<0)) exit 0; exit 1 }'; then
    echo "smoke: FAIL: $name = '$val' not finite non-zero" >&2; STATUS=1
  fi
done < "$OUT/measurements.txt"
[ "$RC" -eq 0 ] || echo "smoke: note: ngspice rc=$RC" >&2
if [ "$BAD" = 0 ]; then
  { echo "date_utc=$STAMP"; echo "open_pdks=$OPEN_PDKS"; echo "variant=$VARIANT"
    echo "ngspice=$NGSPICE_VERSION"; echo "corner=typical temp=27C"
    echo "result=$([ $STATUS = 0 ] && echo PASS || echo FAIL)"; } > "$OUT/record.txt"
  echo "record: $OUT"
fi
[ "$STATUS" = 0 ] && { cat "$OUT/measurements.txt"; echo "smoke: PASS"; } || echo "smoke: FAIL" >&2
exit $STATUS
