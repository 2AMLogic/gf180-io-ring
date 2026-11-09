# gpio-pex: cause of the extracted-leg `ngspice_fatal` confirmed, 2026-11-09 (item 7 still NOT met)

Issue #61. Local single-corner work only (one `ngspice -b` debug probe, plus `sim/gpio-pex/run.sh --probe`
with an alternate client); no grid, no batch job. Earlier records are untouched.

## Cause

The "diode model not resolvable" hypothesis in `../20261109T1900Z-probe-pin-order/record.md` is **refuted**.
The extracted netlist writes both diodes as `D… <model> A=178P P=55.6U` (lines 305 and 307). ngspice's `D`
element rejects the `A=`/`P=` instance parameters. PDK `gf180mcuD` @ open_pdks `c6d73a35`,
`.lib sm141064.ngspice typical` + `diode_typical`, ngspice-46:

| card | outcome |
|---|---|
| `D1 0 a diode_nd2ps_06v0 A=178P P=55.6U` | `unknown parameter (a)`, "Simulation interrupted due to error!" |
| `D2 0 a diode_nd2ps_06v0 area=178p pj=55.6u` | model resolves, `.op` runs (benign `IKR too small` warning) |

The schematic leg uses the same model with `area=`/`pj=` (`design/gpio.spice:90-91`), which is why it passes.

## Newer klt

`run.sh --probe` with `KLT_CLIENT="uvx --from klayout-tools klt"` (0.9.2.dev385+gfafa69b5f3b6, throwaway env):
still `ngspice_fatal` on the extracted leg of 9 of 9 rows, still `A=`/`P=` on lines 305/307
(`extracted-gpio-klt-0.9.2.dev.spice`). `klt pex --help` shows no switch or netlist post-processing hook;
`--measure-command` replaces the measurement, and rewriting the netlist `klt pex` consumes would change what is
measured, so no workaround is added in `gen_requests.py`.

## Outcome

Blocked on the tool. Gap filed generically: 2AMLogic/klayout-tools#5178. No parasitic delta is available, no spec
limit is relaxed, and nothing here is ESD-rated or qualified. #20 stays blocked until klt emits `area=`/`pj=`.
