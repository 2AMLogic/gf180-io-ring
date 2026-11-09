# gpio-pex probe, 2026-11-05 (item 7 still NOT met; pin count fixed)

Local single-corner probe (`sim/gpio-pex/run.sh --probe`: deck `vol_5v`, typical, 25 C). No grid
was run and no batch job was submitted.

- klt `0.9.0` (`5dbbad05`), `--pins A,OE,IE,PU,PD,Y,PAD,DVDD,VDD,DVSS,VSS --tie-declared-pins`;
  the report echoes `extraction.tie_declared_pins: true`. Layout `layout/gf180_io_ring.gds`, `--top gpio`.
- Files: `pex-vol_5v.json`, `extracted-gpio.spice`.

## Result

| check | outcome |
|---|---|
| `pin_count_mismatch` | **gone** (`null`); extracted `.SUBCKT gpio A DVDD DVSS IE OE PAD PD PU VDD Y VSS` has 11 pins |
| delta rows | 9 of 9 `error`, now `pin_order_mismatch` (extracted side) |

`pin_order_mismatch`: klt reuses the testbench's positional instantiation line on both legs, and the
extracted pins are alphabetical (`A DVDD DVSS IE OE ...`) while `design/gpio.spice` declares
`A OE IE PU PD Y PAD DVDD VDD DVSS VSS`. klt's own advice is to wrap the schematic DUT in a
`.SUBCKT` that declares the pins in the extracted order. That is a testbench/harness change and
belongs to #20 (follow-up #53); it was out of scope for #40, which only settles the
`DVSS`/`VSS` binding (DR-0004). `model_mismatch` reports `count_only` (finger decomposition),
the expected shape.

Nothing here is ESD-rated or qualified.
