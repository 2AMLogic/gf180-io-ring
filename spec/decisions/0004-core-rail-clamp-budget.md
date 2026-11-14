# DR-0004: Peak-voltage budget for the core `VDD`↔`VSS` rail clamp

**Status: Proposed.** Awaiting operator ratification. Agents do not accept their own
spec proposals; until this record is Accepted, T1 item 5 must not be read as `met`.

## Context

`spec/io-ring.md` §ESD network gives the core rail clamp only a device class
("one per core-supply pad, 3.3 V devices") and no voltage the clamp must hold. DR-0003
chose the clamp (RC-triggered `nfet_03v3`) and its Amendment 1 gave the `DVDD` clamp a
6 V peak budget, the `*_06v0` device class, labelled an assumption. The core clamp has
no such budget, so no simulation of it can pass or fail, and `manifests/gf180-io-ring.json`
declares `esd_core_rail_clamp` as a gap holding item 5 at `partial_coverage`.

## Proposal

1. **Budget.** Peak core `VDD` under the stress pulse is at most **4.0 V**.
2. **Source (an assumption, not a spec row).** The `DVDD` budget is 6.0 V against a
   5.0 V nominal, a headroom ratio of 1.2. The same ratio on the 3.3 V nominal is
   3.96 V, rounded to 4.0 V. A `*_03v3` "device class" label (3.3 V) cannot serve as
   the bound as it does for `*_06v0`: it is below the 3.63 V that DR-0002's +10 % supply
   corner already applies in normal operation. The open PDK states no absolute-maximum
   rating for the 3.3 V devices that this record could cite instead.
3. **Stress.** The same pulse as the `DVDD` bench (DR-0003 Amendment 1): 1.33 A
   (2 kV / 1.5 kohm HBM arithmetic, a design target only), 10 ns rise, 100 ns plateau,
   into `VDD` with `DVDD`, `DVSS`, `VSS` at 0 V and the cell unpowered.
4. **Check.** `esd_core_rail` request in `sim/gpio-corners`, `v_peak` bounded by 4.0 V,
   at the 15 PVT corners of DR-0002. The 3.3 V devices skew in `ff`/`ss`/`fs`/`sf`, so
   unlike the `DVDD` bench this one does see process spread on its main devices. The
   bench is unpowered, as in DR-0003, so the 3.63 V supply corner is not a separate point.

## Alternatives considered

- **Stay at the `*_03v3` label, 3.3 V.** Rejected: below normal operation.
- **Use 6.0 V, as `DVDD`.** Rejected: that is the 6 V device class's number; it would
  let a 3.3 V gate see nearly twice its nominal.
- **Relax the budget until the as-captured 400 µm clamp passes.** Rejected (CLAUDE.md:
  agents do not relax a bound to make results pass). The bench is built to the bound
  and the clamp is resized (DR-0003 Amendment 2).

## Consequences

- If the operator picks another budget, `V_CORE_BUDGET` in
  `sim/gpio-corners/gen_requests.py` changes with it and the record is rerun; the
  failing or superseded record stays untouched.
- The 4.0 V figure is not a rating and not a claim about gate-oxide reliability.
  Release after the pulse, absence of latching and normal-operation leakage of the wider
  clamp are not evaluated (the bench ends at 130 ns).
- Item 5's `esd_core_rail_clamp` gap is retired by the cited envelope only on ratification.
