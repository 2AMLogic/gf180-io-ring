#!/usr/bin/env bash
# Regenerate the T1 item-4 LVS reports (klt 0.8.0). Run from anywhere.
#   <cell>.json      layout vs the item-1 netlist design/<cell>.spice, with the declared
#                    hint hints.short_nets {DVSS, VSS}: the ring draws no deep-Nwell
#                    isolation, so both domains share one p-substrate and the extractor
#                    reports one net `DVSS|VSS` (layout/README.md). The report records
#                    the join as a hints.short_nets_applied entry.
#   raw/<cell>.json  the same compare without the hint (the netlists are never edited).
set -euo pipefail
cd "$(dirname "$0")/../../.."
ROOT=$PWD
D=manifests/evidence/item4
mkdir -p $D/raw
KLT=(uvx --from "klayout-tools==0.8.0" klt)
req() {  # req <cell> <with-hint: 1|0>
  # compare_mos_flavour: a 3.3 V device where the netlist has 5/6 V (or the reverse) must not match.
  # The layout is extracted flat, so the ring's hierarchical reference is flattened.
  local fl=; [ "$1" = io_ring ] && fl=',"flatten_reference":true'
  local opts=',"options":{"compare_mos_flavour":true'"$fl"'}'
  [ "$2" = 1 ] && opts="$opts"',"hints":{"short_nets":{"nets":[["DVSS","VSS"]]}}'
  printf '{"schema":"klt.lvs.request/1","portable_paths":true,"layout":{"file":"%s/layout/gf180_io_ring.gds","deck":"gf180mcu","top":"%s"},"reference":{"netlist":"%s/design/%s.spice","top":"%s","form":"subckt-call"}%s}' \
    "$ROOT" "$1" "$ROOT" "$1" "$1" "$opts"
}
run() {  # run <cell> <with-hint> <out>
  local rc=0
  req "$1" "$2" | "${KLT[@]}" lvs - --format json > "$3" || rc=$?
  [ $rc -eq 0 ] || [ $rc -eq 3 ] || { echo "klt lvs $1 failed ($rc)" >&2; exit 1; }
}
# filler has no devices or nets, so the layout netlist has no `filler` circuit to compare;
# it is covered by the ring compare, where it is instantiated (see item4.md).
for c in io_ring gpio dvdd_pad dvss_pad core_pad corner; do
  run $c 1 $D/$c.json
  run $c 0 $D/raw/$c.json
done
