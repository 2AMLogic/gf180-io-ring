"""Helpers shared by the two GPIO sim benches (sim/gpio-bi_t, sim/gpio-corners).

Imported by path (the scripts run as `python3 -I`, which drops the script directory from
sys.path). The corner bundle lives here so the foundry bi_t comparison cannot run on
different corners than the design's.
"""
import json
import math
import sys

PASSIVES = ["diode_{}", "res_{}", "moscap_{}"]


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


def limitation(spec):
    text = open(spec, encoding="utf-8").read()
    i = text.find("**Known limitation, measured.**")
    if i < 0:
        sys.exit("collect: spec 'Known limitation, measured' paragraph not found")
    return text[i:].split("\n\n", 1)[0].strip()
