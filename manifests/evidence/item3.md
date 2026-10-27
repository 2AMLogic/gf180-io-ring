# T1 item 3: DRC clean (claim)

Evidence for item 3 of the T1 checklist (`manifests/design-evidence-tiers.md`).
Nothing here says any cell is ESD-rated or qualified: **clean means clean
against klt's open `gf180mcu` deck only**, which does not model every rule (see
the coverage quoted below).

## Reports

One `klt drc --format json` envelope per top cell of `layout/gf180_io_ring.gds`
(`input.content_hash` `sha256:e6766e5da5ea2e9c58549c3fe2137bfda8cd7be1b729bc877ce352acba6c83ef`, equal to
`manifests/evidence/item2.json`). Each was produced with
`uvx --from "klayout-tools==0.8.0" klt drc layout/gf180_io_ring.gds --deck gf180mcu --top <cell> --format json`
(no `--waivers`, `--rules` subset or `--allow-deck-errors`) and passes
`klt drc --check <report>`. Deck `gf180mcu`
`sha256:0eb6df1bafc5106ec50bd58479dbd7cda36bb685f1ef18cd3a2244a6e7e48666`; `provenance.klt_version` `0.8.0`;
KLayout `0.30.12` (the deck run; the stream itself is generated
under KLayout 0.28.16, see `layout/README.md`).

| Cell | Envelope | status | violations |
|---|---|---|---|
| `io_ring` | `manifests/evidence/item3/io_ring.json` | `clean` | 0 |
| `gpio` | `manifests/evidence/item3/gpio.json` | `clean` | 0 |
| `dvdd_pad` | `manifests/evidence/item3/dvdd_pad.json` | `clean` | 0 |
| `dvss_pad` | `manifests/evidence/item3/dvss_pad.json` | `clean` | 0 |
| `core_pad` | `manifests/evidence/item3/core_pad.json` | `clean` | 0 |
| `corner` | `manifests/evidence/item3/corner.json` | `clean` | 0 |
| `filler` | `manifests/evidence/item3/filler.json` | `clean` | 0 |
| `filler_5` | `manifests/evidence/item3/filler_5.json` | `clean` | 0 |
| `filler_1` | `manifests/evidence/item3/filler_1.json` | `clean` | 0 |

The manifest cites the `io_ring` envelope; the other eight are per-cell
evidence for the same stream. Regenerate all with `layout/regen.sh` and the
command above, never by editing an envelope.

## Coverage, quoted from `manifests/evidence/item3/io_ring.json`

`coverage.layers_in_stream_without_rules`:

```json
["0/0", "34/10", "36/10", "42/10", "46/10", "81/10"]
```

`coverage.rules_skipped`:

```json
["bjt.separation.comp.1", "cap_mk.ongrid.1", "comp.separation.guard_ring_mk.1", "diode_mk.ongrid.1", "dnwell.ongrid.1", "drc_bjt.ongrid.1", "efuse_mk.ongrid.1", "fusetop.ongrid.1", "metal1.separation.guard_ring_mk.1", "metal2.separation.guard_ring_mk.1", "metal3.separation.guard_ring_mk.1", "metal4.separation.guard_ring_mk.1", "metal5.separation.guard_ring_mk.1", "metaltop.ongrid.1", "metaltop.separation.guard_ring_mk.1", "metaltop.space.1", "metaltop.width.1", "mim.enclosing.fusetop.1", "mim.enclosing.via4.1", "mim.space.1", "mim_l_mk.ongrid.1", "nwell.separation.guard_ring_mk.1", "plfuse.ongrid.1", "poly2.enclosing.sab.1", "poly2.separation.guard_ring_mk.1", "res_mk.ongrid.1", "resistor.ongrid.1", "sab.ongrid.1", "sab.separation.contact.1", "sab.space.1", "sab.width.1"]
```

`coverage.deck_scope`:

```json
["10.4.2 MIM Option B", "10.7 DRC_BJT Mark Layer", "7.12 Contact", "7.13 Metaln", "7.14 Vian", "7.15 MetalTop", "7.4 Nwell", "7.5 Comp", "7.7 Poly2", "7.8 Nplus", "7.9 Pplus", "9.1 Bond Pad", "ESD", "GR", "OFFGRID", "SB"]
```

The layers without rules are the stream's boundary layer (`0/0`) and the
Metal1-5 label layers (`34/10`, `36/10`, `42/10`, `46/10`, `81/10`), which carry
only net names.

## Gaps against `spec/io-ring.md` §klt coverage

The spec table was read at klt `0.7.1.dev1743`. At klt `0.8.0` the deck's
`coverage.rules_checked` includes `dualgate.ongrid.1`, `dualgate.space.1`,
`dualgate.width.1` and `esd.area.1`, `esd.holes_area.1`, `esd.overlap.comp.1`,
`esd.separation.nplus.1`, `esd.separation.pplus.1`, `esd.space.1`,
`esd.width.1`, so the spec's "Dualgate: only ongrid" and "ESD implant: no" rows
are out of date for those rules. The ratified spec is not edited here; a
decision record is the route if it should change. Still unchecked
(`coverage.unmodeled_rules` and `rules_skipped`):

| Spec gap | State at klt 0.8.0 |
|---|---|
| Guard-ring marker rules `GR.1`-`GR.11` | not checked: every `*.separation.guard_ring_mk.1` is in `rules_skipped`; `GR.1`, `GR.3`, `GR.4`, `GR.6`, `GR.11` are in `unmodeled_rules` |
| ESD implant remainder | `ESD.3a`, `ESD.3b`, `ESD.4a`, `ESD.6`, `ESD.7`, `ESD.9`, `ESD.10`, `ESD.pl` are in `unmodeled_rules` |
| Other Dualgate / 5-6 V rules | `DV.1`, `DV.3`, `DV.6`-`DV.9` and the `*_MV` columns are in `unmodeled_rules` |
| 5/6 V latch-up taps | `comp.tap_distance.*.mv.1` is checked; LVPWELL rules and `latchup_mk` are not (`LPW.*_MV` in `unmodeled_rules`); the spec's 20 um stand-in applies |
| Pad size and spacing | not public; only `pad.enclosing.metal5.1` is checked |
| SAB, MetalTop | `sab.*`, `metaltop.*` are in `rules_skipped`. `via1.*`, `via2.*` and their Metal enclosures are checked now that the stream draws Via1/Via2 |

The Metal2/3/4 wiring is drawn and is inside this clean result (Via1/Via2/Via3
and Metal1-4 spacing, width and enclosure rules are checked). Metal2 gaps under
0.28 um left by the router were closed in the generator (`Wiring.close_gaps`),
not waived. MetalTop and SAB are not checked; connectivity is evidenced by
`layout/check_connectivity.py` and `klt components`, not by the deck.

## Negative control

`klt drc --negative-control` requires `--engine klayout` and a PDK-native deck,
which this canary does not run (curated engine only; filed as a tool gap, see
the PR). Equivalent known-bad layout: the previous committed stream
(`origin/main` at `3152493`, content hash
`sha256:24e8f0ec7325264d699adcbf369f5677b7b904b87ad664a593bbca98e53f9c1e`),
same deck and options, `--top io_ring`: `status: violations`,
`violation_count: 2760`, `dualgate.space.1` 8, `metal1.space.1` 64, `nplus.enclosing.comp.1` 64, `nplus.enclosing.poly2.1` 1856, `pplus.enclosing.comp.1` 32, `pplus.enclosing.comp.far.1` 32, `pplus.enclosing.poly2.1` 704. So the deck does fail on
this stream's layers; the fix was in the generator geometry (implant extension
beyond comp and gate region raised to 0.4 um, diode tap rings moved off the
diode, one Dualgate marker over stacked rows), with no waiver.
