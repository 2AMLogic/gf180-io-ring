#!/usr/bin/env python3
"""Replay test for the trip-point rows and the supply column of collect.py -- no test framework needed.

    python3 -I sim/gpio-bi_t/selftest.py

collect.py merges the three per-DVDD requests of a transfer deck into one report whose
corner IDs repeat across the supplies (`fs/novdd/125C` exists at 2.97, 3.3 and 3.63 V).
A VIL/VIH row is selected on Vt / DVDD, so the published ratio has to be divided by the
selected point's own DVDD. The first collector divided by the first supply carrying the
corner ID instead (issue #151): a lower trip selected at 3.63 V was published against
2.97 V, and the 3.3 V, CS=0 VIL row read 0.325 (a pass) where the measurement gives
0.266 (a miss). For the same reason its results.tsv carried no supply: with six columns,
`xfer_cs0` at 5 V listed `fs/novdd/125C` Vt- three times (1.134, 1.23 and 1.331 V at
4.5, 5.0 and 5.5 V), told apart by row order alone (issue #152). Every row now carries
its supply in a seventh column, `dvdd`.

The cases run the production collector over the archived `klt sim` reports of
`records/20261023T173526Z` into a temporary directory -- no PDK, no ngspice, nothing
written into the repository -- and check what it writes against what is committed:

  1. replay of the characterization run: results.tsv comes back byte for byte on its six
     archived columns, and the comparison table differs from the committed one in exactly
     the four "VIL as lower trip" rows. They read 0.242 / 0.205 at 5 V and 0.266 / 0.230
     at 3.3 V (CS=0 / CS=1) at their unchanged binding corners, and all four miss the
     0.3*DVDD target; the upper trip and every other row are unchanged;
  2. `records/20261126T170416Z`, the committed correction (the same reports re-collected
     with the fixed collector, no simulation), regenerates byte for byte from its own
     meta.txt and links the record it corrects: results.tsv on its six archived columns,
     record.md once the one sentence that describes `dvdd` is taken out;
  3. the `dvdd` column: every row equals what its source report gives once the report is
     paired with the supply its request stem encodes (`4v50` is 4.5 V), and the repeated
     corner above reads 1.134 V at 4.5 V, 1.23 V at 5.0 V and 1.331 V at 5.5 V. Trading
     the supplies of two of those rows leaves the six archived columns as they were, and
     must still fail this case.

Both committed records predate the `dvdd` column, which is why cases 1 and 2 compare on
the six archived columns. Case 1 fails on the collector before the #151 fix (lower-trip
rows 0.296 / 0.251 / 0.325 / 0.281, the third one a pass) and case 3 on the collector
before the #152 fix (six columns, no supply); that is the point of the tests. Case 2
keeps the committed correction from going stale if the collector moves again.
"""
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
COLLECT = os.path.join(HERE, "collect.py")
RECORDS = os.path.join(HERE, "records")
ARCHIVE = "20261023T173526Z"
CORRECTED = "20261126T170416Z"
SPEC = os.path.join(REPO, "spec", "io-ring.md")
LOWER = "VIL as lower trip Vt-"
EXPECTED = {("5v", f"{LOWER}, CS=0"): "0.242*DVDD", ("5v", f"{LOWER}, CS=1"): "0.205*DVDD",
            ("3v3", f"{LOWER}, CS=0"): "0.266*DVDD", ("3v3", f"{LOWER}, CS=1"): "0.230*DVDD"}
COLUMNS = ["deck", "mode", "corner_id", "measurement", "value", "unit", "dvdd"]
DVDD_SENTENCE = ("The corner ID repeats across the three DVDD requests of a deck and mode, so every "
                 "`results.tsv` row carries its supply: the `dvdd` column is the DVDD in volts for that "
                 "measurement. ")
EXAMPLE = ("xfer_cs0", "5v", "fs/novdd/125C", "vt_minus")
EXAMPLE_DVDD = {1.134: 4.5, 1.23: 5.0, 1.331: 5.5}
TRADED = (1.134, 1.331)


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


def cells(path):
    """A tab-separated file as one tuple of cells per line, header first."""
    with open(path, encoding="utf-8", newline="") as f:
        return [tuple(line.rstrip("\r\n").split("\t")) for line in f]


def project(src, dst):
    """Write results.tsv src onto its first six columns, the archived ones; every other byte stays."""
    with open(src, "rb") as f, open(dst, "wb") as out:
        for line in f:
            eol = line[len(line.rstrip(b"\r\n")):]
            out.write(b"\t".join(line[:len(line) - len(eol)].split(b"\t")[:6]) + eol)


def without(src, dst, text):
    """Write src to dst minus every copy of text, every other byte kept; returns how many went."""
    with open(src, encoding="utf-8", newline="") as f:
        body = f.read()
    with open(dst, "w", encoding="utf-8", newline="") as f:
        f.write(body.replace(text, ""))
    return body.count(text)


def trade(src, dst):
    """Copy results.tsv src to dst with the dvdd cells traded between the two example-corner rows
    that hold TRADED; every other byte stays. False unless each row is there exactly once."""
    key = "\t".join(EXAMPLE).encode() + b"\t"
    with open(src, "rb") as f:
        lines = f.read().split(b"\n")
    at = []
    for v in TRADED:
        hit = [i for i, line in enumerate(lines) if line.startswith(key + str(v).encode() + b"\t")]
        if len(hit) != 1:
            return False
        at.append(hit[0])
    first, second = (lines[i].rsplit(b"\t", 1) for i in at)
    lines[at[0]], lines[at[1]] = first[0] + b"\t" + second[1], second[0] + b"\t" + first[1]
    with open(dst, "wb") as f:
        f.write(b"\n".join(lines))
    return True


def source_rows():
    """What the archived requests must give: a Counter of complete results.tsv rows, one per
    measurement, the supply read from each request stem (`4v50` is 4.5 V) and not from the
    collector; with the PVT points and requests they come from."""
    archived = os.path.join(RECORDS, ARCHIVE)
    with open(os.path.join(archived, "requests.list")) as f:
        stems = f.read().split()
    rows, points = Counter(), 0
    for stem in stems:
        deck, mode, supply = stem.rsplit("_", 2)
        with open(os.path.join(archived, "klt", stem, "report.json")) as f:
            rep = json.load(f)
        points += len(rep["corners"])
        for c in rep["corners"]:
            for m in c["measurements"]:
                rows[(deck, mode, c["corner_id"], m["name"], repr(m["value"]), m.get("unit", ""),
                      repr(float(supply.replace("v", "."))))] += 1
    return rows, points, len(stems)


def mismatch(got, want):
    """Problems of the results.tsv rows `got` against the source-request rows `want`, counted as
    multisets: a value that repeats is compared as many times as it occurs."""
    lost, extra = want - got, got - want
    problems = []
    if lost:
        problems.append(f"{sum(lost.values())} row(s) of the source requests are missing from results.tsv, "
                        f"e.g. {next(iter(lost))}")
    if extra:
        problems.append(f"{sum(extra.values())} row(s) of results.tsv match no source request at their "
                        f"supply, e.g. {next(iter(extra))}")
    return problems


def legacy_columns(tsv, archive):
    """Problems of a replayed results.tsv against a six-column archive: the header must be the
    archived columns followed by `dvdd`, and the first six columns must reproduce the archive."""
    problems = []
    head = cells(tsv)[:1]
    if head != [tuple(COLUMNS)]:
        problems.append(f"results.tsv header {list(head[0]) if head else []}, expected {COLUMNS}")
    six = os.path.join(os.path.dirname(tsv), "results.six.tsv")
    project(tsv, six)
    if not same_bytes(six, archive):
        problems.append("results.tsv without its dvdd column differs from records/"
                        f"{os.path.basename(os.path.dirname(archive))}/results.tsv: a header, value, unit "
                        "or row order moved")
    return problems


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
    problems = legacy_columns(os.path.join(out, "results.tsv"), os.path.join(RECORDS, ARCHIVE, "results.tsv"))
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
    return ok("replay", f"{len(got)} rows: results.tsv identical on its six archived columns, the four "
                        f"lower-trip rows read 0.242 / 0.205 / 0.266 / 0.230*DVDD and miss, "
                        f"{len(got) - len(EXPECTED)} others unchanged")


def case_supply(tmp):
    out, proc = collect(tmp, os.path.join(RECORDS, ARCHIVE, "meta.txt"))
    if proc.returncode != 0:
        return fail("supply", f"collect.py rc={proc.returncode}", proc.stderr.strip())
    archived = os.path.join(RECORDS, ARCHIVE, "results.tsv")
    tsv = os.path.join(out, "results.tsv")
    want, points, requests = source_rows()
    got = Counter(cells(tsv)[1:])
    problems = legacy_columns(tsv, archived)
    per_supply = sorted(Counter(r[6] for r in want.elements()).values())
    if (requests, points, per_supply) != (48, 720, [210] * 6):
        problems.append(f"the archive has {requests} requests, {points} PVT points and {per_supply} rows per "
                        "supply, expected 48, 720 and 210 at each of six")
    problems += mismatch(got, want)
    found = {float(r[4]): float(r[6]) for r in got if r[:4] == EXAMPLE and len(r) == len(COLUMNS)}
    if found != EXAMPLE_DVDD:
        problems.append(f"{'/'.join(EXAMPLE)} reads {found}, expected {EXAMPLE_DVDD}")
    traded = os.path.join(out, "results.traded.tsv")
    if not trade(tsv, traded):
        problems.append(f"the rows of {'/'.join(EXAMPLE)} at {TRADED[0]} V and {TRADED[1]} V are not in "
                        "results.tsv once each")
    else:
        six = os.path.join(out, "results.traded.six.tsv")
        project(traded, six)
        if not same_bytes(six, archived):
            problems.append("results.tsv with two supplies traded no longer matches the six archived columns")
        if not mismatch(Counter(cells(traded)[1:]), want):
            problems.append(f"results.tsv with the supplies of {TRADED[0]} V and {TRADED[1]} V traded passes "
                            "the check")
    if problems:
        return fail("supply", *problems)
    return ok("supply", f"{sum(want.values())} rows equal the {requests} source requests at the supply of their "
                        f"stem; {'/'.join(EXAMPLE)} reads 1.134 / 1.23 / 1.331 V at 4.5 / 5.0 / 5.5 V; trading "
                        "two of them fails the check with the six archived columns unchanged")


def case_corrected(tmp):
    rec = os.path.join(RECORDS, CORRECTED)
    out, proc = collect(tmp, os.path.join(rec, "meta.txt"))
    if proc.returncode != 0:
        return fail("corrected", f"collect.py rc={proc.returncode}", proc.stderr.strip())
    problems = legacy_columns(os.path.join(out, "results.tsv"), os.path.join(rec, "results.tsv"))
    before = os.path.join(out, "record.before.md")
    n = without(os.path.join(out, "record.md"), before, DVDD_SENTENCE)
    if n != 1:
        problems.append(f"the dvdd sentence appears {n} times in record.md, expected exactly once")
    if not same_bytes(before, os.path.join(rec, "record.md")):
        problems.append("record.md without the dvdd sentence does not regenerate from the archived reports")
    with open(os.path.join(rec, "record.md"), encoding="utf-8") as f:
        if f"records/{ARCHIVE}/record.md" not in f.read():
            problems.append("record.md does not link the record it corrects")
    if problems:
        return fail("corrected", *problems)
    return ok("corrected", f"records/{CORRECTED} regenerates byte for byte from records/{ARCHIVE} (results.tsv "
                           "on its six archived columns, record.md without its one dvdd sentence) and links it")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        replay, supply, corrected = case_replay(tmp), case_supply(tmp), case_corrected(tmp)
        if not (replay and supply and corrected):
            return 1
    print("selftest: all bi_t collector cases pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
