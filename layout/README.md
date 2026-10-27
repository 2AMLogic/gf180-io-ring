# layout

Generated layout of the 5 V I/O ring (T1 item 2). Nothing here is ESD-rated or
qualified. The stream is `klt drc` clean against klt's open `gf180mcu` deck only
(T1 item 3, `manifests/evidence/item3.md`, which lists what that deck does not
check); it is LVS-compared against the item-1 netlists with `klt lvs`
(T1 item 4, `manifests/evidence/item4.md`, which states what that compare does
and does not cover). The four supply rails are `klt erc` checked on the
assembled ring (T1 item 11, `manifests/evidence/item11.md`, which states what
that run does and does not cover).

## Regenerate

```console
klayout -b -r layout/gen_ring.py      # writes layout/gf180_io_ring.gds
layout/regen.sh                       # runs it twice (about 20 s each), asserts equal bytes, rewrites manifests/evidence/item2.json
layout/regen.sh --check               # regenerate and compare to the committed stream
klayout -b -r layout/check_connectivity.py   # shorts / opens / unreached nets per cell
```

After a change, rerun `layout/regen.sh`, put the new `content_hash` of
`manifests/evidence/item2.json` in `manifests/gf180-io-ring.json`, and
regenerate the verdict of record (see `manifests/README.md`).

Pins: KLayout 0.28.16 (`klayout -v`), klt 0.8.0 (`klt --version` via
`uvx --from "klayout-tools==0.8.0" klt`). The stream is written with
`gds2_write_timestamps = False`, so it is byte-stable (the byte hash of two
runs matched). The `regen.sh --check` comparison is only meaningful with the
same KLayout version; CI does not run it (CI has no pinned KLayout).

PDK: open_pdks `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7` (`gf180mcuD`, as
resolved by `klt pdk find`); layer numbers are from its
`libs.tech/klayout/tech/gf180mcu.lyp`. This is the revision the spec geometry
used (the item-1 attestation pins the sim side to `c6d73a35…`; see
`spec/io-ring.md` §Geometry).

## Contents

`gf180_io_ring.gds` is one stream: cells `gpio`, `dvdd_pad`, `dvss_pad`,
`core_pad`, `corner`, `filler` (10 µm), `filler_5`, `filler_1`, and `io_ring`
(closed ring, 4 corners + 4 sides of GPIO, `DVDD`, GPIO, `DVSS`, core-supply,
filler; same mix as `design/io_ring.sch`). Cell and pin names follow
`design/*.spice`. `filler_5`/`filler_1` are not instantiated in the ring.

## Wiring

`gen_ring.py` wires each cell from its `design/<cell>.spice`, not from a net
table. Terminals (`Wiring.terminal`) are: source/drain straps on Metal2 (source
columns at the top of the fingers, drain columns at the bottom), one poly
contact per gate bar, the diode plates, the MOS-capacitor gate and diffusion
strips, one Metal2 tie per tap ring, and the `A OE IE PU PD Y` pins. A
grid router (Metal2/3/4, 0.78 µm grid, 0.4 µm wires) joins the terminals of
each net; the `PAD` net leaves the Metal5 landing through a Via4 at x = 37.5 µm.

Rails: in each pad cell a Metal4 trunk per rail net and side (columns 0, 2, 4, 6
for `DVSS`, `DVDD`, `VSS`, `VDD`; mirrored on the right edge) is tied by Metal3
bars and Via3 to every stub of that net, so a net's left and right stubs are one
conductor across the cell. In the corner, each net is an L of Metal4 (vertical
trunk on the right-edge side joined to a horizontal trunk on the top-edge side)
with Metal3 bars from its stubs; the four L's nest, so none crosses another.

Net labels sit on a Metal2 pad of every terminal, so `klt components` and
`layout/check_connectivity.py` can name each component.

## Per-cell status

| Cell | Drawn | Placeholder / not drawn |
|---|---|---|
| all pad cells | 75 × 350 µm boundary; `DVDD`/`DVSS`/`VDD`/`VSS` stubs 1 µm wide on Metal3/4/5 (joined by Via3/Via4) at x = 0–1 and 74–75, y ranges per spec; Metal4 trunks and Metal3 bars tying all stubs of a net | per-stub heights (7 or 15 µm; top `DVSS` stub 6 µm) are my choice within the spec's extents, so rails do not overlap |
| `gpio` | Metal5 60 × 60 µm landing at (7.5, 2) with a Pad opening (2 µm enclosure); both pad clamps at 10 × 17.8 µm, each in its own tap ring; every transistor of `gpio.spice` at its W/L/nf (driver 16 × 5 µm PMOS / 8 × 5 µm NMOS), thick ones under Dualgate, grouped by (type, oxide, bulk net) in tap rings tied to that bulk net; all 34 nets wired (level shifters, NAND/NOR, Schmitt, input stage, pad); `A OE IE PU PD Y` Metal2 pins on the core edge | devices are grouped by flavour, not placed by function, so signal nets run long |
| `dvdd_pad`, `dvss_pad` | devices of the netlist (MOS cap, `XMN_clampio` 60 fingers in two rows under the ESD implant, others) with tap rings; all nets wired (`tio`, `gio`, the four rails); the two cells are identical per the netlists | – |
| `core_pad` | 3.3 V devices of the netlist with tap rings; all nets wired | – |
| `corner` | 355 × 355 µm boundary; rail stubs on its right and top edges; the turn joining the two edges of each net | – |
| `filler*` | 1/5/10 µm × 350 µm boundary with rail stripes edge to edge | – |

What the drawing does not settle: `DVSS`-bulk and `VSS`-bulk NMOS groups sit on
the one p-substrate (no deep-Nwell isolation is drawn), so the substrate taps of
both domains share the substrate; LVS reads that as one net `DVSS|VSS`, so the
item-4 compare declares `hints.short_nets` `DVSS`/`VSS` (see
`manifests/evidence/item4.md`).
The Metal2/3/4 wiring is inside the `klt drc` run below (spacing, width and
enclosure of Metal1-4 and Via1-3 are in the deck); density is not checked. The
router leaves sub-minimum Metal2 gaps between shapes of one net, so each wired
cell closes gaps under 0.3 µm on Metal2 (`Wiring.close_gaps`) after routing.

Tap spacing for 5/6 V devices: the DRM value is not in the open PDK; the spec's
20 µm stand-in applies and is not checked here.

## Checks run

- `klt drc` (klt 0.8.0, deck `gf180mcu`) over `io_ring` and each of the eight
  cells: `status: clean`; envelopes in `manifests/evidence/item3/`. Clean was
  reached by geometry (Nplus/Pplus extension of 0.4 µm beyond comp and gate
  region, diode tap rings 1.5 µm clear of the diode, one Dualgate marker over
  stacked rows, Metal2 gap closing), not by waivers or rule subsets. This
  covers the Metal2/3/4 wiring and its vias.

- `klayout -b -r layout/check_connectivity.py`: for `gpio`, `dvdd_pad`,
  `dvss_pad`, `core_pad` and `corner`, no conductor carries two net labels, no
  net label sits on two conductors, and every net of `design/<cell>.spice` has a
  conductor (34, 6, 6, 6 and 4 nets). It is a label-based geometric check, not
  LVS: a device placed with the wrong terminal would pass it.
- `klt components` (Metal2–5, Via2–4, 0.8.0) on `io_ring`: `DVSS`, `DVDD`, `VSS`
  and `VDD` are each one ring-wide component across all abutments and corners.
- `klt cells layout/gf180_io_ring.gds`: `io_ring` instantiates `core_pad`,
  `corner`, `dvdd_pad`, `dvss_pad`, `filler`, `gpio`; bboxes 75 × 350, 355 × 355,
  10 × 350 (also asserted by the generator).
- Earlier pass (#15): `klt components` over Metal3/4/5 + Via3/Via4 showed every
  stub merged with its neighbour's across each abutment; the stubs of one net
  were then separate segments, now they are one conductor (above). This is
  geometric continuity; the ERC run is item 11 (#24, `manifests/evidence/item11.md`).
