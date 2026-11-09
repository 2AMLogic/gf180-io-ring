# gpio-pex: extracted leg runs with newer klt; item 7 probe yields numeric deltas, 2026-11-09

Issue #61. Local single-corner probe only (`sim/gpio-pex/run.sh --probe`: `vol_5v`, typical, 25 C); no grid,
no batch job. Earlier records are untouched. Follows `../20261109T2000Z-probe-diode-params/record.md`.

## What changed

The tool gap that record filed (2AMLogic/klayout-tools#5178) was fixed by klayout-tools PR #5184 ("spell diode
instance params area=/pj= for ngspice in leg netlists"). Throwaway env, no host tool touched:
`KLT_CLIENT="uvx --from klayout-tools klt" sim/gpio-pex/run.sh --probe` (klt 0.9.2.dev397+gd8fa2907890e).

The netlist `klt pex` writes still carries `A=178P P=55.6U` (lines 305/307); the leg netlist it simulates
(`extracted-gpio-klt-0.9.2.dev397-ngspice-diode.spice`) now has `area=178p pj=55.6u` on both diodes
(`diode_nd2ps_06v0`, `diode_pd2nw_06v0`). No change to `gen_requests.py`, `design/` or any recorded netlist.

## Result (vol_5v, typical/novdd/25C; `klt` rc 0, 9 rows, 0 errored, pdk gf180mcuD, body_bias biased)

| spec row | schematic V | extracted V | delta % | status |
|---|---|---|---|---|
| vol_d0v0..v2 | 0.1633215 | 0.1657454 | 1.484 | pass |
| vol_d1v0..v2 | 0.1523869 | 0.1547968 | 1.581 | pass |
| vol_d2v0..v2 | 0.1445476 | 0.1469478 | 1.660 | pass |

## Outcome

The extracted-leg `ngspice_fatal` is resolved by a klt version at or after PR #5184. One corner only; this is a
debug probe, not the PVT grid, so it is not item-7 evidence by itself. The fleet runner image is klt 0.9.0, which
still emits `A=`/`P=`: the full batch run needs a runner image with the fix (worker-spec change, not made here).
No spec limit relaxed; nothing here is ESD-rated or qualified. #20 can be re-curated against these findings.
