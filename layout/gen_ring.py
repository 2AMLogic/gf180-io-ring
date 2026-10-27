# gf180-io-ring layout generator (issue #15).
#
#   klayout -b -r layout/gen_ring.py            # from the repo root
#
# Writes layout/gf180_io_ring.gds. Pure KLayout-Python, no network, no
# timestamps in the stream, so two runs are byte-identical.
#
# What is drawn: the six cells of design/*.spice (gpio, dvdd_pad, dvss_pad,
# core_pad, corner, filler) plus 1/5 um filler variants, and io_ring, the closed
# ring around an empty core. Geometry follows spec/io-ring.md "Geometry".
# Devices are placed from the netlists (W, L, nf) inside guard rings and wired
# from the same netlists: S/D straps and gate contacts on Metal2, tap rings tied
# to their rail, a small grid router (Metal2/3/4) for the nets, and pre-planned
# Metal4 trunks that tie every rail stub of a net together. The corner turn
# joins the right-edge and top-edge stubs of each net. LVS (#17) is the proof;
# the drawing is connectivity only. Nothing here is ESD-rated or qualified.
import heapq
import math
import os
import re

import pya

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:  # pragma: no cover - older klayout -r
    HERE = os.path.abspath("layout")
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "gf180_io_ring.gds")

# gf180mcu layer numbers: libs.tech/klayout/tech/gf180mcu.lyp, open_pdks f6eeac7
L = {
    "COMP": (22, 0), "NWELL": (21, 0), "POLY": (30, 0), "PPLUS": (31, 0),
    "NPLUS": (32, 0), "CONT": (33, 0), "M1": (34, 0), "V1": (35, 0),
    "M2": (36, 0), "V2": (38, 0), "M3": (42, 0), "V3": (40, 0),
    "M4": (46, 0), "V4": (41, 0), "M5": (81, 0), "PAD": (37, 0),
    "DUALGATE": (55, 0), "ESD": (24, 0), "BNDRY": (0, 0),
    "M1_LBL": (34, 10), "M2_LBL": (36, 10), "M3_LBL": (42, 10),
    "M4_LBL": (46, 10), "M5_LBL": (81, 10),
}
VIA_AT = ("V2", "V3")  # via between routing layer l and l + 1 (M2/M3/M4)
ROUTE_LAYERS = ("M2", "M3", "M4")

PITCH, DEPTH, CORNER = 75.0, 350.0, 355.0
SIDE_FILL = 10.0  # the ring's filler cell is the 10 um variant
DBU = 0.001

layout = pya.Layout()
layout.dbu = DBU
LI = {k: layout.layer(*v) for k, v in L.items()}


def um(v):
    return int(round(v / DBU))


def box(cell, layer, x0, y0, x1, y1):
    cell.shapes(LI[layer]).insert(pya.Box(um(x0), um(y0), um(x1), um(y1)))


def label(cell, layer, text, x, y):
    cell.shapes(LI[layer]).insert(pya.Text(text, um(x), um(y)))


# --- rail stubs (spec Geometry): Metal3/4/5, 1 um wide, both cell edges -------
# The spec gives each rail's y extent; per-stub heights (7 or 15 um) are
# chosen here so that no two rails overlap on an edge.
# (net, y0, y1). DVDD spans 118-341, DVSS 70-348.4 (top stub shortened to fit
# above DVDD), core rails at the spec's four y ranges.
STUBS = [
    ("DVSS", 70.0, 85.0), ("DVDD", 118.0, 133.0), ("DVSS", 136.0, 151.0),
    ("DVDD", 160.0, 175.0), ("DVSS", 190.0, 205.0), ("DVDD", 208.0, 223.0),
    ("DVSS", 226.0, 241.0), ("VSS", 246.0, 253.0), ("VDD", 254.0, 261.0),
    ("DVSS", 264.0, 279.0), ("DVDD", 280.0, 295.0), ("VDD", 310.0, 317.0),
    ("VSS", 318.0, 325.0), ("DVDD", 326.0, 341.0), ("DVSS", 342.4, 348.4),
]
STUB_X = [(0.0, 1.0), (PITCH - 1.0, PITCH)]
RAIL_LAYERS = ["M3", "M4", "M5"]


def check_stubs():
    ext = {}
    for net, a, b in STUBS:
        lo, hi = ext.get(net, (1e9, -1e9))
        ext[net] = (min(lo, a), max(hi, b))
    assert ext["DVDD"] == (118.0, 341.0), ext
    assert ext["DVSS"] == (70.0, 348.4), ext
    ys = sorted((a, b) for _, a, b in STUBS)
    for (a0, b0), (a1, b1) in zip(ys, ys[1:]):
        assert b0 < a1, "stub overlap %s %s" % ((a0, b0), (a1, b1))


def stub_stack(cell, x0, x1, y0, y1, net, text=True):
    for lyr in RAIL_LAYERS:
        box(cell, lyr, x0, y0, x1, y1)
    # one column of Via3/Via4 at 0.56 um pitch joins the three layers
    xc = (x0 + x1) / 2.0
    y = y0 + 0.4
    while y + 0.26 <= y1 - 0.2:
        for v in ("V3", "V4"):
            box(cell, v, xc - 0.13, y, xc + 0.13, y + 0.26)
        y += 0.56
    if text:
        for lyr in ("M3_LBL", "M4_LBL", "M5_LBL"):
            label(cell, lyr, net, xc, (y0 + y1) / 2.0)


def rails(cell, width=PITCH, height=DEPTH):
    for net, a, b in STUBS:
        for x0, x1 in ((0.0, 1.0), (width - 1.0, width)):
            stub_stack(cell, x0, x1, a, b, net)


def tie_bar(cell, net, x_to, y):
    """M3 bar from the left-edge stub segment of `net` at height y to x_to."""
    seg = [s for s in STUBS if s[0] == net and s[1] <= y <= s[2]]
    assert seg, "no %s stub at y=%s" % (net, y)
    box(cell, "M3", 0.0, y - 0.25, x_to, y + 0.25)


# --- wiring: terminals, rail trunks, grid router -------------------------------
# Routing grid shared by the pad cells (Metal2 vertical-preferred, Metal3
# horizontal-preferred, Metal4 vertical-preferred). Nodes are 0.78 um apart,
# wires 0.4 um wide, via pads 0.46 um, so two wires on adjacent tracks keep
# 0.38 um. Rail trunks sit on the first columns (Metal4) and tie every stub of
# a net to one conductor; the router connects everything else.
GP, GX0, NX = 0.78, 2.4, 91          # x_i = 2.4 + 0.78 i: i = 90 mirrors i = 0
GY0, NY = 64.0, 364                  # rows span y = 64 ... 347.1 (below the pad)
WIRE, VPAD, VIA = 0.4, 0.46, 0.26
INFLATE = 0.6        # M2 nodes this close to another net's M2 shape are unusable
SPACE = 0.3          # stub-to-foreign-M2 clearance
TRUNK_I = {"DVSS": 0, "DVDD": 2, "VSS": 4, "VDD": 6}
BUCKET = 4.0


def gx(i):
    return GX0 + GP * i


def gy(j):
    return GY0 + GP * j


class Wiring:
    def __init__(self, cell):
        self.cell = cell
        self.occ = {}      # (layer, i, j) -> net: node carries drawn metal of net
        self.blk = {}      # (0, i, j) -> net or "#": too close to foreign M2
        self.m2 = []       # (net, x0, y0, x1, y1) every drawn M2 shape
        self.hash = {}
        self.terms = {}    # net -> [(x, y)] M2 points awaiting a grid node
        self.groups = {}   # net -> [[node, ...]] metal already on the grid
        self.unrouted = []

    # -- M2 shapes ------------------------------------------------------------
    def m2rect(self, net, x0, y0, x1, y1, draw=True):
        if draw:
            box(self.cell, "M2", x0, y0, x1, y1)
        k = len(self.m2)
        self.m2.append((net, x0, y0, x1, y1))
        for bx in range(int(x0 // BUCKET), int(x1 // BUCKET) + 1):
            for by in range(int(y0 // BUCKET), int(y1 // BUCKET) + 1):
                self.hash.setdefault((bx, by), []).append(k)
        i0 = max(0, math.ceil((x0 - INFLATE - GX0) / GP))
        i1 = min(NX - 1, math.floor((x1 + INFLATE - GX0) / GP))
        j0 = max(0, math.ceil((y0 - INFLATE - GY0) / GP))
        j1 = min(NY - 1, math.floor((y1 + INFLATE - GY0) / GP))
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                cur = self.blk.get((0, i, j))
                self.blk[(0, i, j)] = net if cur in (None, net) else "#"

    def conflict(self, net, x0, y0, x1, y1):
        seen = set()
        for bx in range(int((x0 - SPACE) // BUCKET), int((x1 + SPACE) // BUCKET) + 1):
            for by in range(int((y0 - SPACE) // BUCKET), int((y1 + SPACE) // BUCKET) + 1):
                for k in self.hash.get((bx, by), ()):
                    if k in seen:
                        continue
                    seen.add(k)
                    n, a, b, c, d = self.m2[k]
                    if n != net and a < x1 + SPACE and c > x0 - SPACE \
                            and b < y1 + SPACE and d > y0 - SPACE:
                        return True
        return False

    def via1(self, net, x, y):
        box(self.cell, "V1", x - VIA / 2, y - VIA / 2, x + VIA / 2, y + VIA / 2)
        self.m2rect(net, x - VPAD / 2, y - VPAD / 2, x + VPAD / 2, y + VPAD / 2)

    def terminal(self, net, x, y):
        self.terms.setdefault(net, []).append((x, y))
        label(self.cell, "M2_LBL", net, x, y)    # one net label per terminal

    # -- gate / diffusion contacts -------------------------------------------
    def m1_contact(self, net, xc, yc):
        """M1 pad with V1 + M2 pad at (xc, yc); registers the terminal."""
        box(self.cell, "M1", xc - 0.25, yc - 0.25, xc + 0.25, yc + 0.25)
        self.via1(net, xc, yc)
        self.terminal(net, xc, yc)

    def poly_contact(self, net, xc, yc):
        box(self.cell, "POLY", xc - 0.35, yc - 0.35, xc + 0.35, yc + 0.35)
        box(self.cell, "CONT", xc - CT / 2, yc - CT / 2, xc + CT / 2, yc + CT / 2)
        self.m1_contact(net, xc, yc)

    # -- rail trunks ------------------------------------------------------------
    def trunks(self, stubs, width=PITCH):
        """Metal4 trunk per rail net on each side, Metal3 bars from every stub."""
        for net, ti in TRUNK_I.items():
            ss = [(a, b) for n, a, b in stubs if n == net]
            for side in (0, 1):
                i = ti if side == 0 else NX - 1 - ti
                x = gx(i)
                rows = []
                for a, b in ss:
                    j = min(range(NY), key=lambda jj: abs(gy(jj) - (a + b) / 2))
                    assert a + 0.3 <= gy(j) <= b - 0.3, (net, a, b)
                    rows.append(j)
                    ex = 0.6 if side == 0 else width - 0.6
                    box(self.cell, "M3", min(ex, x) - 0.2, gy(j) - 0.2, max(ex, x) + 0.2, gy(j) + 0.2)
                    lo, hi = sorted((i, 0 if side == 0 else NX - 1))
                    for ii in range(lo, hi + 1):
                        self.occ[(1, ii, j)] = net
                    self.via23(1, x, gy(j))
                box(self.cell, "M4", x - 0.2, gy(min(rows)) - 0.2, x + 0.2, gy(max(rows)) + 0.2)
                nodes = [(2, i, j) for j in range(min(rows), max(rows) + 1)]
                for nd in nodes:
                    self.occ[nd] = net
                self.groups.setdefault(net, []).append(nodes)

    def close_gaps(self, layer="M2", gap=0.15):
        """Fill sub-minimum gaps between drawn Metal2 shapes (morphological
        close). The deck's spacing rule is geometric, so a 0.1 um sliver
        between two shapes of the same net is a violation; a gap this small
        between two nets would be a short, which check_connectivity.py catches."""
        shapes = self.cell.shapes(LI[layer])
        reg = pya.Region(shapes)
        closed = reg.sized(int(gap / layout.dbu), 2).sized(-int(gap / layout.dbu), 2)
        shapes.clear()
        shapes.insert(closed)

    def via23(self, l, x, y):
        """Via between routing layer l and l+1 with pads on both."""
        box(self.cell, VIA_AT[l], x - VIA / 2, y - VIA / 2, x + VIA / 2, y + VIA / 2)
        for lyr in (ROUTE_LAYERS[l], ROUTE_LAYERS[l + 1]):
            box(self.cell, lyr, x - VPAD / 2, y - VPAD / 2, x + VPAD / 2, y + VPAD / 2)

    # -- terminal -> grid node ---------------------------------------------------
    def stub(self, x, y, nx, ny, order):
        h = WIRE / 2
        if order == 0:   # horizontal first, then vertical
            return [(min(x, nx) - h, y - h, max(x, nx) + h, y + h),
                    (nx - h, min(y, ny) - h, nx + h, max(y, ny) + h)]
        return [(x - h, min(y, ny) - h, x + h, max(y, ny) + h),
                (min(x, nx) - h, ny - h, max(x, nx) + h, ny + h)]

    def attach(self, net, x, y):
        i0, j0 = round((x - GX0) / GP), round((y - GY0) / GP)
        cands = sorted(((di, dj) for di in range(-10, 11) for dj in range(-10, 11)),
                       key=lambda t: (gx(i0 + t[0]) - x) ** 2 + (gy(j0 + t[1]) - y) ** 2)
        for di, dj in cands:
            i, j = i0 + di, j0 + dj
            if not (0 <= i < NX and 0 <= j < NY):
                continue
            key = (0, i, j)
            if not self.usable(key, net):
                continue
            nxp, nyp = gx(i), gy(j)
            for order in (0, 1):
                rects = self.stub(x, y, nxp, nyp, order)
                pad = (nxp - VPAD / 2, nyp - VPAD / 2, nxp + VPAD / 2, nyp + VPAD / 2)
                if any(self.conflict(net, *r) for r in rects + [pad]):
                    continue
                for r in rects + [pad]:
                    self.m2rect(net, *r)
                self.occ[key] = net
                return key
        raise RuntimeError("no grid access for net %s at (%.2f, %.2f)" % (net, x, y))

    def usable(self, key, net):
        o = self.occ.get(key)
        return o == net or (o is None and self.blk.get(key) in (None, net))

    # -- router ------------------------------------------------------------------
    def route(self):
        groups = {n: [list(g) for g in gs] for n, gs in self.groups.items()}
        for net in sorted(self.terms):
            for (x, y) in self.terms[net]:
                groups.setdefault(net, []).append([self.attach(net, x, y)])
        order = sorted(groups, key=lambda n: (n not in TRUNK_I, self.span(groups[n])))
        for net in order:
            self.route_net(net, groups[net])
        return self.unrouted

    @staticmethod
    def span(gs):
        pts = [(gx(n[1]), gy(n[2])) for g in gs for n in g[:1]]
        xs, ys = zip(*pts)
        return (max(xs) - min(xs)) + (max(ys) - min(ys))

    def route_net(self, net, gs):
        if len(gs) < 2:
            return
        tree = set(gs[0])
        left = [set(g) for g in gs[1:]]
        while left:
            goal = {}
            for k, g in enumerate(left):
                for n in g:
                    goal[n] = k
            path = self.dijkstra(net, tree, goal)
            if path is None:
                self.unrouted.append(net)
                return
            k = goal[path[-1]]
            self.draw(net, path)
            tree |= set(path) | left[k]
            left.pop(k)

    def dijkstra(self, net, src, goal):
        dist = {n: 0 for n in src}
        prev = {}
        heap = [(0, n) for n in src]
        heapq.heapify(heap)
        while heap:
            d, n = heapq.heappop(heap)
            if d > dist.get(n, 1e18):
                continue
            if n in goal:
                path = [n]
                while path[-1] in prev:
                    path.append(prev[path[-1]])
                return path[::-1]
            l, i, j = n
            moves = []
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                horiz = di != 0
                pref = (not horiz) if l != 1 else horiz
                moves.append(((l, i + di, j + dj), 1.0 if pref else 3.0))
            for dl in (-1, 1):
                if 0 <= l + dl <= 2:
                    moves.append(((l + dl, i, j), 6.0))
            for m, c in moves:
                if not (0 <= m[1] < NX and 0 <= m[2] < NY):
                    continue
                if not self.usable(m, net) and m not in goal:
                    continue
                nd = d + c
                if nd < dist.get(m, 1e18):
                    dist[m] = nd
                    prev[m] = n
                    heapq.heappush(heap, (nd, m))
        return None

    def draw(self, net, path):
        h = WIRE / 2
        for a, b in zip(path, path[1:]):
            if a[0] == b[0]:
                xa, ya, xb, yb = gx(a[1]), gy(a[2]), gx(b[1]), gy(b[2])
                box(self.cell, ROUTE_LAYERS[a[0]], min(xa, xb) - h, min(ya, yb) - h,
                    max(xa, xb) + h, max(ya, yb) + h)
            else:
                self.via23(min(a[0], b[0]), gx(a[1]), gy(a[2]))
        for n in path:
            self.occ[n] = net


# --- device primitives --------------------------------------------------------
CT = 0.22        # contact
SD = 0.62        # source/drain column width
RING_W = 1.0     # tap ring width
IMP_ENC = 0.4    # Nplus/Pplus extension beyond a device's comp and gate region


def contacts(cell, x0, y0, x1, y1, enc=0.12):
    y = y0 + enc
    while y + CT <= y1 - enc + 1e-9:
        x = x0 + enc
        while x + CT <= x1 - enc + 1e-9:
            box(cell, "CONT", x, y, x + CT, y + CT)
            x += CT + 0.25
        y += CT + 0.25


def mos(cell, x, y, kind, w, l, nf, thick, rows=1, nets=None, wr=None):
    """nf-finger MOS, W total split over fingers (and `rows` stacked blocks).
    nets = (drain, gate, source); with `wr` the S/D columns get Metal2 straps
    (source = even columns at the top, drain = odd columns at the bottom) and
    the gates a poly bar with one contact. Returns (x1, y1) of the drawn extent
    (COMP + poly, before implant)."""
    per_row = nf // rows
    wf = w / nf
    pitch = l + SD
    width = per_row * pitch + SD
    ytop = y
    dg_y0 = dg_y1 = None
    for r in range(rows):
        y0 = ytop + 0.4
        y1 = y0 + wf
        box(cell, "COMP", x, y0, x + width, y1)
        for i in range(per_row):
            gx = x + SD + i * pitch
            box(cell, "POLY", gx, y0 - 0.3, gx + l, y1 + 0.3)
        for i in range(per_row + 1):
            sx = x + i * pitch
            contacts(cell, sx, y0, sx + SD, y1)
            box(cell, "M1", sx + 0.06, y0, sx + SD - 0.06, y1)
        imp = "NPLUS" if kind == "n" else "PPLUS"
        # implant overlaps the gate region by IMP_ENC (deck: nplus/pplus
        # enclosing poly2 and comp)
        box(cell, imp, x - IMP_ENC, y0 - IMP_ENC, x + width + IMP_ENC, y1 + IMP_ENC)
        dg_y0 = y0 if dg_y0 is None else dg_y0
        dg_y1 = y1
        if wr:
            drain, gate, source = nets
            for par, net, yv in ((0, source, y1 - 0.37), (1, drain, y0 + 0.37)):
                cols = [x + i * pitch + SD / 2 for i in range(par, per_row + 1, 2)]
                for xc in cols:
                    wr.via1(net, xc, yv)
                if len(cols) > 1:
                    wr.m2rect(net, cols[0] - VPAD / 2, yv - VPAD / 2, cols[-1] + VPAD / 2, yv + VPAD / 2)
                wr.terminal(net, cols[0], yv)
            g0, g1 = x + SD, x + SD + (per_row - 1) * pitch + l
            box(cell, "POLY", g0, y1 + 0.25, g1, y1 + 0.95)
            wr.poly_contact(gate, g0 + min(l, 1.0) / 2, y1 + 0.6)
        ytop = y1 + 1.4
    if thick:
        # one marker over all stacked rows, so no sub-minimum gap between rows
        box(cell, "DUALGATE", x - 0.4, dg_y0 - 0.7, x + width + 0.4, dg_y1 + 0.7)
    return x + width, ytop - 0.4


def ring(cell, x0, y0, x1, y1, kind, net, wr=None):
    """Non-broken tap ring around (x0,y0)-(x1,y1): P+ tap for 'p' substrate
    (tied DVSS/VSS), N+ tap inside an Nwell for 'n' well (tied DVDD/VDD)."""
    o = RING_W
    ox0, oy0, ox1, oy1 = x0 - o, y0 - o, x1 + o, y1 + o
    imp = "PPLUS" if kind == "p" else "NPLUS"
    for (a, b, c, d) in ((ox0, oy0, ox1, y0), (ox0, y1, ox1, oy1),
                         (ox0, y0, x0, y1), (x1, y0, ox1, y1)):
        box(cell, "COMP", a, b, c, d)
        box(cell, imp, a - 0.16, b - 0.16, c + 0.16, d + 0.16)
        contacts(cell, a, b, c, d, enc=0.2)
        box(cell, "M1", a, b, c, d)
    if kind == "n":
        box(cell, "NWELL", ox0 - 0.6, oy0 - 0.6, ox1 + 0.6, oy1 + 0.6)
    label(cell, "M1_LBL", net, ox0 + 0.5, oy0 + 0.5)
    if wr:
        wr.via1(net, ox0 + 0.5, (y0 + y1) / 2)
        wr.terminal(net, ox0 + 0.5, (y0 + y1) / 2)
    return ox0, oy0, ox1, oy1


def parse_spice(path):
    """-> list of dict(name, model, params) for X (device) lines; joined
    continuation lines. Skips the sch_path comment and .subckt lines."""
    text = open(path).read().replace("\n+", " ")
    devs = []
    for ln in text.splitlines():
        if not ln.startswith("X"):
            continue
        tok = ln.split()
        model = next(t for t in tok if re.match(r"(nfet|pfet|cap_nmos)_", t))
        prm = {}
        for t in tok:
            m = re.match(r"(L|W|nf|c_width|c_length)=([0-9.]+)u?$", t)
            if m:
                prm[m.group(1)] = float(m.group(2))
        nets = tuple(tok[1:5]) if model.startswith(("nfet", "pfet")) else tuple(tok[1:3])
        devs.append({"name": tok[0], "model": model, "p": prm, "n": nets})
    diodes = []
    for ln in text.splitlines():
        if ln.startswith("D_"):
            diodes.append(ln.split()[0])
    return devs, diodes


def classify(d):
    m = d["model"]
    return ("n" if m.startswith("nfet") else "p", m.endswith("06v0"))


MAXW = 67.5


def place_group(cell, devs, y, kind, thick, net, wr=None):
    """Pack single/multi-finger devices of one flavour into rows inside a tap
    ring tied to `net`. Returns the y above the group's outer ring."""
    x0 = RING_W + 1.5 + 1.0
    cx, cy, rowh, xmax, first = x0, y + RING_W + 1.5, 0.0, x0, True
    for d in devs:
        p = d["p"]
        nf = int(p.get("nf", 1))
        rows = 1
        while (nf // rows) * (p["L"] + SD) + SD > MAXW - 1.0 and rows < nf:
            rows += 1
        wf = p["W"] / nf
        w_est = (nf // rows) * (p["L"] + SD) + SD
        if cx + w_est > x0 + MAXW and not first:
            cx, cy, rowh = x0, cy + rowh + 2.5, 0.0
        ex, ey = mos(cell, cx, cy, kind, p["W"], p["L"], nf, thick, rows,
                     d["n"][:3], wr)
        label(cell, "M1_LBL", d["name"], cx, cy)
        rowh = max(rowh, ey - cy)
        xmax = max(xmax, ex)
        cx = ex + 2.5
        first = False
    gx1 = max(xmax, x0 + 10.0)
    gy1 = cy + rowh + 1.0
    ring(cell, x0 - 1.5, y + RING_W + 0.5, gx1 + 1.5, gy1 + 0.0, "p" if kind == "n" else "n", net, wr)
    return gy1 + RING_W + 1.5


def diode(cell, x, y, kind, area_w, area_h, net=None, wr=None):
    """diode_nd2ps_06v0 (N+/Psub) or diode_pd2nw_06v0 (P+/Nwell), 10 x 17.8."""
    box(cell, "COMP", x, y, x + area_w, y + area_h)
    box(cell, "DUALGATE", x - 0.5, y - 0.5, x + area_w + 0.5, y + area_h + 0.5)
    if kind == "n":
        box(cell, "NPLUS", x - 0.2, y - 0.2, x + area_w + 0.2, y + area_h + 0.2)
    else:
        box(cell, "PPLUS", x - 0.2, y - 0.2, x + area_w + 0.2, y + area_h + 0.2)
        box(cell, "NWELL", x - 1.0, y - 1.0, x + area_w + 1.0, y + area_h + 1.0)
    contacts(cell, x, y, x + area_w, y + area_h, enc=0.3)
    box(cell, "M1", x + 0.2, y + 0.2, x + area_w - 0.2, y + area_h - 0.2)
    if wr:
        wr.via1(net, x + area_w / 2, y + area_h / 2)
        wr.terminal(net, x + area_w / 2, y + area_h / 2)


def mos_cap(cell, x, y, w, h, thick, gate=None, body=None, wr=None):
    box(cell, "COMP", x, y, x + w, y + h)
    box(cell, "POLY", x + 1.0, y - 0.3, x + w - 1.0, y + h + 0.3)
    box(cell, "NPLUS", x - IMP_ENC, y - IMP_ENC, x + w + IMP_ENC, y + h + IMP_ENC)
    if thick:
        box(cell, "DUALGATE", x - 0.5, y - 0.5, x + w + 0.5, y + h + 0.5)
    if wr:
        # gate: poly lead above the plate; body: both diffusion strips beside the poly
        box(cell, "POLY", x + 1.0, y + h, x + 2.2, y + h + 1.15)
        wr.poly_contact(gate, x + 1.6, y + h + 0.8)
        for sx in (x + 0.2, x + w - 0.8):
            contacts(cell, sx, y + 0.3, sx + 0.6, y + h - 0.3, enc=0.19)
            box(cell, "M1", sx, y + 0.3, sx + 0.6, y + h - 0.3)
            wr.via1(body, sx + 0.3, y + h / 2)
            wr.terminal(body, sx + 0.3, y + h / 2)


# --- cells --------------------------------------------------------------------
def new_cell(name):
    c = layout.create_cell(name)
    box(c, "BNDRY", 0, 0, PITCH, DEPTH)
    rails(c)
    wr = Wiring(c)
    wr.trunks(STUBS)
    return c, wr


def pad_landing(c, wr):
    box(c, "M5", 7.5, 2.0, 67.5, 62.0)       # spec: 60 x 60 at (7.5, 2)
    box(c, "PAD", 9.5, 4.0, 65.5, 60.0)      # >= 2.0 um enclosure by Metal5
    label(c, "M5_LBL", "PAD", 37.5, 32.0)
    # PAD net leaves the landing through Metal4 at x = 37.5 (grid column 45)
    i = round((37.5 - GX0) / GP)
    box(c, "V4", gx(i) - VIA / 2, 60.0, gx(i) + VIA / 2, 60.0 + VIA)
    box(c, "M4", gx(i) - WIRE / 2, 59.9, gx(i) + WIRE / 2, gy(0) + WIRE / 2)
    wr.groups.setdefault("PAD", []).append([(2, i, 0)])
    wr.occ[(2, i, 0)] = "PAD"


def pin(c, name, x, y, wr, layer="M2"):
    box(c, layer, x - 0.5, y - 0.5, x + 0.5, y + 0.5)
    label(c, layer + "_LBL", name, x, y)
    wr.m2rect(name, x - 0.5, y - 0.5, x + 0.5, y + 0.5, draw=False)
    wr.terminal(name, x, y)


def pick(devs, kind, thick, bulk, names=None, skip=()):
    out = []
    for d in devs:
        if d["name"] in skip or (names is not None and d["name"] not in names):
            continue
        if classify(d) == (kind, thick) and d["n"][3] == bulk:
            out.append(d)
    return out


def build_gpio():
    c, wr = new_cell("gpio")
    pad_landing(c, wr)
    devs, _ = parse_spice(os.path.join(ROOT, "design", "gpio.spice"))
    by = {d["name"]: d for d in devs}
    # pad-side clamps (178 um^2 each, spec ESD network): D_dn then D_up, each in
    # its own tap ring (1.5 um clear of the diode): PAD is the N+ side of D_dn
    # and the P+ side of D_up
    diode(c, 6.0, 68.0, "n", 10.0, 17.8, "PAD", wr)
    ring(c, 4.5, 66.5, 17.5, 87.3, "p", "DVSS", wr)
    diode(c, 46.0, 68.0, "p", 10.0, 17.8, "PAD", wr)
    ring(c, 44.5, 66.5, 57.5, 87.3, "n", "DVDD", wr)
    # output driver devices: PMOS in Nwell + N+ ring, NMOS + P+ ring; every
    # group shares one bulk net, so the ring ties exactly that net
    y = 98.0
    drv = ("XMN_drv", "XMP_drv")
    todo = [("n", True, "DVSS", ("XMN_drv",), ()), ("p", True, "DVDD", ("XMP_drv",), ()),
            ("n", True, "DVSS", None, drv), ("p", True, "DVDD", None, drv),
            ("p", True, "VDD", None, ()), ("n", True, "VSS", None, ())]
    placed = 0
    for kind, thick, bulk, names, skip in todo:
        g = pick(devs, kind, thick, bulk, names, skip)
        if g:
            placed += len(g)
            y = place_group(c, g, y, kind, thick, bulk, wr)
    assert y < 240, y
    yc = max(y, 250.0)
    for kind, bulk in (("n", "VSS"), ("p", "VDD")):
        g = pick(devs, kind, False, bulk)
        placed += len(g)
        yc = place_group(c, g, yc, kind, False, bulk, wr)
    assert placed == len(devs), (placed, len(devs))
    assert yc < 346, "gpio overflows the cell: %s" % yc
    # core-side pins on Metal2 along the top edge, port order of gpio.spice
    for i, n in enumerate(("A", "OE", "IE", "PU", "PD", "Y")):
        pin(c, n, 12.0 + i * 10.0, 347.5, wr)
    assert not wr.route(), wr.unrouted
    wr.close_gaps()
    return c


def build_supply(name, rail_dev_net, big_thick):
    c, wr = new_cell(name)
    devs, _ = parse_spice(os.path.join(ROOT, "design", name + ".spice"))
    bigs = [d for d in devs if d["model"].startswith(("nfet", "pfet"))]
    caps = [d for d in devs if d["model"].startswith("cap")]
    y = 70.0
    for cp in caps:
        p = cp["p"]
        mos_cap(c, 17.0, y + 2.0, p["c_width"], p["c_length"], cp["model"].endswith("06v0"),
                cp["n"][0], cp["n"][1], wr)
        label(c, "M1_LBL", cp["name"], 17.0, y + 2.0)
        y += p["c_length"] + 8.0
    sel = [d for d in bigs if d["name"] != "XMN_clampio"]
    y = place_group(c, [d for d in sel if classify(d)[0] == "n"], y, "n", True, rail_dev_net[0], wr)
    y = place_group(c, [d for d in sel if classify(d)[0] == "p"], y, "p", True, rail_dev_net[1], wr)
    clamp = [d for d in bigs if d["name"] == "XMN_clampio"][0]
    y = place_group(c, [clamp], y + 4.0, "n", True, rail_dev_net[0], wr)
    box(c, "ESD", 3.0, y - 80.0, PITCH - 3.0, y)  # ESD implant over the clamp group
    assert y < 346, "%s overflows: %s" % (name, y)
    assert not wr.route(), wr.unrouted
    wr.close_gaps()
    return c


def build_core_pad():
    c, wr = new_cell("core_pad")
    devs, _ = parse_spice(os.path.join(ROOT, "design", "core_pad.spice"))
    y = 70.0
    for cp in [d for d in devs if d["model"].startswith("cap")]:
        p = cp["p"]
        mos_cap(c, 22.0, y + 2.0, p["c_width"], p["c_length"], False,
                cp["n"][0], cp["n"][1], wr)
        y += p["c_length"] + 8.0
    mosd = [d for d in devs if d["model"].startswith(("nfet", "pfet"))]
    clamp = [d for d in mosd if d["name"] == "XMN_clampco"]
    rest = [d for d in mosd if d["name"] != "XMN_clampco"]
    y = place_group(c, [d for d in rest if classify(d)[0] == "n"], y, "n", False, "VSS", wr)
    y = place_group(c, [d for d in rest if classify(d)[0] == "p"], y, "p", False, "VDD", wr)
    y = place_group(c, clamp, y + 4.0, "n", False, "VSS", wr)
    assert y < 346, "core_pad overflows: %s" % y
    assert not wr.route(), wr.unrouted
    wr.close_gaps()
    return c


def build_filler(name, width):
    c = layout.create_cell(name)
    box(c, "BNDRY", 0, 0, width, DEPTH)
    # fillers carry the rails through as one stripe per net edge-to-edge
    for net, a, b in STUBS:
        for lyr in RAIL_LAYERS:
            box(c, lyr, 0.0, a, width, b)
    return c


def build_corner():
    c = layout.create_cell("corner")
    box(c, "BNDRY", 0, 0, CORNER, CORNER)
    # rail stubs on the right edge (x=354..355, mate with the next pad cell)
    # and on the top edge (y=354..355), same ordinate list, so the turn closes
    for net, a, b in STUBS:
        stub_stack(c, CORNER - 1.0, CORNER, a, b, net)
        stub_stack_h(c, a, b, CORNER - 1.0, CORNER, net)
    # The turn: per net an L of Metal4 (vertical trunk x_k joined to a horizontal
    # trunk y_k at their corner), Metal3 bars from every right-edge stub to the
    # vertical trunk and from every top-edge stub down to the horizontal one.
    # Nets nest (outer x_k, y_k first), so no two trunks cross.
    for k, net in enumerate(("DVSS", "DVDD", "VSS", "VDD")):
        xk = yk = CORNER - 2.6 - 1.6 * k
        mids = [(a + b) / 2.0 for n, a, b in STUBS if n == net]
        for m in mids:
            box(c, "M3", xk - 0.2, m - 0.2, CORNER - 0.6, m + 0.2)   # right stub -> trunk
            box(c, "V3", xk - 0.13, m - 0.13, xk + 0.13, m + 0.13)
            box(c, "M3", m - 0.2, yk - 0.2, m + 0.2, CORNER - 0.6)   # top stub -> trunk
            box(c, "V3", m - 0.13, yk - 0.13, m + 0.13, yk + 0.13)
        box(c, "M4", xk - 0.2, min(mids) - 0.2, xk + 0.2, yk + 0.2)
        box(c, "M4", min(mids) - 0.2, yk - 0.2, xk + 0.2, yk + 0.2)
    return c


def stub_stack_h(cell, xa, xb, y0, y1, net):
    for lyr in RAIL_LAYERS:
        box(cell, lyr, xa, y0, xb, y1)
    yc = (y0 + y1) / 2.0
    x = xa + 0.4
    while x + 0.26 <= xb - 0.2:
        for v in ("V3", "V4"):
            box(cell, v, x, yc - 0.13, x + 0.26, yc + 0.13)
        x += 0.56
    for lyr in ("M3_LBL", "M4_LBL", "M5_LBL"):
        label(cell, lyr, net, (xa + xb) / 2.0, yc)


def build_ring():
    ring_c = layout.create_cell("io_ring")
    side = 5 * PITCH + SIDE_FILL
    total = 2 * CORNER + side
    seq = ["gpio", "dvdd_pad", "gpio", "dvss_pad", "core_pad", "filler"]
    width = {"filler": SIDE_FILL}
    cellref = {n: layout.cell(n) for n in
               ("gpio", "dvdd_pad", "dvss_pad", "core_pad", "corner", "filler")}
    # (rotation code, corner placement, cell origin function)
    rots = [0, 1, 2, 3]  # R0, R90, R180, R270
    gp = 0
    for s in range(4):
        r = rots[s]
        # corner at the start of side s
        cpos = [(0, 0), (total, 0), (total, total), (0, total)][s]
        ring_c.insert(pya.CellInstArray(cellref["corner"].cell_index(),
                                        pya.Trans(r, False, um(cpos[0]), um(cpos[1]))))
        t = CORNER
        for n in seq:
            w = width.get(n, PITCH)
            if s == 0:
                org = (t, 0)
            elif s == 1:
                org = (total, t)
            elif s == 2:
                org = (total - t, total)
            else:
                org = (0, total - t)
            tr = pya.Trans(r, False, um(org[0]), um(org[1]))
            ring_c.insert(pya.CellInstArray(cellref[n].cell_index(), tr))
            if n == "gpio":
                lbl = "PAD%d" % gp
                p = tr * pya.Point(um(37.5), um(32.0))
                ring_c.shapes(LI["M5_LBL"]).insert(pya.Text(lbl, p.x, p.y))
                for pn, px in zip(("A", "OE", "IE", "PU", "PD", "Y"),
                                  [12.0 + i * 10.0 for i in range(6)]):
                    q = tr * pya.Point(um(px), um(347.5))
                    ring_c.shapes(LI["M2_LBL"]).insert(
                        pya.Text(pn + str(gp), q.x, q.y))
                gp += 1
            t += w
    return ring_c


check_stubs()
build_gpio()
build_supply("dvdd_pad", ("DVSS", "DVDD"), True)
build_supply("dvss_pad", ("DVSS", "DVDD"), True)
build_core_pad()
build_corner()
build_filler("filler", SIDE_FILL)
build_filler("filler_1", 1.0)
build_filler("filler_5", 5.0)
top = build_ring()

# spec Geometry: every cell's bbox is exactly its nominal size
for name, (w, h) in {"gpio": (PITCH, DEPTH), "dvdd_pad": (PITCH, DEPTH),
                     "dvss_pad": (PITCH, DEPTH), "core_pad": (PITCH, DEPTH),
                     "filler": (SIDE_FILL, DEPTH), "filler_5": (5.0, DEPTH),
                     "filler_1": (1.0, DEPTH), "corner": (CORNER, CORNER)}.items():
    bb = layout.cell(name).bbox()
    assert (bb.left, bb.bottom, bb.right, bb.top) == (0, 0, um(w), um(h)), (name, bb)

opts = pya.SaveLayoutOptions()
opts.format = "GDS2"
opts.gds2_write_timestamps = False
opts.gds2_write_cell_properties = False
opts.gds2_libname = "gf180_io_ring"
layout.write(OUT, opts)
print("wrote", OUT, "top =", top.name)
