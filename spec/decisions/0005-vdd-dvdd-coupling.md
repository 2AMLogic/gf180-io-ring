# DR-0005: No dedicated `VDD`/`DVDD` cross-domain coupling

**Status: Proposed.** Awaiting operator ratification. Agents do not accept their own
spec proposals; until this record is Accepted, T1 item 5 must not be read as `met`.

## Context

`spec/io-ring.md` §ESD network lists, for "core rails ↔ I/O rails": "shared p-substrate
between `DVSS` and `VSS`; `VDD`/`DVDD` coupled by a clamp or diode pair, decision
record to follow". DR-0003 left the record open. No cell draws such a coupling, and
`manifests/gf180-io-ring.json` declares `esd_vdd_dvdd_coupling` as a gap.

## Proposal

**None drawn: the coupling is "not applicable" in this ring.** The spec's "clamp or
diode pair" is read as the candidates, and this record picks neither.

Reason. The ring merges the two grounds: `DVSS` and `VSS` are one p-substrate (no
deep-Nwell isolation is drawn; LVS declares the `DVSS|VSS` short, `layout/README.md`).
Each supply then already has a clamp to that common node, so a `VDD`↔`DVDD` stress has
a path through two elements in series, with no `VDD`–`DVDD` device between them:

- `DVDD` high against `VDD`: `DVDD` clamp (DR-0003 Amendment 1) to `DVSS`≡`VSS`, then
  the drain-to-substrate diode of the core clamp's `nfet_03v3` forward into `VDD`.
- `VDD` high against `DVDD`: core clamp (DR-0003 Amendment 2) to `VSS`≡`DVSS`, then
  the drain-to-substrate diode of the `DVDD` clamp's `nfet_06v0` forward into `DVDD`.

A back-to-back diode pair between `VDD` and `DVDD` would add a path that bypasses the
clamps and would be a diode between a 3.3 V and a 5 V rail that conducts whenever the
supplies are sequenced the wrong way round. A third clamp would add layout and area for
a path the two existing clamps and the common substrate already provide.

## Alternatives considered

- **Back-to-back diode pair**: rejected, as above (sequencing hazard; bypasses the clamps).
- **A `VDD`↔`DVDD` clamp**: rejected, as above (a third clamp for a path that exists).
- **Draw one and simulate it**: rejected: it needs new layout for the cell that carries
  it and gains a path the substrate already gives.

## Consequences

- `esd_vdd_dvdd_coupling` is removed from the manifest's declared gaps, on ratification.
  `spec/io-ring.md` keeps its sentence until the operator edits it; this record does not
  edit the ratified spec.
- The cross path is argued from the netlist and the merged substrate. It is **not
  simulated** here: no bench forces `VDD` against `DVDD` through both clamps, so the
  statement is a design argument, not a measured result. A bench for it would be a new
  request beside `esd_rail` and `esd_core_rail`.
- It depends on the `DVSS`/`VSS` merge. If #40 decides to isolate the two grounds, this
  record must be revisited.
- No rating or qualification is claimed.
