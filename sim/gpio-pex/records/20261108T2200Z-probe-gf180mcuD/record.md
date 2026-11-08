# gpio-pex probe under the pinned variant, 2026-11-08 (item 7 still NOT met)

Issue #58. The 2026-10-27 probe (`../20261027T1000Z-probe/`, left untouched) passed `--pdk-root`
but no `--pdk`, and klt resolved `gf180mcuA` from the `<rev>` directory that holds A..D side by
side (`provenance.pdk.name: gf180mcuA`). `run.sh` now passes `--pdk "$VARIANT"` (`gf180mcuD`, from
`sim/pdk.json` via `check_env.sh`) and fails the run if `provenance.pdk.name` differs.

- Command: `sim/gpio-pex/run.sh --probe` (vol_5v, typical, 25 C, local, one corner), klt 0.8.0.
- `provenance.pdk`: `name: gf180mcuD`, `source: --pdk-root flag`, `version: open_pdks c6d73a35...`.
  klt also reports `compatibility.status: mismatch` (its expected package pin is `f6eeac7d...`, the
  repo pin is `c6d73a35...`); not acted on here.
- Same result as the A-variant probe: extracted `.SUBCKT gpio` has 10 pins (`DVSS|VSS` joined by
  the shared substrate), schematic declares 11, so 9 of 9 delta rows error `pin_count_mismatch`;
  `body_bias: biased`. The VSS-DVSS tie is unchanged, so DR-0004 is unaffected.
- No parasitic figure is available from this run. Any pex figure cited on #20 / #53 must come from
  a record whose `provenance.pdk.name` is `gf180mcuD`; the 20261027 record's is `gf180mcuA`.
