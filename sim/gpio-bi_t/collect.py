#!/usr/bin/env python3
"""Check the klt sim reports of a bi_t run and write the record.

    python3 -I collect.py <outdir> <klt-outdir> <spec/io-ring.md> <meta.txt>   full run
    python3 -I collect.py --probe <report.json>                                negative control

Full run: <klt-outdir>/<stem>/report.json for each of the 48 requests in
<outdir>/requests. Exit 0 only if every request exists, has all 15 corners (45 per deck and mode over the 3 DVDD values), every
corner passed, and every declared measurement is present and finite in every corner
(resistances and capacitances also > 0, times > 0). A failed measure fails the run:
no blank or NaN row is ever written. The comparison against the spec targets is
data; a target that is missed does not fail the run (these are reference values).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from gpio_common import finite, limitation, load, vlabel  # noqa: E402

DECKS = ["vol", "voh", "edges", "pullup", "pulldown", "cap", "xfer_cs0", "xfer_cs1"]
MODES = ["5v", "3v3"]
EXPECT = {  # measurement names per deck
    "vol": ["vol"], "voh": ["voh", "voh_drop"], "edges": ["t_rise", "t_fall"],
    "pullup": ["r_pullup"], "pulldown": ["r_pulldown"], "cap": ["c_pad"],
    "xfer_cs0": ["vt_plus", "vt_minus", "hyst"], "xfer_cs1": ["vt_plus", "vt_minus", "hyst"],
}
POSITIVE = {"r_pullup", "r_pulldown", "c_pad", "t_rise", "t_fall", "vol"}
CORNERS = 45
DVDDS = {"5v": [4.5, 5.0, 5.5], "3v3": [2.97, 3.3, 3.63]}


def merged(kltout, deck, mode):
    """The three per-DVDD requests of (deck, mode) as one report with 45 corners."""
    out = {"corners": [], "environment": {}, "_parts": []}
    for v in DVDDS[mode]:
        stem = f"{deck}_{mode}_{vlabel(v)}"
        rep = load(os.path.join(kltout, stem, "report.json"))
        if "_unreadable" in rep:
            out["_unreadable"] = f"{stem}: {rep['_unreadable']}"
            return out
        for c in rep.get("corners", []):
            c["params"] = {"dvdd": v}
        out["corners"] += rep.get("corners", [])
        e = rep.get("environment", {})
        out["environment"].setdefault("engine_version", e.get("engine_version"))
        out["_parts"].append((stem, (e.get("remote") or {}).get("job_id"), e.get("engine_host")))
    return out


def check_report(rep, names, ncorners, tag):
    """Return a list of problems for one report."""
    bad = []
    if "_unreadable" in rep:
        return [f"{tag}: report unreadable: {rep['_unreadable']}"]
    corners = rep.get("corners") or []
    if len(corners) != ncorners:
        bad.append(f"{tag}: {len(corners)} corners, expected {ncorners}")
    for c in corners:
        cid = c.get("corner_id")
        if c.get("status") != "pass":
            codes = [d.get("code") for d in c.get("diagnostics", [])]
            bad.append(f"{tag} {cid}: status {c.get('status')} {codes}")
            continue
        got = {m["name"]: m.get("value") for m in c.get("measurements", [])}
        for n in names:
            v = got.get(n)
            if not finite(v):
                bad.append(f"{tag} {cid}: measurement {n} missing or non-finite ({v!r})")
            elif n in POSITIVE and v <= 0:
                bad.append(f"{tag} {cid}: measurement {n} = {v} not > 0")
    return bad


def points(rep, name):
    out = []
    for c in rep["corners"]:
        for m in c["measurements"]:
            if m["name"] == name:
                out.append((c["corner_id"], c["params"]["dvdd"], m["value"]))
    return out


def worst(rep, name, key=lambda p: p[2], high=True):
    pts = points(rep, name)
    return (max if high else min)(pts, key=key)


def nominal(rep, name):
    for cid, dvdd, v in points(rep, name):
        if cid.startswith("typical/") and cid.endswith("/25C") and abs(dvdd - NOMINAL[rep["_mode"]]) < 1e-9:
            return cid, v
    sys.exit(f"collect: no nominal point for {name}")


NOMINAL = {"5v": 5.0, "3v3": 3.3}


def fmt(v, unit):
    scale = {"s": (1e9, "ns"), "F": (1e12, "pF"), "ohm": (1e-3, "kohm"), "V": (1, "V")}[unit]
    return f"{v * scale[0]:.4g} {scale[1]}"


def table(reps):
    """One row per spec parameter and mode: foundry value at its binding corner."""
    rows = []
    for mode in MODES:
        nom = NOMINAL[mode]
        iload = "4 mA" if mode == "5v" else "2 mA"
        vol_lim = 0.4
        voh_lim = 0.5 if mode == "5v" else 0.4
        rise_lim = 5e-9 if mode == "5v" else 8e-9
        hyst_lim = 0.4 if mode == "5v" else 0.25
        r = {d: reps[(d, mode)] for d in DECKS}
        for d in DECKS:
            r[d]["_mode"] = mode
        cid, _, v = worst(r["vol"], "vol")
        rows.append((mode, f"VOL at {iload}", f"<= {vol_lim} V", fmt(v, "V"), "max", cid, v <= vol_lim))
        cid, _, v = worst(r["voh"], "voh_drop")
        rows.append((mode, f"VOH at {iload} (DVDD - VOH)", f"<= {voh_lim} V", fmt(v, "V"),
                     "max drop", cid, v <= voh_lim))
        cid, _, v = worst(r["edges"], "t_rise")
        rows.append((mode, "rise 10-90 % into 15 pF", f"<= {rise_lim * 1e9:g} ns", fmt(v, "s"),
                     "max", cid, v <= rise_lim))
        cid, _, v = worst(r["edges"], "t_fall")
        rows.append((mode, "fall 90-10 % into 15 pF", f"<= {rise_lim * 1e9:g} ns", fmt(v, "s"),
                     "max", cid, v <= rise_lim))
        for cs in (0, 1):
            x = r[f"xfer_cs{cs}"]
            cid, _, v = worst(x, "vt_minus", key=lambda p: p[2] / p[1], high=False)
            lo = v / dv(x, cid)
            rows.append((mode, f"VIL as lower trip Vt-, CS={cs}", ">= 0.3*DVDD (reads low up to 0.3*DVDD)",
                         f"{lo:.3f}*DVDD", "min", cid, lo >= 0.3))
            cid, _, v = worst(x, "vt_plus", key=lambda p: p[2] / p[1])
            hi = v / dv(x, cid)
            rows.append((mode, f"VIH as upper trip Vt+, CS={cs}", "<= 0.7*DVDD (reads high from 0.7*DVDD)",
                         f"{hi:.3f}*DVDD", "max", cid, hi <= 0.7))
            cid, _, v = worst(x, "hyst", high=False)
            rows.append((mode, f"hysteresis, CS={cs}", f">= {hyst_lim} V", fmt(v, "V"),
                         "min", cid, v >= hyst_lim))
        for d, name, label in (("pullup", "r_pullup", "pull-up"), ("pulldown", "r_pulldown", "pull-down")):
            ncid, nv = nominal(r[d], name)
            lo = worst(r[d], name, high=False)
            hi = worst(r[d], name)
            rows.append((mode, f"{label} equivalent R (PAD at DVDD/2)", "25-100 kohm at nominal",
                         f"{fmt(nv, 'ohm')} nominal; {fmt(lo[2], 'ohm')} .. {fmt(hi[2], 'ohm')} over the grid",
                         "nominal", ncid, 25e3 <= nv <= 100e3))
        cid, _, v = worst(r["cap"], "c_pad")
        rows.append((mode, "PAD capacitance, input mode, 1 MHz", "<= 3 pF", fmt(v, "F"), "max", cid, v <= 3e-12))
    return rows


def dv(rep, cid):
    for c in rep["corners"]:
        if c["corner_id"] == cid:
            return c["params"]["dvdd"]
    raise KeyError(cid)


def probe(path):
    """Negative-control verdict: 0 only if the single corner passed with finite values."""
    rep = load(path)
    names = [m["name"] for c in (rep.get("corners") or [])[:1] for m in c.get("measurements", [])]
    bad = check_report(rep, names or ["<none>"], 1, "probe")
    for b in bad:
        print("collect: " + b, file=sys.stderr)
    return 1 if bad else 0


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--probe":
        sys.exit(probe(sys.argv[2]))
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    out, kltout, spec, meta = sys.argv[1:]
    problems, reps = [], {}
    for d in DECKS:
        for m in MODES:
            rep = merged(kltout, d, m)
            problems += check_report(rep, EXPECT[d], CORNERS, f"{d}_{m}")
            reps[(d, m)] = rep
    if problems:
        for p in problems[:40]:
            print("collect: FAIL: " + p, file=sys.stderr)
        print(f"collect: FAIL: {len(problems)} problem(s)", file=sys.stderr)
        sys.exit(1)

    with open(os.path.join(out, "results.tsv"), "w") as f:
        f.write("deck\tmode\tcorner_id\tmeasurement\tvalue\tunit\n")
        for (d, m), rep in reps.items():
            for c in rep["corners"]:
                for ms in c["measurements"]:
                    f.write(f"{d}\t{m}\t{c['corner_id']}\t{ms['name']}\t{ms['value']!r}\t{ms.get('unit', '')}\n")
    n_points = sum(len(r["corners"]) for r in reps.values())

    rows = table(reps)
    envs = []
    for (d, m), rep in sorted(reps.items()):
        for stem, job, host in rep["_parts"]:
            envs.append(f"- `{stem}`: job `{job}`, engine `{rep['environment'].get('engine_version')}`, "
                        f"host `{host}`")
    md = ["# gf180mcu_fd_io__bi_t versus the ratified GPIO electrical targets", "",
          "Reference values for the foundry cell, not results for this block. No ESD claim.", ""]
    md += [open(meta).read().strip(), ""]
    md += ["## Supply convention", "",
           "Foundry convention: `VDD` = `DVDD` (every logic device in `bi_t` is thick-oxide, so this is "
           "electrically consistent). This departs from the ratified spec, which holds core `VDD` at "
           "3.3 V while `DVDD` is 5 V; the level-shifter crossing is NOT exercised by this record.", "",
           "## Known limitation (quoted from spec/io-ring.md, section PVT corners)", "",
           "> " + limitation(spec).replace("\n", "\n> "), "",
           "## Grid", "",
           f"{len(reps) * 3} requests, {n_points} PVT points: process (typical, ff, ss, fs, sf) x "
           "-40/25/125 C x DVDD (4.5/5/5.5 V in 5 V mode; 2.97/3.3/3.63 V in 3.3 V mode). "
           "Pins: PDRV0=PDRV1=0, SL=0, PU=PD=0 unless the row says otherwise. "
           "Diode, resistor and MOS-capacitor sections follow typical/ff/ss; fs and sf use typical passives.", "",
           "## Comparison", "",
           "| Mode | Parameter | Target | Foundry (binding corner) | Binding | Corner | Meets target |",
           "|---|---|---|---|---|---|---|"]
    for mode, par, tgt, val, bind, cid, ok in rows:
        md.append(f"| {mode} | {par} | {tgt} | {val} | {bind} | `{cid}` | {'yes' if ok else 'NO'} |")
    md += ["", "Input thresholds: VIL/VIH are read from a slow PAD ramp up then down (Vt+ at the rising "
           "crossing of Y = DVDD/2, Vt- at the falling one). The rows use the receiver convention "
           "(reads low up to 0.3*DVDD means Vt- >= 0.3*DVDD; reads high from 0.7*DVDD means "
           "Vt+ <= 0.7*DVDD). The spec text does not state the convention; the raw Vt+/Vt- are in "
           "results.tsv. Hysteresis is compared in the Schmitt setting (CS=1); CS=0 is listed as measured.",
           "", "## Jobs", ""] + envs
    open(os.path.join(out, "record.md"), "w").write("\n".join(md) + "\n")
    print(f"collect: {len(reps) * 3} requests, {n_points} points, all finite; {sum(1 for r in rows if not r[-1])}"
          f" of {len(rows)} comparison rows miss their target (reference data, not a failure)")


if __name__ == "__main__":
    main()
