#!/usr/bin/env python3
"""Check the klt sim reports of a gpio-corners run and write the record.

    python3 -I collect.py [--probe] <recorddir> <spec/io-ring.md> <meta.txt>

Reads <recorddir>/klt/<stem>.json (the `klt sim` envelope of each request listed in
<recorddir>/requests.list) and writes results.tsv (every point), rows.json (per spec row:
verdict, worst value, binding corner and supply pair, the envelope that carries it) and
record.md.

Exit 0 only if every request has a readable envelope with every declared corner and every
declared measurement present and finite in every corner. A spec row that MISSES its target
is data, not a failure of the run: it is reported, and the envelope itself is `fail`
(which keeps T1 item 5 unmet). Nothing here relaxes a limit.

--probe writes the record of a run.sh --probe: ONE local corner per deck instead of the PVT
grid. It changes only the record text (the grid paragraph, and a leading statement that the
record is not the PVT result and is not citable evidence); the checks are identical. A probe
record is refused by cite.py.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from gpio_common import finite, limitation, load  # noqa: E402

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
    # esd_rail_release: the powered-rail deck. Every row is report-only (no limits in the
    # request): the spec states no release criterion, and esd_rail's 6 V budget is an assumption
    # about the UNPOWERED deck, so it is not reused here. Base names are deliberately distinct
    # from v_peak/v_end so esd_rail's own row set cannot move.
    "v_gate_rel": ("esd_rail_release_gate", "rail clamp gate at the end of the window, rail "
                   "powered (released = back to 0 V)", "V"),
    "v_dvdd_rel": ("esd_rail_release_dvdd", "DVDD at the end of the window, rail powered "
                   "(recovered = back to the supply less the series-R drop)", "V"),
    "i_rail_rel": ("esd_rail_release_irail", "supply current into DVDD at the end of the window "
                   "(clamp + trigger; a latched clamp would hold this high)", "A"),
    "v_peak_pwr": ("esd_rail_release_peak", "peak DVDD under the same pulse with the rail "
                   "powered (context for the release rows; NOT esd_rail's 6 V budget row)", "V"),
    "v_gate_pk_pwr": ("esd_rail_release_gate_peak", "peak rail clamp gate with the rail powered "
                      "(how hard the RC trigger drives it from a powered start)", "V"),
}
# Report-only context measurements (no limit, listed in results.tsv and the record)
CONTEXT = {"voh", "vf_up_1ma", "vf_dn_1ma", "v_end"}
UNITS = {"s": (1e9, "ns"), "F": (1e12, "pF"), "ohm": (1e-3, "kohm"), "V": (1.0, "V"),
         "A": (1e3, "mA")}
KEY = re.compile(r"^(?P<base>.+?)(_d(?P<i>\d)v(?P<j>\d))?$")


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
    args = sys.argv[1:]
    probe = "--probe" in args
    if probe:
        args.remove("--probe")
    if len(args) != 3:
        sys.exit(__doc__)
    rec, spec, meta = args
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

    if probe:
        title = ("# gpio cell (design/gpio.spice): ONE-CORNER LOCAL PROBE, not the PVT result")
        lead = ("**This record is a single-corner local debug probe, not evidence.** It is one "
                "corner (typical process, 25 C) run locally on the submitting host, not the "
                "DR-0002 PVT set, and the host's ngspice and klt are not the fleet runner's "
                "(see the provenance block below). It does NOT establish any row, it is NOT the "
                "PVT result, and `cite.py` refuses it as T1 item 5 evidence. Results are "
                "measurements, not ratings: no cell is ESD-rated or qualified, and the ESD rows "
                "below are simulated clamp behaviour only.")
        grid = ("ONE corner: typical process, 25 C, with all nine (`DVDD`, `VDD`) instances still "
                "present in the gpio decks, so a gpio row has 9 points and a single-instance ESD "
                "deck has 1. The full bench is 5 process x -40/25/125 C = 15 corners per request "
                "(135 points per gpio row); none of that was run here. A probe cannot show "
                "process or temperature spread, which is where every ESD and timing row of this "
                "bench is binding, so read every number below as one point of an unmeasured "
                "distribution.")
    else:
        title = "# gpio cell (design/gpio.spice) versus the ratified GPIO electrical targets"
        lead = ("Pre-silicon simulation of the drawn cell across the DR-0002 PVT set. Results are "
                "measurements, not ratings: no cell is ESD-rated or qualified, and the ESD rows "
                "below are simulated clamp behaviour only.")
        grid = ("Process (typical, ff, ss, fs, sf) x -40/25/125 C = 15 corners per request; `DVDD` "
                "nominal -10 % / nominal / +10 % (4.5/5/5.5 V in 5 V mode, 2.97/3.3/3.63 V in "
                "3.3 V mode) crossed with core `VDD` 2.97/3.3/3.63 V, as nine independent DUT "
                "instances per netlist: 135 points per row (the `*_nominal` requests are one "
                "corner: typical, 25 C, nominal `DVDD`, `VDD` 3.3 V). Pins not named by a deck "
                "are 0; core-side inputs swing 0..`VDD`. Diode, resistor and MOS-capacitor "
                "sections follow typical/ff/ss; fs and sf use typical passives.")
    md = [title, "", lead, "", open(meta).read().strip(), "",
          "## Known limitation (quoted from spec/io-ring.md, section PVT corners; DR-0002)", "",
          "> " + limitation(spec).replace("\n", "\n> "), "",
          "Every row below therefore moves with supply and temperature, and with process only through "
          "the 3.3 V devices and the passives; `ff`/`ss` say nothing about 5/6 V process spread, and "
          "`fs`/`sf` are incomplete corners (`klt pdk corners`).", "",
          "## Grid", "", grid, "",
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
           "- **ESD rail clamp release, rail powered (`esd_rail_release`).** The same pad cell and the "
           "same 1.33 A / 10 ns-rise pulse as `esd_rail`, but `DVDD` is held at its nominal 5 V through "
           "a 50 ohm series resistance and the window runs to 5 us, about ten times DR-0003 decision "
           "item 1's \"order of 0.5 us\" trigger RC design intent, with the rows read at 4.5 us. This "
           "is the gap DR-0003 Amendment 1 item 3 records as **Not evaluated** (release after the pulse "
           "and absence of latching). **Every row of this request is report-only and carries no "
           "limit**: the spec states no release criterion, and `esd_rail`'s 6 V budget is an assumption "
           "about the *unpowered* deck, so reusing it here would be inventing a limit. The two decks "
           "start from different quiescent states and answer different questions - this one is not a "
           "second opinion on `esd_rail`'s peak. The series resistance and the window length are "
           "declared bench assumptions (`gen_requests.py`), not spec rows. The current row is the whole "
           "rail's current (clamp plus trigger), not the clamp FET's drain current. Simulated clamp "
           "behaviour only: nothing here is an ESD rating.",
           "- **Not covered (declared gaps).** The core `VDD`-`VSS` rail clamp (3.3 V devices; the spec "
           "gives no voltage budget for it) and the `VDD`/`DVDD` cross-domain coupling (spec: decision "
           "record to follow) are not simulated here.",
           "", "## Open questions for a decision record", "",
           "These are questions this bench raises and cannot answer. None is a limit, none is written "
           "into `spec/`, and nothing below was relaxed to make a row pass.", "",
           "- **What counts as release?** `spec/io-ring.md` gives no criterion for the rail clamp after "
           "the pulse: no gate-voltage ceiling, no recovery tolerance on `DVDD`, no quiescent-current "
           "ceiling, and no time by which any of them must hold. The `esd_rail_release_*` rows are "
           "therefore reported against no target. Turning them into pass/fail rows needs a decision "
           "record to state the three numbers and the time - that is not this bench's call.",
           "- **Is a transient on a POWERED rail in the clamp's duty at all, and under what budget?** "
           "The 6 V figure `esd_rail` carries is the `*_06v0` device class applied to the unpowered "
           "HBM-like case. Whether the same ceiling, a different one, or none applies when the rail is "
           "already up is undecided, so `esd_rail_release_peak` is reported without one. A decision "
           "record should settle it before anyone reads that row as a pass or a failure.",
           "- **Latch-up is not fully covered by this bench.** A quiescent rail current back at its "
           "pre-pulse value is evidence the clamp released, not proof that no parasitic structure "
           "latched: the pad-side latch-up and guard-ring rules remain a klt deck gap "
           "(klayout-tools#3793, DR-0003 Amendment 1 item 3), so there is no rule check to pair with "
           "this measurement.",
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
