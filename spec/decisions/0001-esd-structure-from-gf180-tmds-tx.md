# DR-0001: ESD structure from `gf180-tmds-tx` — partial adopt

**Status: Accepted.**

## Context

`CLAUDE.md` requires reading the same-PDK sibling's pad and ESD structure and
then adopting it or recording why not. Read: `gf180-tmds-tx` @ `9a55961`,
`spec/pad-ring-esd-survey.md` and `spec/decisions/0011-pad-esd-strategy.md`
(DR-0011). That sibling draws a pad for a high-speed differential driver, with
a diode clamp (`diode_nd2ps_06v0`; symmetric `diode_pd2nw_06v0` toward the
supply) and a pad capacitance budget of ≤ 2 pF. Its HBM 2 kV and CDM 500 V are
its own design targets, not results.

The question (issue #2): does that clamp fit a general-purpose 5 V pad, or is a
second design justified?

## Decision

Adopt some parts, reject others.

| Part of DR-0011 | Verdict | Reason |
|---|---|---|
| Clamp device family: `diode_nd2ps_06v0` to ground, `diode_pd2nw_06v0` to supply | **Adopt** | Both are 6 V rated, so they fit the 5 V path with margin to 5.5 V. The foundry pad cells use the same two devices `[CDL]`. `klt deck info` on this build lists both as recognised device classes, so layout extraction and LVS no longer force a GGNMOS. DR-0011's own verification of that is the sibling's evidence, not re-run here. |
| Ring continuity (`DVDD`/`DVSS` through the pad on Metal3/4/5) and a substrate tap on a real net | **Adopt** | These are requirements any ring segment has. |
| Pad geometry "350 µm pitch / 75 µm depth" | **Reject the numbers, keep the intent** | The LEF reads 75 µm along the ring by 350 µm deep; the sibling transposed them. See `spec/io-ring.md` §Geometry. The finding is filed as [gf180-tmds-tx#234](https://github.com/2AMLogic/gf180-tmds-tx/issues/234). |
| ≤ 2 pF capacitance budget and the 25 × 25 µm pad | **Reject** | Budget belongs to a high-speed lane. A general-purpose pad uses the 60 × 60 µm landing in the foundry LEF; the added-capacitance target here is ≤ 3 pF (`spec/io-ring.md`), compared against the foundry `bi_t` 2.79 pF. |
| GGNMOS pad cell (`gf180_tmds_pad_min.gds`) | **Reject as the pad clamp**; keep GGNMOS as a candidate **rail** clamp | Its stated reason (diode LVS gap) is closed in this klt build. A GGNMOS with ESD implant remains a candidate for the supply-to-supply clamp, which that sibling does not provide. |
| Single-pad clamp only, no rail clamp | **Extend** | A ring needs a `DVDD`↔`DVSS` clamp for pad-to-pad paths; the sibling's pad has none (its own note: "the driver still has no VDD pin"). The device choice for it is deferred; see Consequences. |

A second, from-scratch design is therefore justified only for the part the
sibling does not cover (rail clamps, ring-level paths, general-purpose sizing).
The pad clamp device family is shared.

## Alternatives considered

- **Adopt DR-0011 wholesale.** Rejected: its capacitance budget and pad size are
  for a different pad, and its pitch/depth figures are transposed.
- **Ignore the sibling and use only the foundry pad structure.** Rejected: the
  foundry library is reference and comparison only, and the sibling's work
  includes tool-checked diode extraction evidence worth reusing.

## Consequences

- The ESD design issue starts from the diode pair and sizes it for this pad.
- A later decision record chooses the rail-clamp device (GGNMOS with ESD implant,
  RC-triggered big NFET, or both). klt does not check the `ESD.*` implant rules
  (`spec/io-ring.md` §klt coverage), so a GGNMOS choice carries an unchecked-rule risk.
- Nothing here is an ESD rating; HBM 2 kV stays a design target.
