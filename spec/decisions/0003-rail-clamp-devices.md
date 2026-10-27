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
