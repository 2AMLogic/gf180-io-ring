#!/usr/bin/env python3
"""Verdict test for the last block of run.sh -- no test framework needed.

    python3 -I sim/mc/selftest.py

run.sh grades a finished campaign three ways: the `result=` field of record.txt, the terminal
message and the exit status (0 every row meets its target, 3 a valid row misses, 1 invalid data
or a harness failure). The field and the exit status were decided by two separate expressions
(issue #165), and they disagreed. With a failed submission, or a repeat run that was not
identical, next to a collector status of 3, the record said ROWS_FAIL while the script exited 1
as invalid; with a collector status outside 0, 1 and 3 next to a clean submission and an
identical repeat, the record said INVALID while the script printed PASS and exited 0. One
decision now serves all three.

Every case copies the production run.sh byte for byte into a sandbox and cold-starts it with a
double for everything it calls -- no PDK, no fleet, no klt, nothing written into the repository:
sim/check_env.sh; gen_requests.py, which emits two nominal requests (xfer_5v_25C and
pulldown_5v_25C, the one run.sh repeats) and one per negative control; collect.py, which exits
with the status the case names; and one klt standing in for both KLT_SIM and KLT_YIELD, which
answers the start-up probe, prints a one-corner report per request, refuses the request the
case names as the failed submission, and moves the reported value between two submissions of
the same request when the case asks for a repeat that is not identical.

The cases are every combination of submission {ok, failed} x repeat {identical, DIFFERENT} x
collector status {0, 1, 2, 3, 4}. Each must record in record.txt, print, and exit as, the same
verdict: PASS (exit 0) for a clean submission, an identical repeat and collector status 0,
ROWS_FAIL (exit 3) for the same with status 3, and INVALID (exit 1) for every other
combination.

On run.sh before the fix five combinations fail. (ok, identical, 2) exits 0 and prints PASS:
the third row of the issue. (ok, DIFFERENT, 3) and (failed, identical, 3) record ROWS_FAIL: the
first two rows. (ok, identical, 4) and (failed, DIFFERENT, 3) are those defects once more: the
first under another unexpected collector status, the second with a failed submission and a
different repeat recording ROWS_FAIL all the same. The fifteen others hold before and after.
That is the point of the test.
"""
import itertools
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, "run.sh")
FAILED_REQUEST = "xfer_5v_25C"
REPEATED_REQUEST = "pulldown_5v_25C"
SUBMISSION = (0, 1)
REPEAT = ("identical", "DIFFERENT")
COLLECTOR = (0, 1, 2, 3, 4)
VERDICTS = ("PASS", "ROWS_FAIL", "INVALID")

CHECK_ENV = '''#!/usr/bin/env bash
echo "PDK_MODELDIR=/mc-selftest-model"
echo "OPEN_PDKS=mc-selftest"
echo "VARIANT=gf180mcuD"
echo "NGSPICE_VERSION=ngspice-42"
'''

GEN = f'''import os, sys
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
if "--negative" in sys.argv:
    stems = ["neg_" + sys.argv[sys.argv.index("--negative") + 1]]
else:
    stems = ["{FAILED_REQUEST}", "{REPEATED_REQUEST}"]
for stem in stems:
    with open(os.path.join(out, stem + ".json"), "w") as f:
        f.write("{{}}\\n")
print("\\n".join(stems))
'''

COLLECT = '''import os, sys
sys.exit(int(os.environ["MC_SELFTEST_COLLECT_RC"]))
'''

KLT = r'''#!/usr/bin/env bash
case "$1" in
  --version) echo "klt 0.0.0 (sim/mc/selftest.py double)"; exit 0 ;;
  yield) exit 0 ;;
  sim) shift ;;
  *) echo "klt double: unexpected arguments: $*" >&2; exit 2 ;;
esac
stem="${1%.json}"
art="."
while [ $# -gt 0 ]; do
  [ "$1" != -o ] || art="$2"
  shift
done
if [ "$stem" = "${MC_SELFTEST_FAIL:-}" ]; then
  echo "klt double: refusing $stem" >&2
  exit 4
fi
mkdir -p "$art"
n=$(( $(cat "$art/submitted" 2>/dev/null || echo 0) + 1 ))
echo "$n" > "$art/submitted"
value=1
[ "${MC_SELFTEST_REPEAT:-}" != DIFFERENT ] || value=$n
printf '{"corners":[{"corner_id":"c0","measurements":[{"name":"v","value":%s}]}]}\n' "$value"
'''


def write(path, text, executable=False):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    if executable:
        os.chmod(path, 0o755)


def sandbox(tmp):
    """A repository lookalike for one campaign: the production run.sh copied byte for byte to
    sim/mc/, a stand-in design/gpio.spice and the doubles. Returns its root."""
    # Exercise both shell word splitting (space) and PATH splitting (colon).
    root = tempfile.mkdtemp(prefix="mc selftest:", dir=tmp)
    for rel in ("design", "sim", "sim/mc", "bin"):
        os.makedirs(os.path.join(root, rel))
    write(os.path.join(root, "design", "gpio.spice"), "* stand-in for design/gpio.spice\n")
    write(os.path.join(root, "sim", "check_env.sh"), CHECK_ENV, executable=True)
    write(os.path.join(root, "sim", "mc", "gen_requests.py"), GEN)
    write(os.path.join(root, "sim", "mc", "collect.py"), COLLECT)
    write(os.path.join(root, "bin", "klt"), KLT, executable=True)
    shutil.copy2(RUN, os.path.join(root, "sim", "mc", "run.sh"))
    return root


def campaign(root, case):
    """Cold-start the copied run.sh with the doubles set to the three statuses of a case;
    returns the finished process."""
    submission, repeat, collector = case
    env = dict(os.environ, KLT_SIM="mc_selftest_klt", KLT_YIELD="mc_selftest_klt",
               MC_SELFTEST_KLT=os.path.join(root, "bin", "klt"),
               MC_SELFTEST_COLLECT_RC=str(collector), MC_SELFTEST_REPEAT=repeat)
    if submission:
        env["MC_SELFTEST_FAIL"] = FAILED_REQUEST
    # run.sh splits its command variables into words. Give it a single function
    # name and let that function invoke the double by its quoted absolute path.
    launch = '''mc_selftest_klt() { "$MC_SELFTEST_KLT" "$@"; }
export -f mc_selftest_klt
exec bash sim/mc/run.sh
'''
    return subprocess.run(["bash", "-c", launch], cwd=root, env=env,
                          capture_output=True, text=True, check=False)


def expected(case):
    """The verdict one campaign must get, and the exit status that goes with it."""
    submission, repeat, collector = case
    if submission == 0 and repeat == "identical":
        if collector == 0:
            return "PASS", 0
        if collector == 3:
            return "ROWS_FAIL", 3
    return "INVALID", 1


def message(verdict, record="<record>"):
    """The terminal line run.sh prints for a verdict."""
    if verdict == "PASS":
        return "mc: PASS"
    if verdict == "ROWS_FAIL":
        return "mc: data valid, some rows miss their target yield"
    return f"mc: INVALID (record kept: {record})"


def describe(case):
    submission, repeat, collector = case
    return f"submission {'ok' if submission == 0 else 'failed'}, repeat {repeat}, collector status {collector}"


def problems(root, case, proc):
    """Ways the finished campaign misses its case; empty list = none."""
    want, want_exit = expected(case)
    submission, repeat = case[:2]
    records = os.path.join(root, "sim", "mc", "records")
    written = os.listdir(records) if os.path.isdir(records) else []
    if len(written) != 1:
        return [f"run.sh left {len(written)} records under sim/mc/records, expected one"]
    record = os.path.join(records, written[0])
    with open(os.path.join(record, "record.txt"), encoding="utf-8") as f:
        fields = dict(line.rstrip("\n").split("=", 1) for line in f)
    found = []
    if (fields.get("submit_rc"), fields.get("repeat")) != (str(submission), repeat):
        found.append("the doubles did not stage the case: record.txt says "
                     f"submit_rc={fields.get('submit_rc')} and repeat={fields.get('repeat')}")
    if proc.returncode != want_exit:
        found.append(f"exit {proc.returncode}, expected {want_exit}")
    if fields.get("result") != want:
        found.append(f"record.txt says result={fields.get('result')}, expected {want}")
    said = [v for v in VERDICTS if message(v, record) in proc.stdout + proc.stderr]
    if said != [want]:
        found.append(f"terminal message says {said}, expected {want}")
    return found


def main():
    bad, held = [], {v: [] for v in VERDICTS}
    with tempfile.TemporaryDirectory() as tmp:
        for case in itertools.product(SUBMISSION, REPEAT, COLLECTOR):
            root = sandbox(tmp)
            proc = campaign(root, case)
            found = problems(root, case, proc)
            if found:
                bad.append((case, proc, found))
            else:
                held[expected(case)[0]].append(case)
    for case, proc, found in bad:
        print(f"FAIL [{describe(case)}]: " + "; ".join(found))
        print(f"---- output ----\n{proc.stdout}{proc.stderr}", end="")
    for verdict in VERDICTS:
        if not held[verdict]:
            continue
        cases = held[verdict]
        which = (f"1 combination ({describe(cases[0])})" if len(cases) == 1
                 else f"{len(cases)} combinations, every submission, repeat and collector status other than "
                      f"the PASS and ROWS_FAIL ones")
        print(f"ok [{verdict}]: {which}: exit {expected(cases[0])[1]}, record.txt result={verdict}, "
              f"terminal message {message(verdict)!r}")
    if bad:
        print(f"selftest: {len(bad)} of {len(bad) + sum(len(c) for c in held.values())} mc campaign-verdict "
              f"cases fail")
        return 1
    print("selftest: all mc campaign-verdict cases pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
