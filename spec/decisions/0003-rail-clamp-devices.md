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
