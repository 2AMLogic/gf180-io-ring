#!/usr/bin/env python3
"""Check the Monte Carlo reports of a record dir and turn them into `klt yield` envelopes.

    python3 -I collect.py <record-dir> --yield-cmd "<klt with klt_yield_native>"   nominal campaign
    python3 -I collect.py <record-dir> --yield-cmd CMD --negative KIND             negative control
                                                                                   (rx | pull | nostat)

Nominal: for every request in <record-dir>/requests, <record-dir>/klt/<stem>.json must be a
`klt sim` report with n samples, none errored, every measurement finite and with non-zero
spread (a zero-variance set means the statistics switches never reached the devices; that is
refused, never graded). Each report goes through `klt yield` -> yield/<stem>.json; xfer and
pull decks are re-derived with their seeded known-bad variant (`klt yield-samples`) so the
envelope carries a `negative_control`, which must read `detected` for the measurement it
targets (hyst for rx, r_pulldown for pull). record.md gets one row per (spec row, temperature).
Exit 0: data valid and every row meets its target_yield. Exit 3: data valid, some row misses
its limit (reported, not hidden). Exit 1: invalid data / harness failure.

--negative KIND: evaluates the known-bad campaign on its own against the same limits and exits
non-zero because rows must fail (rx, pull) or the zero-variance guard must trip (nostat).
"""
import glob
import json
import math
import os
import shlex
import statistics
import subprocess
import sys

CONTROL = {"xfer": ("rx", "hyst"), "pulldown": ("pull", "r_pulldown")}  # pull-up is nominally failing: no control can show
ROW = {  # measurement -> spec row id prefix and wording
    "vt_plus": ("vih", "VIH as upper trip Vt+ (reads high from 0.7*DVDD)"),
    "vt_minus": ("vil", "VIL as lower trip Vt- (reads low up to 0.3*DVDD)"),
    "hyst": ("hyst", "input hysteresis"),
    "vol": ("vol", "VOL"), "voh_drop": ("voh", "DVDD - VOH"),
    "r_pullup": ("pullup", "pull-up equivalent R"), "r_pulldown": ("pulldown", "pull-down equivalent R"),
}


def load(p):
    with open(p) as f:
        return json.load(f)


REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def rel(p):
    """Path as seen from the repo root: the envelopes record the samples path they were given, and
    a committed envelope must name it repo-relative for `klt signoff` to re-hash it anywhere."""
    return os.path.relpath(os.path.abspath(p), REPO)


def run_yield(cmd, args):
    args = [rel(a) if os.path.exists(a) else a for a in args]
    r = subprocess.run(cmd + ["yield"] + args, capture_output=True, text=True, cwd=REPO)
    out = r.stdout
    try:
        return r.returncode, json.loads(out[out.index("{"):])
    except ValueError:
        return r.returncode, {"error": {"message": (r.stderr or out)[-400:]}}


def check_report(path, expect_n):
    """Problems with one sim report; empty list = usable sample set."""
    rep = load(path)
    corners = rep.get("corners") or []
    bad = []
    if len(corners) != expect_n:
        bad.append(f"{len(corners)} samples, expected {expect_n}")
    names = {}
    for c in corners:
        if c.get("status") == "error":
            bad.append(f"{c.get('corner_id')}: errored {[d.get('code') for d in c.get('diagnostics', [])]}")
            continue
        for m in c.get("measurements", []):
            v = m.get("value")
            if not isinstance(v, (int, float)) or not math.isfinite(v):
                bad.append(f"{c.get('corner_id')}: {m['name']} missing or non-finite ({v!r})")
            else:
                names.setdefault(m["name"], []).append(v)
    for n, vs in names.items():
        if len(set(vs)) < 2 or statistics.pstdev(vs) == 0:
            bad.append(f"{n}: zero variance over {len(vs)} samples (sw_stat_* did not reach the devices)")
    return bad[:6], rep


def table_row(stem, m, ctl):
    y = m["yield"]["empirical"]
    ci = y["confidence_interval"]
    cap = m["capability"]
    return {"stem": stem, "name": m["name"], "n": m["n"], "mean": m["distribution"]["mean"],
            "std": m["distribution"]["stddev"], "limits": m["limits"], "yield": y["estimate"],
            "ci": (ci["low"], ci["high"]), "cpk": cap.get("cpk"), "size": m["sample_size"]["verdict"],
            "status": m["status"], "control": ctl}


def main():
    a = sys.argv[1:]
    if len(a) < 3 or a[1] != "--yield-cmd":
        sys.exit(__doc__)
    rec, cmd = a[0], shlex.split(a[2])
    neg = a[4] if len(a) == 5 and a[3] == "--negative" else None
    reqs = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(rec, "requests", "*.json")))
    if not reqs:
        print("collect: FAIL: no requests in the record dir", file=sys.stderr)
        return 1
    os.makedirs(os.path.join(rec, "yield"), exist_ok=True)
    problems, rows, controls = [], [], []
    for stem in reqs:
        deck = stem.split("_")[0]
        n = load(os.path.join(rec, "requests", stem + ".json"))["monte_carlo"]["n"]
        rpath = os.path.join(rec, "klt", stem + ".json")
        if not os.path.exists(rpath):
            problems.append(f"{stem}: no report")
            continue
        bad, _ = check_report(rpath, n)
        problems += [f"{stem}: {b}" for b in bad]
        if bad:
            continue
        rc, env = run_yield(cmd, [rpath, "--format", "json"])
        if "measurements" not in env:
            problems.append(f"{stem}: klt yield failed: {env.get('error', {}).get('message')}")
            continue
        json.dump(env, open(os.path.join(rec, "yield", stem + ".json"), "w"), indent=2)
        ctl = {}
        npath = os.path.join(rec, "negative", stem + ".json")
        if os.path.exists(npath) and deck in CONTROL:
            # the seeded known-bad variant's draw, graded against the nominal limits, for the one
            # measurement the defect targets (klt yield-samples keeps only that measurement)
            kind, target = CONTROL[deck]
            r = subprocess.run(cmd + ["yield-samples", rel(rpath), "--negative-control", rel(npath),
                               "--measurement", target, "--description",
                               f"seeded mis-sized variant '{kind}', same seed", "--format", "json"],
                               capture_output=True, text=True, cwd=REPO)
            if r.returncode != 0:
                problems.append(f"{stem}: yield-samples failed: {r.stderr[-300:]}")
                continue
            sdoc = os.path.join(rec, "yield", f"{stem}.{target}-samples.json")
            open(sdoc, "w").write(r.stdout)
            rc2, cenv = run_yield(cmd, [sdoc, "--format", "json"])
            if "measurements" not in cenv:
                problems.append(f"{stem}: klt yield (control) failed: {cenv.get('error', {}).get('message')}")
                continue
            json.dump(cenv, open(os.path.join(rec, "yield", f"{stem}.{target}-control.json"), "w"), indent=2)
            ctl[target] = cenv["measurements"][0]["negative_control"]["verdict"]
            controls.append((stem, target, ctl[target]))
            if ctl[target] != "detected":
                problems.append(f"{stem}: negative control on {target} is {ctl[target]}, must be detected")
        for m in env["measurements"]:
            if m["sample_size"]["verdict"] == "insufficient" and not neg:
                problems.append(f"{stem}: {m['name']} sample_size insufficient")
            rows.append(table_row(stem, m, ctl.get(m["name"])))
    if neg == "nostat":
        for p in problems:
            print("collect: refused: " + p, file=sys.stderr)
        return 1 if problems else 0
    if problems:
        for p in problems[:30]:
            print("collect: FAIL: " + p, file=sys.stderr)
        return 1
    miss = [r for r in rows if r["status"] != "pass"]
    with open(os.path.join(rec, "results.tsv"), "w") as f:
        f.write("stem\tmeasurement\tn\tmean\tstddev\tmin\tmax\tyield\tci_low\tci_high\tcpk\tsample_size\tstatus\tnegative_control\n")
        for r in rows:
            f.write("\t".join(str(x) for x in (r["stem"], r["name"], r["n"], r["mean"], r["std"],
                    r["limits"].get("min", ""), r["limits"].get("max", ""), r["yield"], r["ci"][0],
                    r["ci"][1], r["cpk"], r["size"], r["status"], r["control"] or "")) + "\n")
    md = ["| Request | Measurement | n | mean | stddev | limits | yield (95 % CI) | Cpk | sample size | target 0.98 | negative control |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lim = ", ".join(f"{k} {r['limits'][k]:g}" for k in ("min", "max") if k in r["limits"])
        cpk = "n/a" if r["cpk"] is None else f"{r['cpk']:.2f}"
        md.append(f"| `{r['stem']}` | {r['name']} | {r['n']} | {r['mean']:.5g} | {r['std']:.3g} | {lim} | "
                  f"{r['yield']:.3f} ({r['ci'][0]:.3f}..{r['ci'][1]:.3f}) | {cpk} | {r['size']} | "
                  f"{r['status']} | {r['control'] or '-'} |")
    open(os.path.join(rec, "table.md"), "w").write("\n".join(md) + "\n")
    print(f"collect: {len(reqs)} requests, {len(rows)} measurement rows; {len(miss)} miss their target yield")
    for r in miss:
        print(f"collect: row misses target: {r['stem']} {r['name']} yield {r['yield']:.3f}")
    if neg:  # known-bad campaign evaluated on its own: it must fail its limits
        return 1 if miss else 0
    return 3 if miss else 0


if __name__ == "__main__":
    sys.exit(main())
