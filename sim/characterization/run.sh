#!/usr/bin/env bash
# Regenerate the per-spec-row characterization report from the committed evidence.
#   sim/characterization/run.sh           rewrite report.md and report.json in place
#   sim/characterization/run.sh --check   build to a temp dir and byte-compare against
#                                         the committed report; exit 1 on drift
#
# Reads manifests/gf180-io-ring.json and, through it, only the files that manifest
# cites for T1 items 5 and 6. Runs no simulation and needs nothing but python3 -- no
# klt, no PDK, no ngspice -- so --check is cheap enough to run on every pull request.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$(dirname "$HERE")")"

case "${1:-}" in
  "") ARGS=() ;;
  --check) ARGS=(--check) ;;
  *) echo "usage: run.sh [--check]" >&2; exit 2 ;;
esac

exec python3 -I "$HERE/build.py" "$REPO" --out "$HERE" "${ARGS[@]+"${ARGS[@]}"}"
