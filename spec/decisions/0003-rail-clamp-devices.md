# DR-0003: Rail-clamp devices for `DVDD`/`DVSS` and the core rails

**Status: Accepted.**

## Context

`spec/io-ring.md` §ESD network leaves the device choice for the `DVDD`↔`DVSS`
rail clamp and the core `VDD`↔`VSS` rail clamp to a decision record. The rows give
the Target as "one per supply-pad cell" (and "3.3 V devices" for the core rail) and
the Fallback as "big `nfet_06v0` RC-triggered or GGNMOS, whichever is checkable".
Issue #14 needs the choice to capture the supply-pad schematics.

Checkability, from `spec/io-ring.md` §klt coverage: the gf180mcu deck has no
ESD-implant rules (`ESD.1`–`ESD.10`, `ESD.pl`; klayout-tools#3792) and no 5/6 V
latch-up tap rules (#3793). A grounded-gate NMOS is only an ESD clamp with the ESD
implant, so its layout could not be rule-checked here at all.

## Decision

1. **`DVDD`↔`DVSS` clamp** (in both the `DVDD` and the `DVSS` pad cell): an
   RC-triggered big `nfet_06v0` (600 µm total, 60 fingers, L = 0.8 µm, no ESD
   implant). Trigger: a `pfet_06v0` with its gate on `DVSS` as a long-channel
   resistor (W/L = 1/20 µm) from `DVDD` to the sense node, a `cap_nmos_06v0`
   (40 × 40 µm) from the sense node to `DVSS`, and a `pfet_06v0`/`nfet_06v0`
   inverter driving the big device's gate. The RC time constant is a design
   intent of the order of 0.5 µs, not a result.
2. **Core `VDD`↔`VSS` clamp** (in the core-supply pad cell): the same topology in
   3.3 V devices (`nfet_03v3` 400 µm / 40 fingers, `pfet_03v3` resistor,
   `cap_nmos_03v3` 30 × 30 µm, `*_03v3` inverter), per the spec's "3.3 V devices".
3. The trigger resistor is a MOS device, not a poly resistor, so every device in
   the netlists stays in the spec's named families (`*_06v0` pad side, `*_03v3`
   core side).
4. The sizes above are capture-time starting points. They are not derived from a
   discharge simulation; sizing against the stress current is the later ESD design
   issue, and the evidence is "rule-clean layout plus simulation", never a rating.

## Alternatives considered

- **GGNMOS** (grounded-gate `nfet_06v0` with ESD implant): rejected, because the
  deck cannot check the ESD implant rules, so "whichever is checkable" excludes it.
- **Diode-only (substrate-diode) path**: rejected for `DVDD`/`DVSS` (it is the spec's
  Fallback for the core rail only) because it gives no `DVDD`↔`DVSS` clamp.
- **Poly resistor in the trigger**: rejected to keep the device families as named.

## Consequences

- The `VDD`/`DVDD` cross-domain coupling (clamp or diode pair) is still open and
  needs its own record; no cell here draws it.
- Whether the RC trigger turns on fast enough and releases without latching is
  unverified until simulated; the pad-side latch-up and guard-ring rules stay a
  klt gap (#3793).

## Amendment 1 (issue #38): `DVDD`↔`DVSS` clamp sizing from the transient record

Appended; decision items 1–4 above are left as written. Evidence:
`sim/gpio-corners/records/20261027T091449Z/` (`esd_rail`, 15 PVT corners, batch
fleet). The earlier record `20261027T064449Z` (600 µm, peak 10.5–13.5 V against the
6 V budget, 15/15 corners failing) is left untouched.

1. **Sizing.** The clamp `nfet_06v0` is 4800 µm total: 48 × (100 µm, 10 fingers,
   L = 0.8 µm) via `m=48` (the fleet does not bin a single instance wider than about
   100 µm). The trigger inverter's `pfet_06v0` is 10 × (10 µm) via `m=10`, up from
   one 10 µm device. `design/dvdd_pad.*` and `design/dvss_pad.*` carry the same change.
2. **Why the trigger changed too.** Width alone does not meet the budget: in host
   single-corner probes at `ss/125 °C` a 600 µm clamp peaks at 13.4 V, 6000 µm with the original inverter still
   at 7.6 V, because the peak falls at the end of the 10 ns rise, before the gate is
   driven. The inverter `pfet` sets how fast the gate follows `DVDD` into a clamp whose
   gate capacitance grows with its width. The RC time constant (resistor, 40 × 40 µm
   capacitor) is unchanged, so the trigger topology and the design intent of decision
   item 1 stand; only the inverter's drive grew. Rejected: retuning the RC alone
   (the clamp is still carrying the pulse at 110 ns, so it is width-limited as well).
3. **Result (simulated clamp behaviour, not a rating).** Peak `DVDD` under the
   1.33 A / 10 ns-rise pulse is at most 5.39 V (`ss/125 °C`, worst of 15) against
   the 6 V budget, which stays an assumption (the `*_06v0` device class), not a spec row.
   `v_end` (DVDD at 110 ns, still inside the 100 ns plateau) is 3.24–5.04 V.
   **Not evaluated:** release after the pulse and absence of latching; the bench ends at
   130 ns and measures no recovery, so the trigger re-check in the issue's criteria is
   limited to turn-on speed (the peak above). The pad-side latch-up rules stay a klt gap
   (#3793).
4. **Request change.** The `esd_rail` bench's DC leak at `DVDD` went from 1 GΩ to 1 MΩ
   (6 µA at 6 V against 1.33 A): at 1 GΩ the `ss/125 °C` and `sf/125 °C` corners
   failed to converge in the trigger capacitor at 0.5 ns, before the pulse. The first
   attempt is kept under the record's `superseded/`.
5. **Cost.** The two supply-pad cells grow their clamp group from about 70 µm to
   about 170 µm of the 350 µm cell depth (`layout/gen_ring.py`, now drawing each `m=`
   copy and a shared substrate-tap bar to meet the 15 µm tap distance). Normal-operation
   leakage of the wider device is not simulated here.
6. **Still open.** The core `VDD`↔`VSS` clamp (3.3 V devices, 400 µm) and the
   `VDD`/`DVDD` coupling are unchanged and unsimulated; the bench still declares them
   as gaps.

## Amendment 2 (issue #48): core `VDD`↔`VSS` clamp sizing against the DR-0004 budget

Appended; decision items 1–4 and Amendment 1 are left as written. Evidence:
`sim/gpio-corners/records/20261028T182957Z/` (`esd_core_rail`, 15 PVT corners, batch
fleet). The budget is DR-0004's 4.0 V, **Proposed** and an assumption, not a spec row.

1. **The captured clamp could not be simulated as drawn.** Item 2's 400 µm as one
   `nf=40` instance does not bin on the fleet (`could not find a valid modelname`, as in
   Amendment 1 item 2). As four 100 µm copies, a host probe (ngspice-42, typical, 25 °C,
   not a record) peaks at 13.7 V under the 1.33 A / 10 ns-rise pulse. No fleet record of
   the 400 µm clamp exists.
2. **Sizing.** The clamp `nfet_03v3` is 5600 µm total: 56 × (100 µm, 10 fingers,
   L = 0.8 µm) via `m=56`. The trigger inverter is `pfet_03v3` 8 × (50 µm, 10 fingers,
   L = 0.28 µm), up from one 5 µm device, and `nfet_03v3` 4 × (70 µm, 14 fingers,
   L = 0.28 µm), up from one 8 µm device. The RC trigger (20 µm-long `pfet` resistor,
   30 × 30 µm `cap_nmos_03v3`) is unchanged, so decision item 2's topology stands.
   `design/core_pad.*`, `design/io_ring.spice` and the layout carry the change.
3. **Why this size.** As in Amendment 1, width alone does not meet the budget: the peak
   falls at the end of the 10 ns rise, before the gate is driven, so the inverter drive
   matters as much. Host probes at `ss`/125 °C (not records) peaked at 4.2 V (4800 µm, inverter
   `pfet` 200 µm and `nfet` 160 µm), 4.4 V (6400 µm, the same inverter) and 3.6 V (6400 µm,
   inverter `pfet` 400 µm and `nfet` 320 µm). The peak is not monotone in clamp width. 5600 µm is
   the largest clamp group the 350 µm cell holds: 64 copies overflow `build_core_pad`'s
   346 µm limit, and the inverter `nfet` was made 14-finger so 56 copies fit.
4. **Result (simulated clamp behaviour, not a rating).** Peak `VDD` under the 1.33 A /
   10 ns-rise pulse is at most 3.88 V (`ss`/125 °C, worst of 15) against the 4.0 V
   budget, 15/15 corners within it. `v_end` (`VDD` at 110 ns, inside the 100 ns plateau)
   is 2.75–3.87 V. The margin to the budget at the binding corner is 0.12 V, so a budget
   below about 3.9 V would send the clamp back for another resize. **Not evaluated:**
   release after the pulse and absence of latching (the bench ends at 130 ns; #45),
   normal-operation leakage of the wider device, and the `ss`/`ff` spread of the
   5/6 V devices (DR-0002); the pad-side latch-up rules stay a klt gap (#3793).
5. **Request.** The `esd_core_rail` bench carries a 1 MΩ leak at `VDD` and
   `.options itl4=1000 gmin=1e-8 reltol=0.01 abstol=1e-9 rshunt=1e12 cshunt=1e-14`. With
   `gmin=1e-9` the fleet aborted `fs`/125 °C ("timestep too small" in the trigger
   moscap); with `gmin=1e-8` it aborted `sf`/125 °C. Both attempts are kept under the
   record's `superseded/`, with the first submit that the shared fleet refused
   (`batch_concurrency_cap`) and the retries that followed. Convergence aids do not
   change a limit.
6. **Cost.** The core-supply pad cell's clamp group grows to fill the cell: the generator
   draws each `m=` copy, as for the `DVDD` clamp, and `build_core_pad` asserts the rows
   stay under 346 µm of the 350 µm depth. Normal-operation leakage is not simulated.
7. **Still open.** The `VDD`/`DVDD` coupling: DR-0005 (Proposed) records it as not
   applicable.
