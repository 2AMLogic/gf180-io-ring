# DR-0002: PVT corner set and the thick-oxide corner limitation

**Status: Accepted.**

## Context

Every recorded analog result needs PVT corners (`CLAUDE.md`). Issue #2 asks for
the set to be fixed and named against this PDK's model library. The sibling
`gf180-tmds-tx` DR-0013 ratified 3 temperatures × ±10 % supply × 5 MOS corners,
using 27 °C.

Reading `libs.tech/ngspice/sm141064.ngspice` (open_pdks `f6eeac7`, variant
`gf180mcuD`): the top-level process sections are `typical`, `ff`, `ss`, `fs`,
`sf`. Each loads `nfet_06v0_t`, `pfet_06v0_t` and `nfet_06v0_nvt_t` for the 5/6 V
devices; only the 3.3 V FETs (`nfet_03v3_{t,f,s,fs,sf}`) have skewed sections.
`klt pdk corners --pdk gf180mcuD` reports `fs` and `sf` as incomplete.

## Decision

1. The matrix in `spec/io-ring.md` §PVT corners is the ratified set:
   `typical, ff, ss, fs, sf` × −40 / 25 / 125 °C × `DVDD` and core `VDD` at
   nominal ±10 %, with `res_*`, `diode_*`, `moscap_*`, `mimcap_*` skews added for
   results that depend on those devices.
2. Temperature nominal is **25 °C**, departing from the sibling's 27 °C, so results
   are comparable with the foundry Liberty files, characterized at 25 °C.
3. Because the 5/6 V models do not skew, a result at `ff` or `ss` is **not**
   evidence about thick-oxide process spread. Every recorded result for the 5 V
   path states this. Thick-oxide spread is covered by the supply and temperature
   axes and an explicit margin until a skewed model or a documented parameter
   skew exists. The agent does not invent skew parameters.

## Alternatives considered

- Copy the sibling's 27 °C: rejected (comparability with foundry libraries).
- Add invented `±x %` parameter skews to the 6 V models: rejected; no evidence for
  the values, and the spec must not be made to pass by assumption.

## Consequences

- The gap is a klt friction item (`spec/io-ring.md` §klt coverage, gap 4).
- Results from other PDK variants (A–C) are out of scope; the PDK pin is issue #3.
