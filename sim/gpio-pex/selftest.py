#!/usr/bin/env python3
"""No-simulation self-test for gen_requests.py -- no test framework needed.

    python3 -I sim/gpio-pex/selftest.py

Five cases against a temporary fixture model directory (a design.ngspice with
one .param card) and the real design/ cells -- no PDK, no ngspice, nothing
written into the repository:

  1. grid generation exits 0 and emits 19 requests, probe generation 15 (7
     decks x 2 supply modes + esd_pad, plus 2 pull decks x 2 modes nominal in
     grid only); the printed names match the .sp and .json stems exactly,
     include esd_pad, and the two dvdd_pad rail decks leave neither file;
  2. a copy of a rail deck under an unfamiliar request stem -- header comment
     mentioning design/gpio.spice kept, active .include dvdd_pad.spice kept --
     is selected against: omitted from stdout, both files removed. Selection
     reads the deck's include card, not its name;
  3. a GPIO deck with every Xdut line removed still fails generation, exiting
     non-zero with the pin-rewrite diagnostic;
  4. a GPIO deck with one Xdut line a node short fails the same way.

Cases 2-4 drive the production generator unmodified out of a symlink farm
whose gpio-corners/gen_requests.py is a test double: it runs the real corner
generator, then adds or breaks one deck. The production selection and rewrite
path is what executes.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.dirname(HERE)
REPO = os.path.dirname(SIM)
PEX = os.path.join(HERE, "gen_requests.py")
DESIGN = os.path.join(REPO, "design")

# The test double the farm installs as gpio-corners/gen_requests.py. It finds
# the real generator through the farm's gpio-pex symlink, runs it with the
# arguments given, then applies the fixture named in PEX_SELFTEST_FIXTURE.
DOUBLE = '''#!/usr/bin/env python3
import os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REAL = os.path.join(os.path.dirname(os.path.realpath(os.path.join(HERE, "..", "gpio-pex"))),
                    "gpio-corners", "gen_requests.py")
r = subprocess.run([sys.executable, "-I", REAL] + sys.argv[1:], capture_output=True, text=True)
sys.stderr.write(r.stderr)
if r.returncode:
    sys.exit(r.returncode)
out = sys.argv[1]
fixture = os.environ.get("PEX_SELFTEST_FIXTURE", "")
if fixture == "clone":
    for ext in (".sp", ".json"):
        shutil.copy(os.path.join(out, "esd_rail_release" + ext),
                    os.path.join(out, "esd_rail_clone" + ext))
    print(r.stdout + "esd_rail_clone")
elif fixture in ("no-xdut", "short-xdut"):
    path = os.path.join(out, "vol_5v.sp")
    lines = open(path).read().splitlines(True)
    if fixture == "no-xdut":
        lines = [l for l in lines if not l.startswith("Xdut")]
    else:
        for i, l in enumerate(lines):
            if l.startswith("Xdut"):
                t = l.split()
                lines[i] = " ".join([t[0]] + t[1:-2] + [t[-1]]) + "\\n"
                break
    open(path, "w").write("".join(lines))
    print(r.stdout)
else:
    sys.stderr.write("pex selftest double: PEX_SELFTEST_FIXTURE not set\\n")
    sys.exit(2)
'''


def farm(tmp):
    """A lookalike sim/ tree: production gpio-pex symlinked through, a
    gpio-corners whose generator is the double above wrapping the real one."""
    root = tempfile.mkdtemp(prefix="pex-selftest-farm-", dir=tmp)
    os.makedirs(os.path.join(root, "sim", "gpio-corners"))
    os.symlink(os.path.join(SIM, "gpio-pex"), os.path.join(root, "sim", "gpio-pex"))
    with open(os.path.join(root, "sim", "gpio-corners", "gen_requests.py"), "w") as f:
        f.write(DOUBLE)
    return os.path.join(root, "sim", "gpio-pex", "gen_requests.py")


def run_gen(script, model, args=(), fixture=None):
    out = tempfile.mkdtemp(prefix="pex-selftest-out-", dir=TMP)
    env = dict(os.environ)
    if fixture:
        env["PEX_SELFTEST_FIXTURE"] = fixture
    return out, subprocess.run([sys.executable, "-I", script, out, model, DESIGN] + list(args),
                               capture_output=True, text=True, env=env)


def fail(label, *problems):
    print(f"FAIL [{label}]: " + "; ".join(problems))
    return False


def ok(label, note):
    print(f"ok [{label}]: {note}")
    return True


def case_generation(label, proc, out, want):
    names = proc.stdout.split()
    sp = {f[:-3] for f in os.listdir(out) if f.endswith(".sp")}
    js = {f[:-5] for f in os.listdir(out) if f.endswith(".json")}
    problems = []
    if proc.returncode != 0:
        problems.append(f"rc={proc.returncode}, stderr: {proc.stderr.strip()}")
    if len(names) != want:
        problems.append(f"{len(names)} requests, expected {want}")
    if proc.returncode == 0:
        if set(names) != sp:
            problems.append(f".sp stems != printed names: {sorted(sp ^ set(names))}")
        if set(names) != js:
            problems.append(f".json stems != printed names: {sorted(js ^ set(names))}")
        for stem in ("esd_rail", "esd_rail_release"):
            if stem in names or os.path.exists(os.path.join(out, stem + ".sp")) \
                    or os.path.exists(os.path.join(out, stem + ".json")):
                problems.append(f"{stem} survived")
        if "esd_pad" not in names:
            problems.append("esd_pad missing")
    if problems:
        return fail(label, *problems)
    if proc.returncode != 0:
        return fail(label, f"rc={proc.returncode}, stderr: {proc.stderr.strip()}")
    return ok(label, f"rc=0, {want} requests, names match files, rail decks absent")


def case_refused(label, proc, needle):
    if proc.returncode == 0:
        return fail(label, "exit 0 -- the malformed GPIO deck was absorbed, not refused")
    if needle not in proc.stderr:
        return fail(label, f"stderr does not name the diagnostic {needle!r}: {proc.stderr.strip()}")
    return ok(label, f"refused with rc={proc.returncode}")


TMP = None


def main():
    global TMP
    with tempfile.TemporaryDirectory() as tmp:
        TMP = tmp
        model = os.path.join(tmp, "model")
        os.makedirs(model)
        with open(os.path.join(model, "design.ngspice"), "w") as f:
            f.write(".param fixture=0\n")

        out, proc = run_gen(PEX, model)
        if not case_generation("grid", proc, out, 19):
            return 1
        out, proc = run_gen(PEX, model, ["--probe"])
        if not case_generation("probe", proc, out, 15):
            return 1

        double = farm(tmp)
        out, proc = run_gen(double, model, fixture="clone")
        names = proc.stdout.split()
        problems = []
        if proc.returncode != 0:
            problems.append(f"rc={proc.returncode}, stderr: {proc.stderr.strip()}")
        if "esd_rail_clone" in names:
            problems.append("the unfamiliar rail stem was printed")
        if os.path.exists(os.path.join(out, "esd_rail_clone.sp")) \
                or os.path.exists(os.path.join(out, "esd_rail_clone.json")):
            problems.append("the unfamiliar rail deck left files behind")
        if proc.returncode == 0 and len(names) != 19:
            problems.append(f"{len(names)} requests, expected 19")
        if problems:
            return fail("unfamiliar-stem", *problems)
        print("ok [unfamiliar-stem]: rail deck under a new name selected against, files removed")

        _, proc = run_gen(double, model, fixture="no-xdut")
        if not case_refused("no-xdut", proc, "no Xdut line to reorder"):
            return 1
        _, proc = run_gen(double, model, fixture="short-xdut")
        if not case_refused("short-xdut", proc, "nodes, expected 11"):
            return 1

    print("selftest: all pex generator cases pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
