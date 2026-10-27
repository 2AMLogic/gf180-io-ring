# layout

Generated layout of the 5 V I/O ring (T1 item 2). Nothing here is ESD-rated or
qualified. The stream is `klt drc` clean against klt's open `gf180mcu` deck only
(T1 item 3, `manifests/evidence/item3.md`, which lists what that deck does not
check); it is **not** LVS- or ERC-verified (issues #17, #24).

## Regenerate

```console
klayout -b -r layout/gen_ring.py      # writes layout/gf180_io_ring.gds
layout/regen.sh                       # runs it twice, asserts equal bytes, rewrites manifests/evidence/item2.json
layout/regen.sh --check               # regenerate and compare to the committed stream
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

## Per-cell status

| Cell | Drawn | Placeholder / not drawn |
|---|---|---|
| all pad cells | 75 × 350 µm boundary; `DVDD`/`DVSS`/`VDD`/`VSS` stubs 1 µm wide on Metal3/4/5 (joined by Via3/Via4) at x = 0–1 and 74–75, y ranges per spec | per-stub heights (7 or 15 µm; top `DVSS` stub 6 µm) are my choice within the spec's extents, so rails do not overlap |
| `gpio` | Metal5 60 × 60 µm landing at (7.5, 2) with a Pad opening (2 µm enclosure); both pad clamps at 10 × 17.8 µm; every transistor of `gpio.spice` at its W/L/nf (driver 16 × 5 µm PMOS / 8 × 5 µm NMOS), thick ones under Dualgate; tap rings (P+ for NMOS groups, N+ in Nwell for PMOS groups); `A OE IE PU PD Y` Metal2 pins on the core edge | **signal routing between devices, rail connections of rings and devices, level-shifter/Schmitt wiring**: not drawn. Rings are not tied to rails. Devices are grouped by flavour, not placed by function |
| `dvdd_pad`, `dvss_pad` | devices of the netlist (MOS cap, `XMN_clampio` 60 fingers in stacked rows under the ESD implant, others) with tap rings | wiring and rail ties not drawn; the two cells are identical per the netlists |
| `core_pad` | 3.3 V devices of the netlist with tap rings | same |
| `corner` | 355 × 355 µm boundary; rail stubs on its right and top edges | **the turn joining the two edges of each net inside the corner is not drawn** |
| `filler*` | 1/5/10 µm × 350 µm boundary with rail stripes edge to edge | – |

Tap spacing for 5/6 V devices: the DRM value is not in the open PDK; the spec's
20 µm stand-in applies and is not checked here.

## Checks run

- `klt drc` (klt 0.8.0, deck `gf180mcu`) over `io_ring` and each of the eight
  cells: `status: clean`; envelopes in `manifests/evidence/item3/`. Clean was
  reached by geometry (Nplus/Pplus extension of 0.4 µm beyond comp and gate
  region, diode tap rings 1.5 µm clear of the diode, one Dualgate marker over
  stacked rows), not by waivers or rule subsets.

- `klt cells layout/gf180_io_ring.gds`: `io_ring` instantiates `core_pad`,
  `corner`, `dvdd_pad`, `dvss_pad`, `filler`, `gpio`; bboxes 75 × 350, 355 × 355,
  10 × 350 (also asserted by the generator).
- `klt components` over Metal3/4/5 + Via3/Via4 on `io_ring`: every labelled
  `DVDD`/`DVSS`/`VDD`/`VSS` stub is merged with its neighbour's stub across each
  abutment (including both corner-to-side joints and the ring closure); no
  stub is left unpaired. This is geometric continuity per abutment, not ERC
  (#24); the stubs of one net are separate segments, not one connected rail.
