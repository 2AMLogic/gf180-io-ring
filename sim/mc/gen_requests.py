#!/usr/bin/env python3
"""Write the Monte Carlo `klt sim` requests (and their netlists) for the own-design GPIO.

    python3 -I gen_requests.py <outdir> <modeldir> <gpio.spice> [--negative rx|pull] [--probe | --no-stat]

One request per (deck, supply mode, temperature): a single corner (typical process) with
`monte_carlo` n samples, so each request is a multi-unit job that `klt sim` sends to the
batch fleet (KLT_SIM_BACKEND=batch). Nothing here runs ngspice. The spec limits ride in the
request (`measurements[].limits`), so `klt yield <report>` needs no separate limits file.

Reduced campaign, stated in README.md: typical process only (DR-0002 section 3: the 5/6 V
sections carry no skew, so ff/ss/fs/sf would only repeat typical for the devices under test),
-40/25/125 C, nominal DVDD (5.0 V and 3.3 V), core VDD = 3.3 V. The pull rows are
nominal-only in the spec, so they run at 25 C only.

Variation: `vary: both` re-seeds every sample; `.param sw_stat_global=1 sw_stat_mismatch=1`
in the netlist (after the model includes, so it wins over design.ngspice's 0 defaults)
turns on the library's own global and per-instance statistics. No skew or sigma is invented
here. (`monte_carlo.mismatch_scale` is not used: the fleet runner predates it, see README.)

--negative KIND writes the seeded known-bad variant of the nominal campaign (same seed,
same requests, deliberately mis-sized cell) for `klt yield-samples --negative-control`:
  rx    the Schmitt feedback devices st3 are shrunk, collapsing the hysteresis
  pull  the pull-up/pull-down channel lengths are cut to 1/4, so the equivalent R drops
--no-stat writes ONE request (pull-up, 5 V, 25 C, 10 samples) with sw_stat_global and
sw_stat_mismatch left at the library default 0: every sample is identical, and collect.py
must refuse it (zero variance is not a pass).
--probe writes ONE single-corner, non-MC request (typical, 25 C, 5 V) per deck for the
local sanity check in run.sh --dry-run.
"""
import json
import os
import re
import shutil
import sys

MC_N = 300
MC_SEED = 20261027
MODES = {  # name: (DVDD, load current at the spec VOL/VOH point, hysteresis limit, VOH drop limit)
    "5v": (5.0, 4e-3, 0.4, 0.5),
    "3v3": (3.3, 2e-3, 0.25, 0.4),
}
VDD_CORE = 3.3
TEMPS = [-40, 25, 125]
TARGET_YIELD = 0.98

# gf180mcu has no all-device corner section: a bundle loads the MOS section plus the diode
# (pad clamps), resistor and MOS-capacitor sections, all typical.
PROCESS = {"name": "typical",
           "sections": ["typical", "diode_typical", "res_typical", "moscap_typical"]}

BASE = {"a": "0", "oe": "0", "ie": "0", "pu": "0", "pd": "0"}


def lim(**kw):
    return dict(kw, target_yield=TARGET_YIELD)


def decks(mode):
    dvdd, iload, hyst, vohd = MODES[mode]
    return {
        "xfer": dict(
            doc="input transfer curve, slow PAD ramp up then down (receiver thresholds)",
            temps=TEMPS, pins={"ie": "{vdd}"},
            extra="Vpad pad 0 PWL(0 0 100u {dvdd} 200u 0)",
            analysis={"kind": "tran", "args": "0.1u 200u 0 0.1u"},
            meas=[{"name": "vt_plus", "unit": "V", "limits": lim(max=0.7 * dvdd),
                   "spice": ".meas tran vt_plus FIND v(pad) WHEN v(y)='0.5*vdd' RISE=1"},
                  {"name": "vt_minus", "unit": "V", "limits": lim(min=0.3 * dvdd),
                   "spice": ".meas tran vt_minus FIND v(pad) WHEN v(y)='0.5*vdd' FALL=1"},
                  {"name": "hyst", "unit": "V", "limits": lim(min=hyst),
                   "spice": ".meas tran hyst PARAM='vt_plus-vt_minus'"}]),
        "vol": dict(
            doc="VOL: A=0, OE=1; sink current from DVDD into PAD",
            temps=TEMPS, pins={"oe": "{vdd}"}, extra="Iload dvdd pad DC {iload}",
            analysis={"kind": "op", "args": ""},
            meas=[{"name": "vol", "expr": "v(pad)", "unit": "V", "limits": lim(max=0.4)}]),
        "voh": dict(
            doc="VOH: A=1, OE=1; source current from PAD to ground",
            temps=TEMPS, pins={"a": "{vdd}", "oe": "{vdd}"}, extra="Iload pad 0 DC {iload}",
            analysis={"kind": "op", "args": ""},
            meas=[{"name": "voh_drop", "expr": "v(dvdd)-v(pad)", "unit": "V",
                   "limits": lim(max=vohd)}]),
        "pullup": dict(
            doc="pull-up equivalent resistance, PAD held at DVDD/2, OE=IE=0, PU=1",
            temps=[25], pins={"pu": "{vdd}"}, extra="Vpad pad 0 DC {0.5*dvdd}",
            analysis={"kind": "op", "args": ""},
            meas=[{"name": "r_pullup", "expr": "0.5*v(dvdd)/abs(i(vpad))", "unit": "ohm",
                   "limits": lim(min=25e3, max=100e3)}]),
        "pulldown": dict(
            doc="pull-down equivalent resistance, PAD held at DVDD/2, OE=IE=0, PD=1",
            temps=[25], pins={"pd": "{vdd}"}, extra="Vpad pad 0 DC {0.5*dvdd}",
            analysis={"kind": "op", "args": ""},
            meas=[{"name": "r_pulldown", "expr": "0.5*v(dvdd)/abs(i(vpad))", "unit": "ohm",
                   "limits": lim(min=25e3, max=100e3)}]),
    }


def netlist(deck, mode, d, modeldir, stem, stat=1):
    dvdd, iload = MODES[mode][:2]
    pins = dict(BASE, **d["pins"])
    lines = [f"* own-design gpio, deck {deck}, {mode} mode: {d['doc']}",
             "* Generated by sim/mc/gen_requests.py. Core VDD = 3.3 V.",
             f".include {modeldir}/design.ngspice",
             ".include gpio.spice",
             # the fleet runner (klt 0.7.0) does not pin OMP_NUM_THREADS: with several units
             # per instance ngspice 42's OpenMP threads oversubscribe the cores and a transient
             # takes minutes instead of 0.4 s. One thread per unit is the fix.
             ".control", "set num_threads=1", ".endc",
             f".param sw_stat_global={stat} sw_stat_mismatch={stat}",
             f".param dvdd={dvdd} vdd={VDD_CORE} iload={iload}",
             "Vdvdd dvdd 0 {dvdd}", "Vvdd vdd 0 {vdd}", "Vvss vss 0 0", "Vdvss dvss 0 0"]
    for p in ("a", "oe", "ie", "pu", "pd"):
        lines.append(f"V{p} {p} 0 {pins[p]}")
    lines.append(d["extra"])
    lines.append("Xdut a oe ie pu pd y pad dvdd vdd dvss vss gpio")
    return "\n".join(lines) + "\n"


def mis_size(text, kind):
    """The deliberate defect for the negative control."""
    if kind == "rx":
        for name in ("XMN_st3", "XMP_st3"):
            text, n = re.subn(rf"(?m)^({name} .*?\bW=)[0-9.]+u", r"\g<1>0.3u", text)
            assert n == 1, name
    else:
        for name in ("XMP_pu", "XMN_pd"):
            # length / 4, floored at 0.7 um so the thick-oxide bin still resolves (an out-of-bin L fails the whole job)
            text, n = re.subn(rf"(?m)^({name} .*?\bL=)([0-9.]+)u",
                              lambda m: f"{m.group(1)}{max(float(m.group(2)) / 4, 0.7):g}u", text)
            assert n == 1, name
    return text


def main():
    args = sys.argv[1:]
    neg = None
    probe = "--probe" in args
    nostat = "--no-stat" in args
    for flag in ("--probe", "--no-stat"):
        if flag in args:
            args.remove(flag)
    if "--negative" in args:
        i = args.index("--negative")
        neg = args[i + 1] if i + 1 < len(args) else None
        if neg not in ("rx", "pull"):
            sys.exit(__doc__)
        del args[i:i + 2]
    if len(args) != 3:
        sys.exit(__doc__)
    out, modeldir, gpio = args
    os.makedirs(out, exist_ok=True)
    text = open(gpio).read()
    if neg:
        text = mis_size(text, neg)
    open(os.path.join(out, "gpio.spice"), "w").write(text)
    names = []
    for mode in MODES:
        for deck, d in decks(mode).items():
            if neg == "rx" and deck != "xfer" or neg == "pull" and not deck.startswith("pull"):
                continue
            if nostat and (deck != "pullup" or mode != "5v"):
                continue
            for t in ([25] if probe else d["temps"]):
                if probe and mode != "5v":
                    continue
                stem = f"{deck}_{mode}_{'m' if t < 0 else ''}{abs(t)}C"
                with open(os.path.join(out, stem + ".sp"), "w") as f:
                    f.write(netlist(deck, mode, d, modeldir, stem, 0 if nostat else 1))
                req = {
                    "netlist": stem + ".sp", "engine": "ngspice",
                    "models": {"pdk": "gf180mcuD", "lib": f"{modeldir}/sm141064.ngspice"},
                    "corners": {"process": [PROCESS], "temperature_c": [t]},
                    "analysis": d["analysis"], "measurements": d["meas"],
                    "options": {"stage_model_inputs": True, "timeout_s": 600},
                }
                if not probe:
                    req["monte_carlo"] = {"n": 10 if nostat else MC_N, "seed": MC_SEED,
                                          "vary": "both"}
                with open(os.path.join(out, stem + ".json"), "w") as f:
                    json.dump(req, f, indent=2)
                    f.write("\n")
                names.append(stem)
    print("\n".join(names))


if __name__ == "__main__":
    main()
