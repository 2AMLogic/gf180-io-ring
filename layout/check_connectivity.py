# Connectivity spot check for the ring GDS (issue #32); not LVS (#17).
#
#   klayout -b -r layout/check_connectivity.py     # from the repo root
#
# Per cell: extracts the conductors (Poly/Comp-minus-Poly, Contact, Metal1-5 and
# the vias between them) with KLayout's LayoutToNetlist and names the nets from
# the net labels on Metal2-5. Fails on a short (one conductor carrying two
# names), an open (one name on two conductors) and on a net of design/<cell>.spice
# that no label reaches. Every device terminal, tap ring and rail stub of the
# generator carries a label, so a terminal left unwired shows up as an open.
import os
import re
import sys

import pya

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.abspath("layout")
ROOT = os.path.dirname(HERE)
CELLS = ("gpio", "dvdd_pad", "dvss_pad", "core_pad", "corner")
LAYERS = {"COMP": (22, 0), "POLY": (30, 0), "CONT": (33, 0), "M1": (34, 0), "V1": (35, 0),
          "M2": (36, 0), "V2": (38, 0), "M3": (42, 0), "V3": (40, 0), "M4": (46, 0),
          "V4": (41, 0), "M5": (81, 0)}
LABELS = {"M2": (36, 10), "M3": (42, 10), "M4": (46, 10), "M5": (81, 10)}
VIAS = (("M1", "V1"), ("V1", "M2"), ("M2", "V2"), ("V2", "M3"), ("M3", "V3"),
        ("V3", "M4"), ("M4", "V4"), ("V4", "M5"), ("M1", "CONT"))


def netlist_nets(cell):
    """Net names of design/<cell>.spice (device terminals, diodes and ports)."""
    nets = set()
    for ln in open(os.path.join(ROOT, "design", cell + ".spice")).read().replace("\n+", " ").splitlines():
        tok = ln.split()
        if ln.startswith(".subckt"):
            nets.update(tok[2:])
        elif ln.startswith("X"):
            nets.update(tok[1:5] if re.search(r"\b[np]fet_", ln) else tok[1:3])
        elif ln.startswith("D_"):
            nets.update(tok[1:3])
    return nets


lay = pya.Layout()
lay.read(os.path.join(HERE, "gf180_io_ring.gds"))
bad = 0
for name in CELLS:
    l2n = pya.LayoutToNetlist(pya.RecursiveShapeIterator(lay, lay.cell(name), []))
    R = {k: l2n.make_layer(lay.layer(*v), k) for k, v in LAYERS.items()}
    T = {k: l2n.make_text_layer(lay.layer(*v), "t" + k) for k, v in LABELS.items()}
    diff = R["COMP"] - R["POLY"]
    for a, b in VIAS:
        l2n.connect(R[a], R[b])
    l2n.connect(R["CONT"], diff)
    l2n.connect(R["CONT"], R["POLY"])
    for k in ("M1", "M2", "M3", "M4", "M5", "POLY"):
        l2n.connect(R[k])
    l2n.connect(diff)
    for k in T:
        l2n.connect(R[k], T[k])
    l2n.extract_netlist()
    names = {}
    for net in l2n.netlist().circuit_by_name(name).each_net():
        names.setdefault(net.name or "", []).append(net)
    shorts = sorted(n for n in names if "," in n)
    opens = sorted(n for n, v in names.items() if n and "," not in n and len(v) > 1)
    seen = {n for n in names if n and "," not in n}
    missing = sorted(netlist_nets(name) - seen)
    extra = sorted(seen - netlist_nets(name))
    ok = not (shorts or opens or missing or extra)
    print("%-9s %2d nets  %s" % (name, len(seen), "ok" if ok else
          "FAIL shorts=%s opens=%s unreached=%s unknown=%s" % (shorts, opens, missing, extra)))
    bad += not ok
sys.exit(1 if bad else 0)
