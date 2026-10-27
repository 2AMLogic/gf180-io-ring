# T1 item 4: LVS clean (claim)

Evidence for item 4 of the T1 checklist (`manifests/design-evidence-tiers.md`).
Nothing here says any cell is ESD-rated or qualified: **a match means the
layout's extracted devices and connectivity equal the item-1 netlists under
klt's open `gf180mcu` extraction deck, with the exceptions listed below.**

## Reports

One `klt lvs --format json` report per top cell of `layout/gf180_io_ring.gds`
(`input.content_hash` `sha256:7e83c8f65378af65201414d4b12395bd2df5feaf63786c36164e44893bef2332`, equal to
`manifests/evidence/item2.json`), engine `klayout` (klt 0.8.0, KLayout 0.30.12,
deck `gf180mcu`), reference the item-1 netlist `design/<cell>.spice` unedited,
`reference.form: "subckt-call"`, `options.compare_mos_flavour: true`. Regenerate with
`manifests/evidence/item4/run.sh`; each passes `klt lvs --check <report>`.

| Cell | Report | status | mismatch entries (all `warning`) |
|---|---|---|---|
| `io_ring` | `manifests/evidence/item4/io_ring.json` | `match` | 27 |
| `gpio` | `manifests/evidence/item4/gpio.json` | `match` | 2 |
| `dvdd_pad` | `manifests/evidence/item4/dvdd_pad.json` | `match` | 6 |
| `dvss_pad` | `manifests/evidence/item4/dvss_pad.json` | `match` | 6 |
| `core_pad` | `manifests/evidence/item4/core_pad.json` | `match` | 4 |
| `corner` | `manifests/evidence/item4/corner.json` | `match` | 4 |

`io_ring` compares 267 nets and 1296 devices, all matched. The manifest cites
the `io_ring` report; the others are per-cell evidence. `filler` (and the
unplaced `filler_5`, `filler_1`) has no devices or nets, so the layout netlist
has no circuit for it and `klt lvs` cannot take it as a top; it is instantiated
in `io_ring`, where it is compared (as an empty circuit).

## What the match rests on, and does not

1. **A declared substrate join, not a plain match.** The ring draws no
   deep-Nwell isolation, so the `DVSS`-bulk and `VSS`-bulk NMOS share one
   p-substrate and the extractor reports a single net `DVSS|VSS`
   (`merged_net_labels`). The item-1 netlists keep `DVSS` and `VSS` separate.
   The top-level reports therefore pass `hints.short_nets` `[["DVSS","VSS"]]`,
   which klt records as a `hints.short_nets_applied` warning: "asserted by the
   request ... not independently verified". The netlists are not edited. The
   same compare **without** the hint is committed in `manifests/evidence/item4/raw/`:
   `corner`, `dvdd_pad`, `dvss_pad`, `core_pad` are `match` there too, but
   `gpio` is `mismatch` (52 entries: 34 `device.unmatched`, 9 `net.merged`, 8
   `net.split`, 1 `topology`) and `io_ring` is `mismatch` (2763 entries). That
   is the substrate short, not a wiring error: it is an honest consequence of
   the drawing, and whether the design should isolate the domains is a design
   decision for the spec, not something this item decides.
2. **`power_connectivity.status` is `unchecked` in every report.** The check
   only runs for `reference.form: gate-level-verilog`; for these SPICE
   references it "does not apply here". The rails are **not** verified by this
   item. Rail continuity across abutting cells stays with `klt ring-check` and
   ERC (#24).
3. **MOS capacitors are paired on topology only.** `cap_nmos_03v3` (4 in the
   ring) and `cap_nmos_06v0` (8): `device.placeholder_value` (the converted
   reference carries `C = 0`, so `C` is excluded on both sides; layout
   `C` 3.696e-12 and 3.496e-12) and `device.geometry_not_compared` (`A`, `P`
   are secondary and not compared). Cap size is not verified by LVS.
4. **Other warnings, all in the reports**: `topology.flattened` (the ring
   reference is flattened with `options.flatten_reference`, because the layout
   is extracted flat, so the hierarchy boundaries are not checked);
   `topology` "nets were paired ambiguously; resolved structurally" (21 in
   `io_ring`); `topology` `bjt`, and (pads) the base `nfet`/`pfet` classes ("no devices of
   this class were extracted either", not a mismatch). No device was dropped:
   the deck extracted `nfet`, `pfet`, `diode_nd2ps_06v0`, `diode_pd2nw_06v0`,
   `cap_nmos_03v3` and `cap_nmos_06v0`, and every device in every compared
   cell is matched (`counts.devices.matched` equals the layout count).
5. Thick-oxide versus 3.3 V FETs: `options.compare_mos_flavour: true` puts each
   flavoured device in its own class, so a 5/6 V device against a 3.3 V one is
   a `device.unmatched` pair, not a match. This is on in every report,
   including `raw/`. `L`/`W` are compared as well.

## Layout change this item required

The first runs did not extract the diodes or the MOS capacitors: the deck
recognises `diode_*` only under `DIODE_MK` (115/5) and `cap_*` only under
`MOS_CAP_MK` (166/5), neither of which the generator drew, so those devices
came out as plain `nfet` or vanished. `layout/gen_ring.py` now draws both
markers over the device Comp. The stream was regenerated (`layout/regen.sh`,
item 2) and the nine item-3 DRC reports re-run: all `clean`, 0 violations.
`MOS_CAP_MK` joins the layers the deck has no DRC rule for (see `item3.md`).

## Gaps

No deck gap blocked a `match`, so no upstream issue is linked from this item.
Tool friction met on the way: `hints.short_nets` is documented for
mask-option netlists and is used here for a different purpose (a physical
substrate short); and `klt lvs` converts `cap_nmos_*` calls with a `C`
placeholder, so capacitor size cannot be compared (the deck's own
`device.placeholder_value` text says so).
