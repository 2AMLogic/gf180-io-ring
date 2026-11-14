"""Values and helpers shared by the GPIO sim benches (sim/gpio-corners, sim/gpio-bi_t, sim/mc).

Imported by path (the scripts run as `python3 -I`, which drops the script directory from
sys.path). The corner bundle lives here so the foundry bi_t comparison cannot run on
different corners than the design's; the ratified spec limits below live here for the same
reason, so the Monte Carlo campaign, the corner sweep and the foundry comparison table
cannot grade against three different copies of one spec row.

Each constant names the `spec/io-ring.md` row it comes from. These are the ratified values:
change one only through a spec change and a decision record, never to make a result pass.
Benches need different *shapes* of the same numbers (the corner sweep wants the three-point
DVDD axis, the MC campaign wants the nominal point, bi_t wants the axis without the limits),
so the values are shared and each caller selects what it needs.
"""
import json
import math
import sys

PASSIVES = ["diode_{}", "res_{}", "moscap_{}"]

# --- PVT axes (spec/io-ring.md, "Supplies and devices per path" and "PVT corners") ------
# I/O supply, nominal -10 % / nominal / +10 %, per supply mode (spec:51, spec:174).
DVDD = {"5v": [4.5, 5.0, 5.5], "3v3": [2.97, 3.3, 3.63]}
# Core interface supply, crossed with DVDD for any result through the level shifter
# (spec:52, spec:175).
VDD_CORE = [2.97, 3.3, 3.63]
# Temperature axis (spec:173).
TEMPS = [-40, 25, 125]

# --- Ratified electrical limits (spec/io-ring.md, "GPIO electrical targets") ------------
# Load current at the spec VOL/VOH point: 4 mA at 5 V, 2 mA at 3.3 V (spec:76-:77).
ILOAD = {"5v": 4e-3, "3v3": 2e-3}
# VOL <= 0.4 V at that load, both modes (spec:76-:77).
VOL_MAX = 0.4
# VOH >= DVDD - this drop, at that load (spec:76-:77).
VOH_DROP_MAX = {"5v": 0.5, "3v3": 0.4}
# Rise/fall 10-90 % into 15 pF (spec:78).
EDGE_MAX = {"5v": 5e-9, "3v3": 8e-9}
# Input hysteresis (spec:80).
HYST_MIN = {"5v": 0.4, "3v3": 0.25}
# Pull-up / pull-down equivalent R at nominal, (min, max) (spec:81).
R_PULL = (25e3, 100e3)


def dvdd_nominal(mode):
    """Nominal DVDD of a supply mode: the middle point of its three-point axis."""
    return DVDD[mode][1]


def vdd_core_nominal():
    """Nominal core VDD: the middle point of the three-point core axis."""
    return VDD_CORE[1]


def process_axis():
    """gf180mcu has no all-device corner section: each corner is a bundle. The 5/6 V
    devices load their typical section in every one of them (spec 'PVT corners', DR-0002)."""
    axis = []
    for name, passive in (("typical", "typical"), ("ff", "ff"), ("ss", "ss"),
                          ("fs", "typical"), ("sf", "typical")):
        axis.append({"name": name,
                     "sections": [name] + [p.format(passive) for p in PASSIVES]})
    return axis


def vlabel(v):
    return f"{v:.2f}".replace(".", "v")


def load(path):
    try:
        return json.load(open(path))
    except Exception as e:  # noqa: BLE001
        return {"_unreadable": str(e)}


def finite(v):
    return isinstance(v, (int, float)) and math.isfinite(v)


# Display scaling for the record tables. Shared so the design record and the foundry
# comparison table cannot print the same quantity on two different scales.
UNITS = {"s": (1e9, "ns"), "F": (1e12, "pF"), "ohm": (1e-3, "kohm"), "V": (1.0, "V")}


def fmt(v, unit):
    s, u = UNITS[unit]
    return f"{v * s:.4g} {u}"


def limitation(spec):
    text = open(spec, encoding="utf-8").read()
    i = text.find("**Known limitation, measured.**")
    if i < 0:
        sys.exit("collect: spec 'Known limitation, measured' paragraph not found")
    return text[i:].split("\n\n", 1)[0].strip()
