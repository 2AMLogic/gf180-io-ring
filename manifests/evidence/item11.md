# T1 item 11: power delivery, structural (claim)

Evidence for item 11 of the T1 checklist (`manifests/design-evidence-tiers.md`),
analog column. Nothing here says any cell is ESD-rated or qualified: **the claim
is that, in the drawn Metal3-5 stack, each of the four supplies is one connected
conductor around the closed ring and that the well and substrate taps checked
below reach their rail.** It says nothing about IR drop, electromigration or
current capacity.

## Evidence

- `manifests/evidence/item11/erc-spec.json`: the `klt erc` spec.
- `manifests/evidence/item11/io_ring.json`: `klt erc layout/gf180_io_ring.gds
  <spec> --top io_ring --deck gf180mcu --format json` (klt 0.8.0). Regenerate with
  `manifests/evidence/item11/run.sh`; it passes `klt erc --check`. Its
  `provenance.input.content_hash` equals `manifests/evidence/item2.json`.
- Item 4's `io_ring` LVS report (`manifests/evidence/item4/io_ring.json`), the
  other half of the item.

## What was measured (2026-10-27)

`erc_findings`: none (`erc_finding_count` 0, `erc_status` `clean`).

| Supply | Islands (declared / found) | Unlabelled conductor on Metal3-5 |
|---|---|---|
| `DVDD` | 1 / 1 | 0 |
| `DVSS` | 1 / 1 | 0 |
| `VDD` | 1 / 1 | 0 |
| `VSS` | 1 / 1 | 0 |

No `erc.unconnected_net`, `erc.supply_short` or `erc.missing_tie`. Each supply
declares `roles` `met3`, `met4`, `met5`, so a rail piece reached by no label would
show as `erc.unlabelled_conductor`; there are none. `klt signoff` grades item 11
`met` from this report plus item 4's, and `net_correspondence` pairs `DVDD`,
`VDD` and the merged `DVSS|VSS` entry (below).

## DVSS and VSS

The ring draws no deep-Nwell isolation, so `DVSS` and `VSS` share one p-substrate
(`item4.md` §1). They are declared as two separate supplies here and `klt erc`
reports each as its own single island with no `erc.supply_short`: the ERC model
joins conductors through the declared Metal/via stackup, and the substrate is not
in it, so the short through the substrate is **not visible to this run** in either
direction. `nets[].same_net_as` was not used: it would declare the rails one net,
which is not what the Metal3-5 stack draws and would hide the question rather than
answer it. The same fact appears in item 4 as the declared `hints.short_nets`
`DVSS`/`VSS` join, and `net_correspondence` carries `DVSS` and `VSS` only as the
merged `DVSS|VSS` entry, so "all four supplies paired" holds only in that form.
Whether the domains should be isolated is a spec decision and is not made here.

## Ties and what they rest on

Four ties are declared (`erc_coverage.checked` has 226 entries in all); `dvdd_n_well_taps`, `vdd_thick_n_well_taps` and
`p_substrate_taps` are graded under `checked_by_well_assertion`, i.e. the selection of *which* wells or substrate each
tie covers rests on the spec, not on a marker layer alone:

- `dvdd_n_well_taps`: N-wells with a `DUALGATE` marker (thick-oxide PMOS) except
  eight boxes, N+ taps, to `DVDD`.
- `vdd_n_well_taps`: N-wells without `DUALGATE` (3.3 V PMOS), N+ taps, to `VDD`.
- `vdd_thick_n_well_taps`: the eight thick-oxide wells whose bulk is `VDD` (the
  `XMP_ds*` devices of the `gpio` cells, `layout/gen_ring.py` `todo`), selected
  by the same eight boxes, N+ taps, to `VDD`. `DUALGATE` cannot separate them
  from the `DVDD` wells, so the boxes were taken from the first run's
  `erc.missing_tie` findings and checked against the `M1` net labels in each.
- `p_substrate_taps`: P-substrate (complement of `NWELL`), P+ taps, to `DVSS`.
  Because `DVSS` and `VSS` are one substrate, this tie cannot distinguish a
  `DVSS` tap from a `VSS` tap, and does not claim to.

## Limits

1. **Substrate join:** see above; not detected by this run.
2. **Tap ring metal is outside the stackup roles owned by the supplies** (`met1`,
   `met2` carry the tap rings and device straps); the island count is over Metal3-5
   as the issue specifies, with the taps required to reach the net through
   `connect_to: met1`.
3. **Antenna:** `coverage.scope` is `antenna` with every entry `skipped` (reason
   `missing_antenna_pdk`; `--pdk` has no gf180mcu table). `klt erc` exits `4` and
   `status` is `not_checked` for that reason only; `klt signoff` does not make it
   block this item. No antenna claim is made.
4. **Not a current or voltage claim:** no IR-drop, EM or rail-width verdict.
5. **Item 4 prerequisite:** the LVS half uses `power_connectivity.status`
   `unchecked` (SPICE reference), which is sufficient for the analog column.
