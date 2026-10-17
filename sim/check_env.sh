#!/usr/bin/env bash
# Verify the toolchain against sim/toolchain.json + sim/pdk.json.
# On success prints "KEY=value" lines (PDK_MODELDIR, NGSPICE_VERSION, ...).
# On any mismatch exits non-zero naming the field. Usage: check_env.sh [--quiet]
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 -I - "$HERE" "$@" <<'PY'
import json, os, re, subprocess, sys
here = sys.argv[1]
def fail(field, msg):
    print(f"check_env: FAIL [{field}]: {msg}", file=sys.stderr); sys.exit(1)
def load(n):
    try:
        return json.load(open(os.path.join(here, n)))
    except Exception as e:
        fail(n, f"cannot read: {e}")
tc, pdk = load("toolchain.json"), load("pdk.json")
for k in ("open_pdks", "ngspice_min_major", "python_min"):
    if k not in tc: fail(f"toolchain.json:{k}", "missing")
for k in ("variant",):
    if k not in pdk: fail(f"pdk.json:{k}", "missing")
need = tuple(int(x) for x in str(tc["python_min"]).split("."))
if sys.version_info[:2] < need:
    fail("python_min", f"have {sys.version_info[0]}.{sys.version_info[1]}, need >= {tc['python_min']}")
try:
    out = subprocess.run(["ngspice", "--version"], capture_output=True, text=True, timeout=30).stdout
except Exception as e:
    fail("ngspice", f"not runnable: {e}")
m = re.search(r"ngspice-(\d+)", out)
if not m: fail("ngspice_min_major", "cannot parse ngspice --version")
if int(m.group(1)) < int(tc["ngspice_min_major"]):
    fail("ngspice_min_major", f"have ngspice-{m.group(1)}, need >= {tc['ngspice_min_major']}")
home = os.path.expanduser("~")
roots = list(pdk.get("search_roots", [])) + [os.path.join(home, ".volare"), os.path.join(home, ".ciel")]
rev, var = tc["open_pdks"], pdk["variant"]
found = None
for r in roots:
    for sub in ("volare/gf180mcu/versions", "ciel/gf180mcu/versions", "gf180mcu/versions"):
        d = os.path.join(r, sub, rev, var, "libs.tech", "ngspice")
        if os.path.isfile(os.path.join(d, "sm141064.ngspice")):
            found = d; break
    if found: break
if not found:
    fail("open_pdks", f"no libs.tech/ngspice/sm141064.ngspice for revision {rev} variant {var} under {roots}")
if "--quiet" not in sys.argv[2:]:
    print(f"PDK_MODELDIR={found}")
    print(f"OPEN_PDKS={rev}")
    print(f"VARIANT={var}")
    print(f"NGSPICE_VERSION=ngspice-{m.group(1)}")
PY
