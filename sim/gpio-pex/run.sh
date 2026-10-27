#!/usr/bin/env bash
# Re-run the item-5 GPIO spec suite on the netlist extracted from layout/gf180_io_ring.gds (T1 item 7).
#   sim/gpio-pex/run.sh           cold start: one `klt pex --backend batch` per request; writes records/<UTC stamp>/
#   sim/gpio-pex/run.sh --probe   local single-corner debug probe of one deck (vol_5v, typical, 25 C)
# The grid is the item-5 grid (sim/gpio-corners/gen_requests.py, reused, not copied); every request
# is a multi-corner `klt pex` whose schematic and extracted legs both go to the Spot fleet. A failed
# submit fails the run; there is no local fallback (only --probe runs locally, one corner).
# KLT_CLIENT: the fleet runner image is klt 0.7.0 and refuses a 0.8.x client, so the default is 0.7.0.
# Exit 0 only if every request reports status pass/fail with no errored delta row.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIM="$(dirname "$HERE")"
REPO="$(dirname "$SIM")"
KLT_CLIENT="${KLT_CLIENT:-uvx --from klayout-tools==0.7.0 klt}"
PINS="A,OE,IE,PU,PD,Y,PAD,DVDD,VDD,DVSS,VSS"
MODE=run
case "${1:-}" in "") ;; --probe) MODE=probe ;; *) echo "usage: run.sh [--probe]" >&2; exit 2 ;; esac

ENVOUT="$("$SIM/check_env.sh")" || { echo "$ENVOUT"; exit 2; }
eval "$(printf '%s\n' "$ENVOUT" | sed "s/^\([A-Z_]*\)=\(.*\)$/\1='\2'/")"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
if [ "$MODE" = run ]; then OUT="$HERE/records/$STAMP"; mkdir -p "$OUT"; else OUT="$(mktemp -d)"; fi
REQ="$OUT/requests"; mkdir -p "$REQ" "$OUT/pex"
EXTRA=""; [ "$MODE" = probe ] && EXTRA="--probe"
python3 -I "$HERE/gen_requests.py" "$REQ" "$PDK_MODELDIR" "$REPO/design" $EXTRA > "$OUT/requests.list" \
  || { echo "gpio-pex: FAIL: request generation" >&2; exit 1; }
[ "$MODE" = probe ] && sed -i '/^vol_5v$/!d' "$OUT/requests.list"

BACKEND=batch; [ "$MODE" = probe ] && BACKEND=local
STATUS=0
while read -r stem; do
  # rc 0 pass, 4 = a failing or errored unit; the envelope is on stdout either way.
  $KLT_CLIENT pex --deck gf180mcu --top gpio --pins "$PINS" \
    --pdk-root "$(dirname "$(dirname "$(dirname "$PDK_MODELDIR")")")" \
    -o "$OUT/pex/$stem.spice" --outdir "$OUT/pex/$stem" --backend "$BACKEND" --format json \
    "$REPO/layout/gf180_io_ring.gds" "$REQ/$stem.json" > "$OUT/pex/$stem.json" 2> "$OUT/pex/$stem.stderr"
  RC=$?
  echo "gpio-pex: $stem: klt rc=$RC"
  case "$RC" in 0|4) ;; *) STATUS=1; echo "gpio-pex: pex failed for $stem (see $OUT/pex/$stem.stderr); not falling back to local" >&2 ;; esac
  python3 -I -c "
import json, sys
d = json.load(open(sys.argv[1])); rows = d.get('delta') or []
bad = [r for r in rows if r.get('status') == 'error']
print('gpio-pex: %s: %d rows, %d errored; body_bias %s' % (sys.argv[2], len(rows), len(bad), (d.get('body_bias') or {}).get('status')))
sys.exit(1 if bad else 0)" "$OUT/pex/$stem.json" "$stem" || STATUS=1
done < "$OUT/requests.list"
echo "gpio-pex: output in $OUT"
exit $STATUS
