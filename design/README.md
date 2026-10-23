# design

## Pad clamp diode sizing (issue #11)

Source: `sim/esd_clamp/records/20261023T172346Z/record.md`. Pre-silicon, simulation
only; the record quotes the spec's ESD-evidence limitation and this note adds no
claim beyond it.

- **Stress current (assumption).** 2 kV / 1.5 kohm = 1.33 A, standard human-body-model
  arithmetic; the spec itself only says "HBM 2 kV, design target only".
- **Budget (assumption).** Forward drop at 1.33 A of at most 3.0 V, half of the
  6.0 V class, leaving the rest for the rail clamp (not chosen yet). The 6.0 V is a
  model-header label; the cards' `bv` (11 / 10.5 V) is reverse breakdown and unused.
- **Result.** Smallest swept area meeting the budget in every diode process section
  and −40/25/125 °C: 178 µm² for both `diode_nd2ps_06v0` (binding: `ss`, −40 °C) and
  `diode_pd2nw_06v0` (binding: `ss`, 125 °C). At 2.5 V / 3.5 V budgets the area is
  237 / 133 µm² (nd2ps) and 237 / 178 µm² (pd2nw).
- **Capacitance.** Both diodes at those areas sum to at most 0.42 pF (0 V, `ss`, 125 °C)
  against the 3 pF added-capacitance target. Reverse leakage at 5.5 V sits at the
  simulator's gmin floor (about 5.5 pA; up to ~29 pA hot), so it is a bound, not a value.
- **Caveats.** 1.33 A is far above the currents the model was characterized at
  (extrapolation, no self-heating); the diode sections do not say anything about
  thick-oxide MOS spread (DR-0002). Areas are on a 10^(1/8) grid, not interpolated.
