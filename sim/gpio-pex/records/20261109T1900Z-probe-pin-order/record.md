# gpio-pex probe with pin-order wrapper, 2026-11-09 (item 7 still NOT met)

Issue #53. Local single-corner probe (`sim/gpio-pex/run.sh --probe`: deck `vol_5v`, typical, 25 C,
`provenance.pdk.name: gf180mcuD`), klt 0.9.0, `--tie-declared-pins`. No grid, no batch job.
Earlier records are untouched.

`gen_requests.py` now rewrites each `Xdut` line to the extracted order
(`A DVDD DVSS IE OE PAD PD PU VDD Y VSS`, taken from `../20261105T0900Z-probe/extracted-gpio.spice:21`)
and writes a schematic-leg `gpio.spice` into the request dir only: the design cell renamed
`gpio_design`, wrapped by `.subckt gpio` in that order. `design/` and `sim/gpio-corners/` are unchanged.

## Result

| check | outcome |
|---|---|
| `pin_order_mismatch` | **gone** (0 of 9 rows) |
| schematic leg | `pass` (vol = 0.1633 V at the typical corner) |
| delta rows | 9 of 9 `error`, now `ngspice_fatal` on the **extracted** leg: "Error on line 305", no analysis started |

Line 305 of the extracted netlist (`extracted-gpio.spice`) is the first diode instance,
`D$95 DVSS__t35 PAD__t0 diode_nd2ps_06v0 A=178P P=55.6U`. The extracted netlist references the
diode model `diode_nd2ps_06v0`; the likely cause is that the model is not resolvable from the testbench
include set, but this was not confirmed here. No parasitic delta is available from this run, and
nothing here is ESD-rated or qualified. The next blocker is a separate item; no spec limit is relaxed.
