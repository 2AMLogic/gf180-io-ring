#!/usr/bin/env python3
"""Negative tests for the citation join in build.py -- no test framework needed.

    python3 -I sim/characterization/selftest.py

Three assertions, each pointing build.py at a sandboxed copy of the repository
(every top-level entry symlinked through except manifests/, which is a real
directory holding a copy of the manifest that may be mutated):

  1. the committed manifest still builds (rc=0) -- guards against the refusal
     becoming over-eager on the benign unmatched population (the six
     yield/xfer_*_<T>.json files carry hyst_* measurements cited through their
     .hyst-control.json companions), and against it breaking any of the
     declared (exact or ALIAS) placements;
  2. a multi-base mis-citation (the pad-clamp envelope re-pointed at the rail
     row) is refused with a non-zero exit naming the orphan row, the unplaced
     measurements and both remedies;
  3. the single-base shape (the rail envelope, whose one limited measurement
     makes the pile-on look unambiguous, re-pointed at the pad row) is refused
     the same way.

Before the single-orphan-row pairing rung was removed, both mis-citations built
at exit 0 and rendered one clamp's number against the other clamp's limit, so
assertions 2 and 3 fail on the unfixed builder -- that is the point of the test.

Writes nothing into the repository: outputs go to a temp directory, and the
sandbox it reads from is a symlink farm under one.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
BUILD = os.path.join(HERE, "build.py")
MANIFEST = "manifests/gf180-io-ring.json"

#: (item, citation-file suffix) for the two ESD envelopes the mis-citations re-point
ESD_PAD = ("5", "klt/esd_pad.json")
ESD_RAIL = ("5", "klt/esd_rail.json")


def sandbox(tmp):
    """A repo-root lookalike: everything symlinked through except manifests/."""
    root = tempfile.mkdtemp(prefix="char-selftest-", dir=tmp)
    for entry in os.listdir(REPO):
        if entry == "manifests":
            continue
        os.symlink(os.path.join(REPO, entry), os.path.join(root, entry))
    os.mkdir(os.path.join(root, "manifests"))
    with open(os.path.join(REPO, MANIFEST), encoding="utf-8") as f:
        man = json.load(f)
    write_manifest(root, man)
    return root, man


def run_build(root, tmp):
    out = tempfile.mkdtemp(prefix="char-selftest-out-", dir=tmp)
    return subprocess.run(
        [sys.executable, "-I", BUILD, root, "--out", out],
        capture_output=True, text=True, check=False)


def repoint(man, item, suffix, rows):
    for cit in man["evidence"][item]:
        if cit["file"].endswith(suffix):
            cit["rows"] = rows
            return
    raise AssertionError(f"no item-{item} citation ends with {suffix}")


def drop(man, item, suffix):
    cits = man["evidence"][item]
    man["evidence"][item] = [c for c in cits if not c["file"].endswith(suffix)]
    if len(man["evidence"][item]) == len(cits):
        raise AssertionError(f"no item-{item} citation ends with {suffix}")


def write_manifest(root, man):
    path = os.path.join(root, MANIFEST)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(man, f, indent=2)
        f.write("\n")


def expect_refuse(label, proc, orphan_row, unplaced):
    problems = []
    if proc.returncode == 0:
        problems.append(f"exit 0 -- the mis-citation was absorbed, not refused")
    for needle in [orphan_row] + unplaced + ["ALIAS", MANIFEST]:
        if needle not in (proc.stderr + proc.stdout):
            problems.append(f"message does not name {needle!r}")
    if problems:
        print(f"FAIL [{label}]: " + "; ".join(problems))
        print(f"---- output ----\n{proc.stdout}{proc.stderr}")
        return False
    print(f"ok [{label}]: refused with rc={proc.returncode}")
    return True


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root, _ = sandbox(tmp)
        proc = run_build(root, tmp)
        if proc.returncode != 0:
            print(f"FAIL [unmutated]: rc={proc.returncode} -- the committed manifest "
                  f"must still build\n{proc.stdout}{proc.stderr}")
            return 1
        print("ok [unmutated]: committed manifest builds, rc=0")

        root, man = sandbox(tmp)
        drop(man, *ESD_RAIL)
        repoint(man, *ESD_PAD, rows=["esd_rail_clamp"])
        write_manifest(root, man)
        if not expect_refuse("multi-base", run_build(root, tmp), "esd_rail_clamp",
                             ["esd_pad_up", "esd_pad_dn"]):
            return 1

        root, man = sandbox(tmp)
        drop(man, *ESD_PAD)
        repoint(man, *ESD_RAIL, rows=["esd_pad_clamp"])
        write_manifest(root, man)
        if not expect_refuse("single-base", run_build(root, tmp), "esd_pad_clamp",
                             ["esd_rail"]):
            return 1

    print("selftest: all join-refusal cases pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
