#!/usr/bin/env python3
"""Write the `klt pex` testbench requests for the GPIO cell: the item-5 requests, made pex-shaped.

    python3 -I gen_requests.py <outdir> <modeldir> <design-dir> [--probe]

The corner grid, decks and spec limits are the ones in ../gpio-corners/gen_requests.py,
unchanged: this calls its generator and rewrites each testbench. Two differences:

* `klt pex` swaps exactly one `.include` (the DUT) for the extracted netlist, so the PDK
  switch-parameter include (`design.ngspice`, only `.param` defaults) is inlined into the
  testbench body, which both legs then share.
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


def inline_params(text, modeldir):
    """Replace `.include <modeldir>/design.ngspice` with its non-comment cards."""
    path = os.path.join(modeldir, "design.ngspice")
    cards = [l for l in open(path).read().splitlines() if l.strip() and not l.lstrip().startswith("*")]
    pat = re.compile(r"^\.include\s+" + re.escape(path) + r"\s*$", re.M)
    if not pat.search(text):
        sys.exit("gpio-pex: gen_requests: no design.ngspice include to inline")
    return pat.sub("* design.ngspice (inlined: pex swaps exactly one .include)\n" + "\n".join(cards), text)


def main():
    args = sys.argv[1:]
    if len(args) not in (3, 4):
        sys.exit(__doc__)
    out, modeldir, designdir = args[:3]
    r = subprocess.run([sys.executable, "-I", SRC] + args, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr)
    for stem in r.stdout.split():
        if stem in DROP:
            for ext in (".sp", ".json"):
                os.remove(os.path.join(out, stem + ext))
            continue
        sp = os.path.join(out, stem + ".sp")
        text = inline_params(open(sp).read(), modeldir)
        open(sp, "w").write(text)
        print(stem)


if __name__ == "__main__":
    main()
