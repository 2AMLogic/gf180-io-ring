#!/usr/bin/env python3
"""Write the `klt pex` testbench requests for the GPIO cell: the item-5 requests, made pex-shaped.

    python3 -I gen_requests.py <outdir> <modeldir> <design-dir> [--probe]

The corner grid, decks and spec limits are the ones in ../gpio-corners/gen_requests.py,
unchanged: this calls its generator and rewrites each testbench. Two differences:

* `klt pex` swaps exactly one `.include` (the DUT) for the extracted netlist, so the PDK
  switch-parameter include (`design.ngspice`, only `.param` defaults) is inlined into the
  testbench body, which both legs then share.
* The positional `Xdut` line is rewritten to the extracted pin order, and the copied
  `gpio.spice` is replaced (in <outdir> only) by a wrapper `gpio` in that order around the
  unchanged design cell, renamed `gpio_design`. `design/` and the corners generator are untouched.
* `esd_rail` is dropped: its DUT is `dvdd_pad`, not the `gpio` cell the pex run extracts.

--probe writes the single-corner requests (typical, 25 C) for a local debug run.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "gpio-corners", "gen_requests.py")
DROP = ("esd_rail",)

# Pin order of the extracted `.SUBCKT gpio`, as `klt pex --tie-declared-pins` (klt 0.9.0) emits it:
# records/20261105T0900Z-probe/extracted-gpio.spice:21. klt reuses the testbench's positional
# `Xdut` line on both legs, so the line and the schematic-leg subckt are put in this order.
EXTRACTED_PINS = "A DVDD DVSS IE OE PAD PD PU VDD Y VSS".split()
# Design order (design/gpio.spice:2) -> the node the corner generator wires to each pin.
DESIGN_PINS = "A OE IE PU PD Y PAD DVDD VDD DVSS VSS".split()


def inline_params(text, modeldir):
    """Replace `.include <modeldir>/design.ngspice` with its non-comment cards."""
    path = os.path.join(modeldir, "design.ngspice")
    cards = [l for l in open(path).read().splitlines() if l.strip() and not l.lstrip().startswith("*")]
    pat = re.compile(r"^\.include\s+" + re.escape(path) + r"\s*$", re.M)
    if not pat.search(text):
        sys.exit("gpio-pex: gen_requests: no design.ngspice include to inline")
    return pat.sub("* design.ngspice (inlined: pex swaps exactly one .include)\n" + "\n".join(cards), text)


def reorder_xdut(text):
    """Rewrite each `Xdut<k> <11 design-order nodes> gpio` line to the extracted pin order."""
    def sub(m):
        nodes = m.group(2).split()
        if len(nodes) != len(DESIGN_PINS):
            sys.exit("gpio-pex: gen_requests: Xdut%s has %d nodes, expected %d" % (m.group(1), len(nodes), len(DESIGN_PINS)))
        by = dict(zip(DESIGN_PINS, nodes))
        return "Xdut%s %s %s" % (m.group(1), " ".join(by[p] for p in EXTRACTED_PINS), m.group(3))
    text, n = re.subn(r"^Xdut(\S*)\s+(.+?)\s+(gpio)\s*$", sub, text, flags=re.M)
    if not n:
        sys.exit("gpio-pex: gen_requests: no Xdut line to reorder")
    return text


def write_wrapper(out, designdir):
    """Write <out>/gpio.spice: the design cell as `gpio_design`, wrapped as `gpio` in extracted order."""
    text = open(os.path.join(designdir, "gpio.spice")).read()
    text, n = re.subn(r"^\.subckt\s+gpio\s+(.*)$", r".subckt gpio_design \1", text, count=1, flags=re.M | re.I)
    if not n or " ".join(DESIGN_PINS) not in text:
        sys.exit("gpio-pex: gen_requests: design/gpio.spice pin list is not the expected design order")
    wrapper = (".subckt gpio " + " ".join(EXTRACTED_PINS) + "\n"
               "Xcore " + " ".join(DESIGN_PINS) + " gpio_design\n.ends\n")
    open(os.path.join(out, "gpio.spice"), "w").write(text.rstrip("\n") + "\n\n* pex schematic-leg wrapper: extracted pin order\n" + wrapper)


def main():
    args = sys.argv[1:]
    if len(args) not in (3, 4):
        sys.exit(__doc__)
    out, modeldir, designdir = args[:3]
    r = subprocess.run([sys.executable, "-I", SRC] + args, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr)
    write_wrapper(out, designdir)
    for stem in r.stdout.split():
        if stem in DROP:
            for ext in (".sp", ".json"):
                os.remove(os.path.join(out, stem + ext))
            continue
        sp = os.path.join(out, stem + ".sp")
        text = reorder_xdut(inline_params(open(sp).read(), modeldir))
        open(sp, "w").write(text)
        print(stem)


if __name__ == "__main__":
    main()
