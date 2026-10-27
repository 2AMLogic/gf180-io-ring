#!/usr/bin/env bash
# Regenerate the T1 item-11 klt erc supply report (klt 0.8.0). Run from anywhere.
#   io_ring.json   klt erc of the assembled ring against erc-spec.json (supply nets
#                  DVDD/DVSS/VDD/VSS, Metal3-5 roles, checked well/substrate ties).
# Exit 0 (clean) and 4 (clean, antenna ratios unchecked: no gf180mcu limit table) are
# accepted; 3 (findings) is a failed run and is recorded as such by the report.
set -euo pipefail
cd "$(dirname "$0")/../../.."
rc=0
uvx --from "klayout-tools==0.8.0" klt erc layout/gf180_io_ring.gds \
    manifests/evidence/item11/erc-spec.json --top io_ring --deck gf180mcu \
    --format json > manifests/evidence/item11/io_ring.json || rc=$?
[ $rc -eq 0 ] || [ $rc -eq 3 ] || [ $rc -eq 4 ] || { echo "klt erc failed ($rc)" >&2; exit 1; }
