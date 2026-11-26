#!/usr/bin/env python3
"""Replay test for the trip-point rows of collect.py -- no test framework needed.

    python3 -I sim/gpio-bi_t/selftest.py

collect.py merges the three per-DVDD requests of a transfer deck into one report whose
corner IDs repeat across the supplies (`fs/novdd/125C` exists at 2.97, 3.3 and 3.63 V).
A VIL/VIH row is selected on Vt / DVDD, so the published ratio has to be divided by the
selected point's own DVDD. The first collector divided by the first supply carrying the
corner ID instead (issue #151): a lower trip selected at 3.63 V was published against
2.97 V, and the 3.3 V, CS=0 VIL row read 0.325 (a pass) where the measurement gives
0.266 (a miss).

The case runs the production collector over the archived `klt sim` reports of
`records/20261023T173526Z` into a temporary directory -- no PDK, no ngspice, nothing
written into the repository -- and checks what it writes against what is committed:

  1. replay of the characterization run: results.tsv comes back byte for byte, and the
     comparison table differs from the committed one in exactly the four "VIL as lower
     trip" rows. They read 0.242 / 0.205 at 5 V and 0.266 / 0.230 at 3.3 V (CS=0 / CS=1)
     at their unchanged binding corners, and all four miss the 0.3*DVDD target; the
     upper trip and every other row are unchanged.

The replay case fails on the collector before the fix (lower-trip rows 0.296 / 0.251 /
0.325 / 0.281, the third one a pass); that is the point of the test.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
COLLECT = os.path.join(HERE, "collect.py")
RECORDS = os.path.join(HERE, "records")
ARCHIVE = "20261023T173526Z"
SPEC = os.path.join(REPO, "spec", "io-ring.md")
LOWER = "VIL as lower trip Vt-"
#: (mode, parameter) -> published ratio of the lower trip at the selected point's own DVDD
EXPECTED = {("5v", f"{LOWER}, CS=0"): "0.242*DVDD", ("5v", f"{LOWER}, CS=1"): "0.205*DVDD",
            ("3v3", f"{LOWER}, CS=0"): "0.266*DVDD", ("3v3", f"{LOWER}, CS=1"): "0.230*DVDD"}


def collect(tmp, meta):
    """Run the production collector over the archived reports into a fresh dir under tmp."""
    out = tempfile.mkdtemp(prefix="bi_t-selftest-", dir=tmp)
    proc = subprocess.run([sys.executable, "-I", COLLECT, out, os.path.join(RECORDS, ARCHIVE, "klt"),
                          SPEC, meta], capture_output=True, text=True, check=False)
    return out, proc


def table(path):
    """The comparison table of a record.md: one tuple of stripped cells per row, in order."""
    rows, inside = [], False
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not inside:
            inside = line.startswith("| Mode | Parameter |")
            continue
        if not line.startswith("|"):
            break
        rows.append(tuple(c.strip() for c in line.strip().strip("|").split("|")))
    return rows[1:]


def same_bytes(a, b):
    with open(a, "rb") as fa, open(b, "rb") as fb:
        return fa.read() == fb.read()


def fail(label, *problems):
    print(f"FAIL [{label}]: " + "; ".join(problems))
    return False


def ok(label, note):
    print(f"ok [{label}]: {note}")
    return True


def case_replay(tmp):
    out, proc = collect(tmp, os.path.join(RECORDS, ARCHIVE, "meta.txt"))
    if proc.returncode != 0:
        return fail("replay", f"collect.py rc={proc.returncode}", proc.stderr.strip())
    problems = []
    if not same_bytes(os.path.join(out, "results.tsv"), os.path.join(RECORDS, ARCHIVE, "results.tsv")):
        problems.append("results.tsv differs from the archived one: no measured point may move")
    got = table(os.path.join(out, "record.md"))
    was = table(os.path.join(RECORDS, ARCHIVE, "record.md"))
    if [r[:2] for r in got] != [r[:2] for r in was]:
        return fail("replay", f"table rows {[(r[0], r[1]) for r in got]} differ from the archived "
                             f"{[(r[0], r[1]) for r in was]}", *problems)
    new = {(r[0], r[1]): r for r in got}
    old = {(r[0], r[1]): r for r in was}
    lower = {k: r for k, r in new.items() if k[1].startswith(LOWER)}
    if set(lower) != set(EXPECTED):
        problems.append(f"lower-trip rows {sorted(set(lower) ^ set(EXPECTED))} are not the expected four")
    for key, want in EXPECTED.items():
        if key not in lower:
            continue
        row, before = lower[key], old[key]
        if row[:3] != before[:3] or row[4:6] != before[4:6]:
            problems.append(f"{key[0]} {key[1]}: target, binding or corner moved: {before} -> {row}")
        if row[3] != want:
            problems.append(f"{key[0]} {key[1]}: {row[3]}, expected {want}")
        if row[6] != "NO":
            problems.append(f"{key[0]} {key[1]}: verdict {row[6]}, expected NO")
    others = [f"{k[0]} {k[1]}" for k in new if k not in EXPECTED and new[k] != old[k]]
    if others:
        problems.append(f"rows other than the four lower-trip ones changed: {others}")
    if problems:
        return fail("replay", *problems)
    return ok("replay", f"{len(got)} rows: results.tsv identical, the four lower-trip rows read "
                        f"0.242 / 0.205 / 0.266 / 0.230*DVDD and miss, {len(got) - len(EXPECTED)} others unchanged")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        if not case_replay(tmp):
            return 1
    print("selftest: all bi_t collector cases pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
