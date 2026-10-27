#!/usr/bin/env python3
"""Check the klt sim reports of a gpio-corners run and write the record.

    python3 -I collect.py <recorddir> <spec/io-ring.md> <meta.txt>

Reads <recorddir>/klt/<stem>.json (the `klt sim` envelope of each request listed in
<recorddir>/requests.list) and writes results.tsv (every point), rows.json (per spec row:
verdict, worst value, binding corner and supply pair, the envelope that carries it) and
record.md.

Exit 0 only if every request has a readable envelope with every declared corner and every
declared measurement present and finite in every corner. A spec row that MISSES its target
is data, not a failure of the run: it is reported, and the envelope itself is `fail`
(which keeps T1 item 5 unmet). Nothing here relaxes a limit.
"""
import json
import math
import os
import re
import sys

# measurement base name -> (row id prefix, label, unit)
ROWS = {
    "vol": ("vol", "VOL at the spec load", "V"),
    "voh_drop": ("voh", "VOH drop, DVDD - VOH, at the spec load", "V"),
    "t_rise": ("rise", "rise 10-90 % into 15 pF", "s"),
    "t_fall": ("fall", "fall 90-10 % into 15 pF", "s"),
    "vt_minus": ("vil", "VIL as lower trip Vt- (reads low up to the limit)", "V"),
    "vt_plus": ("vih", "VIH as upper trip Vt+ (reads high from the limit)", "V"),
    "hyst": ("hyst", "hysteresis Vt+ - Vt-", "V"),
    "c_pad": ("cap", "PAD capacitance, input mode, 1 MHz", "F"),
    "r_pullup": ("pullup", "pull-up equivalent R, PAD at DVDD/2", "ohm"),
    "r_pulldown": ("pulldown", "pull-down equivalent R, PAD at DVDD/2", "ohm"),
    "vf_up_hbm": ("esd_pad_up", "pad clamp to DVDD, forward drop at the 1.33 A stress current", "V"),
    "vf_dn_hbm": ("esd_pad_dn", "pad clamp from DVSS, forward drop at the 1.33 A stress current", "V"),
    "v_peak": ("esd_rail", "DVDD-DVSS rail clamp, peak DVDD under a 1.33 A / 10 ns-rise pulse", "V"),
    "rel_gio": ("esd_rail_release_gate", "DVDD-DVSS rail clamp, gate back below the threshold at the end of the tail", "V"),
    "rel_dvdd": ("esd_rail_release_dvdd", "DVDD-DVSS rail clamp, DVDD back within tolerance of the 5 V supply at the end of the tail", "V"),
    "rel_i": ("esd_rail_release_supply", "DVDD-DVSS rail clamp, supply current back to leakage level at the end of the tail", "A"),
}
# Report-only context measurements (no limit, listed in results.tsv and the record)
CONTEXT = {"voh", "vf_up_1ma", "vf_dn_1ma", "v_end", "rel_gio_peak", "t_rel"}
UNITS = {"A": (1e6, "uA"), "s": (1e9, "ns"), "F": (1e12, "pF"), "ohm": (1e-3, "kohm"), "V": (1.0, "V")}
KEY = re.compile(r"^(?P<base>.+?)(_d(?P<i>\d)v(?P<j>\d))?$")


def load(path):
    try:
        return json.load(open(path))
    except Exception as e:  # noqa: BLE001
        return {"_unreadable": str(e)}


def finite(v):
    return isinstance(v, (int, float)) and math.isfinite(v)


def limitation(spec):
    text = open(spec, encoding="utf-8").read()
    i = text.find("**Known limitation, measured.**")
    if i < 0:
        sys.exit("collect: spec 'Known limitation, measured' paragraph not found")
    return text[i:].split("\n\n", 1)[0].strip()


def fmt(v, unit):
    s, u = UNITS[unit]
    return f"{v * s:.4g} {u}"


def supply(stem, base, i, j):
    """(DVDD, VDD) of instance (i, j) for the request `stem`."""
    dvdd = {"5v": [4.5, 5.0, 5.5], "3v3": [2.97, 3.3, 3.63]}
    mode = "3v3" if "3v3" in stem else "5v"
    vdd = [2.97, 3.3, 3.63]
    return dvdd[mode][i], vdd[j]


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    rec, spec, meta = sys.argv[1:]
    stems = open(os.path.join(rec, "requests.list")).read().split()
    problems, points, envs, verdict = [], [], [], {}
    for stem in stems:
        rep = load(os.path.join(rec, "klt", stem + ".json"))
        req = load(os.path.join(rec, "requests", stem + ".json"))
        if "_unreadable" in rep:
            problems.append(f"{stem}: report unreadable: {rep['_unreadable']}")
            continue
        ncorner = len(req["corners"]["process"]) * len(req["corners"]["temperature_c"])
        names = [m["name"] for m in req["measurements"]]
        limits_of = {m["name"]: m.get("limits") for m in req["measurements"]}
        corners = rep.get("corners") or []
        if len(corners) != ncorner:
            problems.append(f"{stem}: {len(corners)} corners, expected {ncorner}")
        remote = (rep.get("environment") or {}).get("remote") or {}
        envs.append((stem, rep.get("status"), remote.get("job_id"), remote.get("runner_klt_version"),
                     (rep.get("environment") or {}).get("engine_version")))
        verdict[stem] = rep.get("status")
        for c in corners:
            if c.get("status") not in ("pass", "fail"):
                codes = [d.get("code") for d in c.get("diagnostics", [])]
                problems.append(f"{stem} {c.get('corner_id')}: status {c.get('status')} {codes}")
                continue
            got = {m["name"]: m for m in c.get("measurements", [])}
            for n in names:
                m = got.get(n)
                if m is None or not finite(m.get("value")):
                    problems.append(f"{stem} {c.get('corner_id')}: {n} missing or non-finite")
                    continue
                k = KEY.match(n)
                base = k["base"]
                i = int(k["i"]) if k["i"] else None
                j = int(k["j"]) if k["j"] else None
                points.append(dict(stem=stem, corner=c["corner_id"], name=n, base=base, i=i, j=j,
                                   value=m["value"], unit=m.get("unit", ""), status=m.get("status"),
                                   limits=limits_of[n]))
    if problems:
        for p in problems[:40]:
            print("collect: FAIL: " + p, file=sys.stderr)
        print(f"collect: FAIL: {len(problems)} problem(s)", file=sys.stderr)
        sys.exit(1)

    with open(os.path.join(rec, "results.tsv"), "w") as f:
        f.write("request\tcorner_id\tmeasurement\tvalue\tunit\tklt_status\n")
        for p in points:
            f.write(f"{p['stem']}\t{p['corner']}\t{p['name']}\t{p['value']!r}\t{p['unit']}\t{p['status']}\n")

    # one row per (stem, base); worst over every corner and supply pair
    rows = {}
    for p in points:
        if p["base"] not in ROWS:
            continue
        rows.setdefault((p["stem"], p["base"]), []).append(p)
    out_rows, md_rows = {}, []
    for (stem, base), pts in sorted(rows.items()):
        rid, label, unit = ROWS[base]
        mode = "3v3" if "3v3" in stem else ("-" if stem.startswith("esd") else "5v")
        row_id = rid if mode == "-" else f"{rid}_{mode}"
        if stem.endswith("_nominal"):
            row_id += "_nominal"
        lim = pts[0]["limits"] or {}
        hi_bound, lo_bound = lim.get("max"), lim.get("min")
        # the binding point is the one with the least margin to its own limit
        def margin(p):
            l = p["limits"] or {}
            m = []
            if l.get("max") is not None:
                m.append((l["max"] - p["value"]) / abs(l["max"]))
            if l.get("min") is not None:
                m.append((p["value"] - l["min"]) / abs(l["min"]))
            return min(m) if m else 0.0
        worst = min(pts, key=margin) if (hi_bound is not None or lo_bound is not None) else max(pts, key=lambda p: p["value"])
        nfail = sum(1 for p in pts if p["status"] == "fail")
        has_limit = hi_bound is not None or lo_bound is not None
        ok = (nfail == 0) if has_limit else None
        sp = ""
        if worst["i"] is not None:
            d, v = supply(stem, base, worst["i"], worst["j"])
            sp = f"DVDD {d} V, VDD {v} V"
        tgt = " and ".join(([f">= {fmt(lo_bound, unit)}"] if lo_bound is not None else []) +
                           ([f"<= {fmt(hi_bound, unit)}"] if hi_bound is not None else [])) or "report only"
        out_rows[row_id] = dict(row=row_id, request=stem, measurement=base, target=tgt,
                                verdict=("n/a" if ok is None else "pass" if ok else "fail"),
                                worst=worst["value"], unit=unit, binding_corner=worst["corner"],
                                binding_supply=sp, points=len(pts), points_failing=nfail)
        md_rows.append((row_id, label, tgt, fmt(worst["value"], unit), f"`{worst['corner']}`", sp or "-",
                        "n/a" if ok is None else ("yes" if ok else "**NO**"), f"{nfail}/{len(pts)}", stem))
    json.dump(out_rows, open(os.path.join(rec, "rows.json"), "w"), indent=2, sort_keys=True)
    open(os.path.join(rec, "rows.json"), "a").write("\n")

    md = ["# gpio cell (design/gpio.spice) versus the ratified GPIO electrical targets", "",
          "Pre-silicon simulation of the drawn cell across the DR-0002 PVT set. Results are "
          "measurements, not ratings: no cell is ESD-rated or qualified, and the ESD rows below "
          "are simulated clamp behaviour only.", "", open(meta).read().strip(), "",
          "## Known limitation (quoted from spec/io-ring.md, section PVT corners; DR-0002)", "",
          "> " + limitation(spec).replace("\n", "\n> "), "",
          "Every row below therefore moves with supply and temperature, and with process only through "
          "the 3.3 V devices and the passives; `ff`/`ss` say nothing about 5/6 V process spread, and "
          "`fs`/`sf` are incomplete corners (`klt pdk corners`).", "",
          "## Grid", "",
          "Process (typical, ff, ss, fs, sf) x -40/25/125 C = 15 corners per request; `DVDD` nominal -10 % / "
          "nominal / +10 % (4.5/5/5.5 V in 5 V mode, 2.97/3.3/3.63 V in 3.3 V mode) crossed with core `VDD` "
          "2.97/3.3/3.63 V, as nine independent DUT instances per netlist: 135 points per row (the "
          "`*_nominal` requests are one corner: typical, 25 C, nominal `DVDD`, `VDD` 3.3 V). Pins not "
          "named by a deck are 0; core-side inputs swing 0..`VDD`. Diode, resistor and MOS-capacitor "
          "sections follow typical/ff/ss; fs and sf use typical passives.", "",
          "## Per-row verdict", "",
          "A row passes only if every point of the grid is within its target. The binding point is the "
          "one with the least margin (or the extreme value for report-only rows).", "",
          "| Row | Parameter | Target | Worst | Binding corner | Binding supply | Meets target | Failing points | Request |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in md_rows:
        md.append("| " + " | ".join(r) + " |")
    md += ["", "## Reading the rows", "",
           "- **Input thresholds.** VIL/VIH use the receiver convention: Vt- >= 0.3*`DVDD` and "
           "Vt+ <= 0.7*`DVDD`, read from a slow PAD ramp up then down at the point where `Y` crosses "
           "`VDD`/2. The spec text does not state a convention; the raw Vt+/Vt- are in results.tsv.",
           "- **Pull resistance** is a nominal-point row: the `*_nominal` requests (typical, 25 C, nominal "
           "`DVDD`) carry the 25-100 kohm limit; the full-grid `pullup_*`/`pulldown_*` requests are "
           "report-only context.",
           "- **ESD pad clamps.** The cell is unpowered (every rail at 0 V) and a current source forces "
           "1.33 A (2 kV / 1.5 kohm, the HBM arithmetic of design/README.md) into PAD towards `DVDD` "
           "(`diode_pd2nw_06v0`) and out of PAD from `DVSS` (`diode_nd2ps_06v0`). The spec states no "
           "forward-drop number; the 3.0 V budget is the assumption recorded in design/README.md "
           "(half the 6.0 V device class) and is not a spec row. Turn-on voltage at 1 mA is reported "
           "(`vf_*_1ma`, results.tsv), without a limit.",
           "- **ESD rail clamp (simulated transient).** The `DVDD` pad cell (RC-triggered `nfet_06v0`, "
           "DR-0003 as amended; 48 x 100 um via `m=48`, trigger-inverter `pfet` 10 x 10 um via `m=10`, since one wider instance does not bin on the fleet) is unpowered; a "
           "1.33 A / 10 ns-rise pulse is forced into `DVDD`. The 6 V peak limit is the `*_06v0` device class, "
           "an assumption and not a spec row. Simulated clamp behaviour only: nothing here is an ESD rating.",
           "- **Not covered (declared gaps).** The core `VDD`-`VSS` rail clamp (3.3 V devices; the spec "
           "gives no voltage budget for it) and the `VDD`/`DVDD` cross-domain coupling (spec: decision "
           "record to follow) are not simulated here.",
           "", "## Requests", "",
           "| Request | Status | Job | Runner klt | ngspice |", "|---|---|---|---|---|"]
    for stem, st, job, rk, eng in envs:
        md.append(f"| `{stem}` | {st} | `{job}` | `{rk}` | `{eng}` |")
    open(os.path.join(rec, "record.md"), "w").write("\n".join(md) + "\n")
    missed = [r for r in out_rows.values() if r["verdict"] == "fail"]
    print(f"collect: {len(stems)} requests, {len(points)} points, all finite; {len(missed)} of "
          f"{len(out_rows)} rows miss their target: " + ", ".join(r["row"] for r in missed))


if __name__ == "__main__":
    main()
