# DR-0004: `DVSS` and `VSS` are one extracted net; pex ties the declared pins

**Status: Accepted** (operator ruling q91, 2026-10-29, option c).

## Context

`spec/io-ring.md` §ESD network ratifies a shared p-substrate between `DVSS` and
`VSS`. Extraction therefore returns one net for both, so the extracted `gpio`
subckt had 10 pins against the 11 declared in `design/gpio.spice`, and every
`klt pex` delta row errored `pin_count_mismatch` (issue #40, blocking #20).

## Decision

1. `DVSS` and `VSS` are one extracted net through the shared p-substrate.
2. `design/gpio.spice` stays the 11-pin item-1 netlist. No derived netlist.
3. `sim/gpio-pex/run.sh` binds the pins with klt's `--tie-declared-pins`
   (klayout-tools 0.9.0). The flag is boolean; it ties every declared pin that
   extraction joins back to all of its declared names. It needs `--pins`.

## Alternatives considered

- **(a) Isolate `DVSS` and `VSS` in layout** (deep-Nwell / separate substrate):
  rejected. It reverses the ratified spec row and reopens items 2, 3, 4 and 9.
- **(b) A derived merged-pin pex netlist:** rejected. It adds a second netlist to
  keep in step, and the tool now ties the pins itself.

## Consequences

- Pex is blind to a `DVSS`-`VSS` defect, because the tie makes the two names one
  net by construction. That is not a pex check and this record does not claim it
  is; the substrate join itself is item-4 evidence.
- No spec row is relaxed. This record makes no ESD claim.
