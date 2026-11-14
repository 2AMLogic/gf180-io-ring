#!/usr/bin/env python3
"""Write the `klt sim` corner requests (and their netlists) for the GPIO cell's spec rows.

    python3 -I gen_requests.py <outdir> <modeldir> <design-dir> [--probe]

The device under test is `design/gpio.spice` (subckt `gpio`), the cell drawn in issue #14.
One request per (deck, supply mode): 5 process x 3 T = 15 corners each. The supply axes
(`DVDD` nominal -10 % / nominal / +10 %, crossed with core `VDD` 2.97 / 3.3 / 3.63 V, as
DR-0002 requires for anything through the level shifter) are NOT a `corners.params` axis:
the nine (DVDD, VDD) pairs are nine independent DUT instances in one netlist, each with its
own supplies and bias sources, and a measurement per instance (`<name>_d<i>v<j>`; i, j = 0, 1,
2 for low / nominal / high). That makes every request valid for any `klt sim` client, whereas
`corners.params` is dropped silently by some of them and refused by the fleet runner.

The spec limit of each row is the measurement's own `limits`, so the request's rollup
status is the pass/fail of the row over the whole grid. Rows that the spec states at the
nominal point only (pull resistance) are separate single-corner `*_nominal` requests.

Nothing here runs ngspice. With `KLT_SIM_BACKEND=batch` a multi-corner request goes to the
Spot fleet.

--probe writes ONE single-corner request per deck (typical, 25 C, all nine supply pairs) for
the local debug probe in run.sh --probe; a single corner is the one thing a dispatch host
may run locally.
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from gpio_common import process_axis  # noqa: E402

# mode -> DVDD (low, nominal, high), load current at the spec VOL/VOH point, VOH drop limit,
# rise/fall limit, hysteresis limit
MODES = {
    "5v": dict(dvdd=[4.5, 5.0, 5.5], iload=4e-3, voh_drop=0.5, edge=5e-9, hyst=0.4),
    "3v3": dict(dvdd=[2.97, 3.3, 3.63], iload=2e-3, voh_drop=0.4, edge=8e-9, hyst=0.25),
}
VDDS = [2.97, 3.3, 3.63]
TEMPS = [-40, 25, 125]
PINS = ("a", "oe", "ie", "pu", "pd")
# ESD stress assumptions (design/README.md, "Pad clamp diode sizing"): HBM 2 kV / 1.5 kohm,
# and a forward-drop budget of half the 6.0 V device class. Not spec rows.
I_HBM = 1.33
VF_BUDGET = 3.0
V_RAIL_BUDGET = 6.0
# Core VDD-VSS clamp budget (DR-0004, Proposed): the DVDD headroom ratio (6.0 V budget over 5.0 V
# nominal) applied to the 3.3 V nominal, rounded. An assumption, not a spec row.
V_CORE_BUDGET = 4.0


def lim(lo=None, hi=None):
    out = {}
    if lo is not None:
        out["min"] = lo
    if hi is not None:
        out["max"] = hi
    return out


def mexpr(name, expr, unit, limits=None):
    m = {"name": name, "expr": expr, "unit": unit}
    if limits:
        m["limits"] = limits
    return m


def mspice(name, card, unit, limits=None):
    m = {"name": name, "spice": card, "unit": unit}
    if limits:
        m["limits"] = limits
    return m


# Each deck builder returns (pins, extra lines, measurements) for one DUT instance with
# suffix k, supplies dvdd/vdd (literals) and the mode's constants.
def d_vol(k, dvdd, vdd, M):
    return ({"oe": vdd}, [f"Iload{k} dvdd{k} pad{k} DC {M['iload']}"],
            [mexpr(f"vol{k}", f"v(pad{k})", "V", lim(hi=0.4))])


def d_voh(k, dvdd, vdd, M):
    return ({"a": vdd, "oe": vdd}, [f"Iload{k} pad{k} 0 DC {M['iload']}"],
            [mexpr(f"voh{k}", f"v(pad{k})", "V"),
             mexpr(f"voh_drop{k}", f"v(dvdd{k})-v(pad{k})", "V", lim(hi=M["voh_drop"]))])


def d_edges(k, dvdd, vdd, M):
    lo, hi = round(0.1 * dvdd, 6), round(0.9 * dvdd, 6)
    return ({"a": f"PULSE(0 {vdd} 2n 0.1n 0.1n 40n 80n)", "oe": vdd}, [f"Cl{k} pad{k} 0 15p"],
            [mspice(f"t_rise{k}", f".meas tran t_rise{k} TRIG v(pad{k}) VAL={lo} RISE=1 "
                    f"TARG v(pad{k}) VAL={hi} RISE=1", "s", lim(hi=M["edge"])),
             mspice(f"t_fall{k}", f".meas tran t_fall{k} TRIG v(pad{k}) VAL={hi} FALL=1 "
                    f"TARG v(pad{k}) VAL={lo} FALL=1", "s", lim(hi=M["edge"]))])


def d_xfer(k, dvdd, vdd, M):
    mid = round(0.5 * vdd, 6)
    return ({"ie": vdd}, [f"Vpad{k} pad{k} 0 PWL(0 0 100u {dvdd} 200u 0)"],
            [mspice(f"vt_plus{k}", f".meas tran vt_plus{k} FIND v(pad{k}) WHEN v(y{k})={mid} RISE=1",
                    "V", lim(hi=round(0.7 * dvdd, 6))),
             mspice(f"vt_minus{k}", f".meas tran vt_minus{k} FIND v(pad{k}) WHEN v(y{k})={mid} FALL=1",
                    "V", lim(lo=round(0.3 * dvdd, 6))),
             mspice(f"hyst{k}", f".meas tran hyst{k} PARAM='vt_plus{k}-vt_minus{k}'", "V",
                    lim(lo=M["hyst"]))])


def d_pullup(k, dvdd, vdd, M):
    return ({"pu": vdd}, [f"Vpad{k} pad{k} 0 DC {round(dvdd / 2, 6)}"],
            [mexpr(f"r_pullup{k}", f"0.5*v(dvdd{k})/abs(i(vpad{k}))", "ohm")])


def d_pulldown(k, dvdd, vdd, M):
    return ({"pd": vdd}, [f"Vpad{k} pad{k} 0 DC {round(dvdd / 2, 6)}"],
            [mexpr(f"r_pulldown{k}", f"0.5*v(dvdd{k})/abs(i(vpad{k}))", "ohm")])


def d_cap(k, dvdd, vdd, M):
    return ({"ie": vdd}, [f"Vpad{k} pad{k} 0 DC {round(dvdd / 2, 6)} AC 1"],
            [mexpr(f"c_pad{k}", f"-imag(i(vpad{k}))/(2*3.14159265358979*1e6)", "F", lim(hi=3e-12))])


DECKS = {
    "vol": (d_vol, "VOL: A=0, OE=1; sink current from DVDD into PAD",
            {"kind": "op", "args": ""}),
    "voh": (d_voh, "VOH: A=1, OE=1; source current from PAD to ground",
            {"kind": "op", "args": ""}),
    "edges": (d_edges, "10-90 % rise/fall into 15 pF, OE=1, A pulsed",
              {"kind": "tran", "args": "20p 90n 0 50p"}),
    "xfer": (d_xfer, "input transfer curve: slow PAD ramp up then down, OE=0, IE=1",
             {"kind": "tran", "args": "0.2u 200u 0 0.2u"}),
    "pullup": (d_pullup, "pull-up equivalent R, PAD held at DVDD/2, OE=IE=0, PU=1",
               {"kind": "op", "args": ""}),
    "pulldown": (d_pulldown, "pull-down equivalent R, PAD held at DVDD/2, OE=IE=0, PD=1",
                 {"kind": "op", "args": ""}),
    "cap": (d_cap, "PAD small-signal capacitance at 1 MHz, input mode, PAD at DVDD/2",
            {"kind": "ac", "args": "lin 1 1meg 1meg"}),
}


def instance(k, dvdd, vdd, pins, extra, sub="gpio"):
    lines = [f"Vdvdd{k} dvdd{k} 0 {dvdd}", f"Vvdd{k} vdd{k} 0 {vdd}"]
    for p in PINS:
        lines.append(f"V{p}{k} {p}{k} 0 {pins.get(p, 0)}")
    lines += extra
    lines.append(f"Xdut{k} a{k} oe{k} ie{k} pu{k} pd{k} y{k} pad{k} dvdd{k} vdd{k} 0 0 {sub}")
    return lines


def header(deck, mode, doc, modeldir, extra_includes=("gpio.spice",)):
    return [f"* GPIO cell (design/gpio.spice), deck {deck}, {mode} mode: {doc}",
            "* Generated by gen_requests.py. Nine independent instances, one per (DVDD, VDD) pair.",
            f".include {modeldir}/design.ngspice"] + [f".include {i}" for i in extra_includes]


def request(netlist, modeldir, analysis, meas, corners, timeout=600):
    return {"netlist": netlist, "engine": "ngspice",
            "models": {"pdk": "gf180mcuD", "lib": f"{modeldir}/sm141064.ngspice"},
            "corners": corners, "analysis": analysis, "measurements": meas,
            "options": {"stage_model_inputs": True, "timeout_s": timeout}}


def grid_corners():
    return {"process": process_axis(), "temperature_c": TEMPS}


def nominal_corners():
    return {"process": [process_axis()[0]], "temperature_c": [25]}


def build_deck(deck, mode, modeldir, only_nominal=False):
    fn, doc, analysis = DECKS[deck]
    M = MODES[mode]
    lines = header(deck, mode, doc, modeldir)
    meas = []
    for i, dvdd in enumerate(M["dvdd"]):
        for j, vdd in enumerate(VDDS):
            if only_nominal and not (i == 1 and j == 1):
                continue
            k = f"_d{i}v{j}"
            pins, extra, ms = fn(k, dvdd, vdd, M)
            lines += instance(k, dvdd, vdd, pins, extra)
            meas += ms
    return "\n".join(lines) + "\n", analysis, meas


def esd_pad_netlist(modeldir):
    """The cell unpowered (every rail at 0 V); a current source forces the HBM-equivalent
    current (and 1 mA) into PAD (towards DVDD through the pull-up clamp diode) and out of
    PAD (from DVSS through the pull-down clamp diode)."""
    lines = header("esd_pad", "-", "pad clamp diodes in the cell, forced current", modeldir)
    meas = []
    for tag, sign, amp, limit in (("up_hbm", 1, I_HBM, VF_BUDGET), ("dn_hbm", -1, I_HBM, VF_BUDGET),
                                  ("up_1ma", 1, 1e-3, None), ("dn_1ma", -1, 1e-3, None)):
        k = f"_{tag}"
        src = f"Iforce{k} 0 pad{k} DC {amp}" if sign > 0 else f"Iforce{k} pad{k} 0 DC {amp}"
        lines += instance(k, 0, 0, {}, [src])
        expr = f"v(pad{k})" if sign > 0 else f"-v(pad{k})"
        meas.append(mexpr(f"vf_{tag}", expr, "V", lim(hi=limit) if limit else None))
    return "\n".join(lines) + "\n", {"kind": "op", "args": ""}, meas


def esd_rail_netlist(modeldir):
    """DVDD pad cell (RC-triggered clamp, DR-0003) unpowered; a 10 ns-rise current pulse
    into DVDD with DVSS, VDD, VSS grounded."""
    lines = header("esd_rail", "-", "DVDD-DVSS rail clamp, ESD-like current pulse", modeldir,
                   ("dvdd_pad.spice",))
    # Convergence aid: without it some corners (fs/125 C, ss/-40 C, ff/125 C) abort with
    # "timestep too small" in the trigger moscap. The 1 Meg leak (6 uA at 6 V, against 1.33 A) is
    # what converged ss/125 C and sf/125 C with the 4800 um clamp; at 1 G they erred at 0.5 ns.
    lines += [".options itl4=1000 gmin=1e-9 reltol=0.01 abstol=1e-10 rshunt=1e12", "Rleak dvdd 0 1Meg",
              f"Ipulse 0 dvdd PULSE(0 {I_HBM} 1n 10n 10n 100n 1)",
              "Xrail dvdd 0 0 0 dvdd_pad"]
    meas = [mspice("v_peak", ".meas tran v_peak MAX v(dvdd)", "V", lim(hi=V_RAIL_BUDGET)),
            mspice("v_end", ".meas tran v_end FIND v(dvdd) AT=110n", "V")]
    return "\n".join(lines) + "\n", {"kind": "tran", "args": "0.1n 130n 0 0.2n"}, meas


def esd_core_rail_netlist(modeldir):
    """Core-supply pad cell (RC-triggered 3.3 V clamp, DR-0003) unpowered; the same 10 ns-rise
    current pulse as esd_rail into VDD with DVDD, DVSS, VSS grounded."""
    lines = header("esd_core_rail", "-", "VDD-VSS core rail clamp, ESD-like current pulse", modeldir,
                   ("core_pad.spice",))
    # Same convergence aid as esd_rail (DR-0003 Amendment 1, item 4): a 1 Meg leak at VDD. The
    # fleet's ngspice aborted fs/125 C (gmin=1e-9), then sf/125 C (gmin=1e-8), with "timestep too
    # small" in the trigger moscap; both attempts are kept under the record's superseded/.
    # gmin=1e-8 with cshunt=1e-14 (10 fF per node, against pF-scale devices) converged both.
    lines += [".options itl4=1000 gmin=1e-8 reltol=0.01 abstol=1e-9 rshunt=1e12 cshunt=1e-14", "Rleak vdd 0 1Meg",
              f"Ipulse 0 vdd PULSE(0 {I_HBM} 1n 10n 10n 100n 1)",
              "Xcore 0 vdd 0 0 core_pad"]
    meas = [mspice("v_peak", ".meas tran v_peak MAX v(vdd)", "V", lim(hi=V_CORE_BUDGET)),
            mspice("v_end", ".meas tran v_end FIND v(vdd) AT=110n", "V")]
    return "\n".join(lines) + "\n", {"kind": "tran", "args": "0.1n 130n 0 0.2n"}, meas


def write(out, stem, text, req):
    with open(os.path.join(out, stem + ".sp"), "w") as f:
        f.write(text)
    with open(os.path.join(out, stem + ".json"), "w") as f:
        json.dump(req, f, indent=2)
        f.write("\n")


def main():
    args = sys.argv[1:]
    probe = "--probe" in args
    if probe:
        args.remove("--probe")
    if len(args) != 3:
        sys.exit(__doc__)
    out, modeldir, designdir = args
    os.makedirs(out, exist_ok=True)
    for f in ("gpio.spice", "dvdd_pad.spice", "core_pad.spice"):
        shutil.copy(os.path.join(designdir, f), os.path.join(out, f))
    cor = nominal_corners() if probe else grid_corners()
    names = []
    for deck, (_, _, _) in DECKS.items():
        for mode in MODES:
            text, analysis, meas = build_deck(deck, mode, modeldir)
            stem = f"{deck}_{mode}"
            write(out, stem, text, request(stem + ".sp", modeldir, analysis, meas, cor))
            names.append(stem)
    text, analysis, meas = esd_pad_netlist(modeldir)
    write(out, "esd_pad", text, request("esd_pad.sp", modeldir, analysis, meas, cor))
    names.append("esd_pad")
    # The clamp FET of dvdd_pad.spice is 100 um x 10 fingers x m=48 (DR-0003 as amended: 4800 um): one
    # wide instance failed to bin on the fleet ("could not find a valid modelname").
    text, analysis, meas = esd_rail_netlist(modeldir)
    write(out, "esd_rail", text, request("esd_rail.sp", modeldir, analysis, meas, cor, 900))
    names.append("esd_rail")
    text, analysis, meas = esd_core_rail_netlist(modeldir)
    write(out, "esd_core_rail", text, request("esd_core_rail.sp", modeldir, analysis, meas, cor, 900))
    names.append("esd_core_rail")
    if not probe:
        for deck in ("pullup", "pulldown"):
            for mode in MODES:
                text, analysis, meas = build_deck(deck, mode, modeldir, only_nominal=True)
                for m in meas:
                    m["limits"] = lim(25e3, 100e3)
                stem = f"{deck}_{mode}_nominal"
                write(out, stem, text, request(stem + ".sp", modeldir, analysis, meas, nominal_corners()))
                names.append(stem)
    print("\n".join(names))


if __name__ == "__main__":
    main()
