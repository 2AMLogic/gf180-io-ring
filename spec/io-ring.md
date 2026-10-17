# gf180-io-ring target specification

Status: ratified by the merge of the PR that closes issue #2, subject to the
`pending` rows below. Every number is a **design target**, not a result and not
a rating. Inheritance from the origin is ledgered in
[`porting-plan.md`](porting-plan.md); departures are in
[`decisions/`](decisions/).

Each parameter gives **target / fallback / stretch** with a rationale. "—" means
the column is intentionally empty, with the reason given.

**No cell is ESD-rated or qualified, and none will be called so before
measured silicon.** HBM 2 kV is a design target only (see §ESD evidence).

## Sources

| Tag | Source |
|---|---|
| `[LEF]` | `gf180mcu_fd_io` LEFs, `~/.ciel/gf180mcuD/libs.ref/gf180mcu_fd_io/lef/`, open_pdks `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7` |
| `[LIB]` | `gf180mcu_fd_io` Liberty files, same tree, `lib/` |
| `[CDL]` | `gf180mcu_fd_io.cdl`, same tree, `cdl/` |
| `[MODEL]` | `libs.tech/ngspice/sm141064.ngspice` and `design.ngspice`, same PDK |
| `[ESDRB]` | `libs.tech/klayout/tech/drc/rule_decks/esd.rb`, `guard_ring.rb` |
| `[TMDS]` | `2AMLogic/gf180-tmds-tx` @ `9a55961`, `spec/pad-ring-esd-survey.md`, DR-0010/0011/0013 |
| `[KLT]` | `klt 0.7.1.dev1743+g7ee09483b748`, `klt deck info/rules --deck gf180mcu`, deck hash `sha256:612a48b4…49d1e7` (unreleased dev build) |

The open PDK ships **no I/O datasheet**: `[LIB]` carries timing, capacitance
and power tables only (no VOL/VOH/IOH/IOL/VIL/VIH). Electrical targets below are
therefore chosen here with a stated rationale, then to be compared against
`gf180mcu_fd_io__bi_t` by simulation across the §PVT corners. They are not
transcribed foundry limits.

## Cell set, GPIO function list, ring structure  (`pending: sky130-io-ring#2`)

Mirrors the origin's draft rows (origin `9cf5d41`); not ratified there.

| Parameter | Target | Fallback | Stretch |
|---|---|---|---|
| Cell set | GPIO, I/O-supply pad (`DVDD`), I/O-ground pad (`DVSS`), core-supply pad, corner, fillers | GPIO + one supply pair + corner | analog pass-through pad |
| GPIO functions | bidirectional, output enable, input enable, pull-up/pull-down | output + input only | selectable drive strength, slew control |
| Ring | closed demonstration ring around an empty core, supply rails continuous | one side + corner | — (no stretch: closing the ring is the target) |

Reference: the foundry library has the same families (`bi_t`, `bi_24t`, `in_c`,
`in_s`, `asig_5p0`, `dvdd`, `dvss`, `cor`, `fill*`, `brk*`) `[LEF]`; it has no
dedicated core-supply pad, as `VDD`/`VSS` run as rails through every cell.

## Supplies and devices per path

| Path | Target | Fallback | Stretch |
|---|---|---|---|
| I/O supply `DVDD` | 5 V ±10 % (4.5–5.5 V) | 3.3 V ±10 % (2.97–3.63 V) | selectable 3.3 V / 5 V on one design |
| Core interface | 3.3 V ±10 % `VDD`, level-shifted in the pad | — (a single core voltage is the premise of the interface) | — |
| Pad-side devices (output driver, ESD, input front end, pull devices) | 5/6 V thick-oxide: `nfet_06v0`, `pfet_06v0`, `diode_nd2ps_06v0`, `diode_pd2nw_06v0` | same | `nfet_06v0_nvt` where a native device simplifies the receiver |
| Core-side devices (level-shifter core half, enable/data buffers) | 3.3 V: `nfet_03v3`, `pfet_03v3` | same | — |

Rationale. Operating limit is the 6.0 V device rating `[MODEL]`; 5 V + 10 % is
5.5 V, leaving 0.5 V of headroom, which is why the 5 V path cannot use 3.3 V
devices. `4.5 V / 5.5 V / 2.97 V / 3.63 V` match the foundry characterization
corners (`ss_4v50`, `ff_5v50`, `ss_2v97`, `ff_3v63`) `[LIB]`.

**Departure from the foundry cell.** Each foundry Liberty file characterizes a
single supply with `VDD` equal to `DVDD` (5 V libs: both 5.0; 3.3 V libs: 3.3)
`[LIB]`, and the foundry cell is built from `nfet_06v0`/`pfet_06v0` throughout
`[CDL]`. This spec instead holds `VDD` at 3.3 V while `DVDD` is 5 V, so the
level shifter crosses a 3.3 → 5 V boundary in normal operation. That crossing is
not covered by any foundry characterization and is verified here only by
simulation (see §PVT corners for the supply matrix).

## GPIO electrical targets

Chosen as conventional 5 V CMOS GPIO levels; see the datasheet note above.
Loads are lumped capacitances, not package models.

| Parameter | Target | Fallback | Stretch | Rationale |
|---|---|---|---|---|
| Output drive, `DVDD` = 5 V | VOL ≤ 0.4 V at 4 mA sink; VOH ≥ `DVDD` − 0.5 V at 4 mA source | same levels at 2 mA | selectable 4 / 8 mA | 4 mA is the lowest drive step a general MCU pad is useful at; the foundry `bi_t` exposes two drive-select pins (`PDRV0/1`) `[LEF]` |
| Output drive, `DVDD` = 3.3 V | VOL ≤ 0.4 V at 2 mA; VOH ≥ `DVDD` − 0.4 V at 2 mA | same levels at 1 mA | selectable 2 / 4 mA | lower overdrive at 3.3 V halves the achievable current at the same device size |
| Rise/fall (10–90 %) | ≤ 5 ns into 15 pF at 5 V; ≤ 8 ns into 15 pF at 3.3 V | ≤ 10 ns into 15 pF | slew control with a slow setting ≥ 10 ns | foundry `bi_t` characterizes up to 30 pF at `PAD` and has an `SL` slew pin `[LIB]` `[LEF]`; 15 pF is half that |
| Input thresholds | VIL ≤ 0.3·`DVDD`, VIH ≥ 0.7·`DVDD`, at both 5 V and 3.3 V | same | — | standard CMOS levels; scale with `DVDD` |
| Input hysteresis | ≥ 0.4 V at 5 V; ≥ 0.25 V at 3.3 V | none required (thresholds only) | `CS`-style selectable CMOS / Schmitt | the foundry `bi_t` has a `CS` select, with separate `in_c`/`in_s` cells `[LEF]` |
| Pull-up / pull-down | enabled by control, equivalent 25–100 kΩ at nominal | pull-down only | strength select | weak pulls hold a floating pad without loading a driver |
| Pad capacitance | ≤ 3 pF added by the pad, input mode | ≤ 5 pF | ≤ 2 pF | the foundry `bi_t` presents 2.79 pF at `PAD` `[LIB]`; this is a comparison anchor, not a requirement from a consumer |

## Geometry

| Parameter | Target | Fallback | Stretch | Source |
|---|---|---|---|---|
| Pad pitch (along the ring) | 75 µm | 75 µm (fillers of 1 / 5 / 10 µm sum to a multiple of the pitch) | tighter custom pitch, only by decision record | `[LEF]` every pad cell is `SIZE 75 BY 350`: 75 µm wide along the ring; fillers are `1`, `5`, `10` µm wide by 350 µm tall |
| Cell depth (pad edge to core) | 350 µm | 350 µm | — (depth fixes compatibility with foundry fillers and corner) | `[LEF]` |
| Corner cell | 355 × 355 µm | same | — | `[LEF]` `gf180mcu_fd_io__cor` |
| Bond-pad landing | Metal5 landing 60 × 60 µm at (7.5, 2) to (67.5, 62) inside the 75 µm cell, i.e. 7.5 µm margin each side, pad end of the cell | smaller landing, but not below the pad-enclosure rule | — | `[LEF]` bi_t `PAD` pin, open_pdks `f6eeac7`. Metal5 must overlap the pad opening by ≥ 2.0 µm (`pad.enclosing.metal5.1`) `[KLT]` |
| Pad-opening rule coverage | pad-opening size, pad spacing: foundry DRM only | — | — | the open deck's only pad-layer rules are enclosure and grid `[KLT]`; the rest is not publicly checkable |
| `DVDD`/`DVSS` rails | Metal3, Metal4 and Metal5 stubs 1 µm wide at both cell edges (x = 0–1 and 74–75 µm), 7 or 15 µm tall, `DVDD` spanning y = 118–341 µm and `DVSS` y = 70–348.4 µm | same | — | `[LEF]` bi_t |
| Core `VDD`/`VSS` rails | Metal3/4/5, 1 µm × 7 µm stubs at both edges: `VSS` at y = 246–253 and 318–325 µm, `VDD` at y = 254–261 and 310–317 µm | same | — | `[LEF]` bi_t |
| Rail continuity | every abutting cell meets its neighbour's `DVDD`, `DVSS`, `VDD`, `VSS` stubs on all three layers | one side continuous plus corner | — | `[TMDS]` DR-0011 requires continuity; checked by ring ERC |

Notes for readers of `[TMDS]`:

- That survey (§1, §8) and DR-0011 state the standard pad as "75 µm deep by
  350 µm wide" and adopt "350 µm pitch / 75 µm depth". The LEF says
  `SIZE 75.000 BY 350.000` with fillers `1.0`–`10.0` µm wide by 350 µm tall and
  the `PAD` pin at the low-y end, so the **pitch along the ring is 75 µm and the
  depth is 350 µm**: the two figures are transposed there. This spec uses the
  LEF reading. Filed as [gf180-tmds-tx#234](https://github.com/2AMLogic/gf180-tmds-tx/issues/234); not decided here.
- The survey quotes a 25 × 25 µm `PAD` landing at (25, 20) from open_pdks
  `c6d73a3`. The newer revision `f6eeac7` resolved by `klt pdk find`
  (`~/.ciel/gf180mcuD`) shows 60 × 60 µm at (7.5, 2). That is a PDK revision
  difference, which is why the PDK pin (issue #3) matters for geometry.

## ESD network

Devices (all 6 V rated, hence the thick-oxide path): `diode_nd2ps_06v0`
(N+/P-substrate) and `diode_pd2nw_06v0` (P+/Nwell) as pad clamps, which is also
what the foundry pad cells use `[CDL]` (8 and 53 instances respectively); a
grounded-gate NMOS (`nfet_06v0` with ESD implant, gate length ≥ 0.8 µm per
`ESD.pl`) `[ESDRB]` as the candidate rail clamp. DR-0001 records the
adopt/reject against `gf180-tmds-tx`.

| Parameter | Target | Fallback | Stretch |
|---|---|---|---|
| Clamp on every pad | pad→`DVDD` (`diode_pd2nw_06v0`) and pad→`DVSS` (`diode_nd2ps_06v0`) | pad→`DVSS` diode only, with the rail clamp alone covering `DVDD` strikes | add a series resistor / secondary clamp stage to the input gate |
| Rail clamp `DVDD`↔`DVSS` | one per supply-pad cell, device choice recorded in a later decision record | big `nfet_06v0` RC-triggered or GGNMOS, whichever is checkable | both, compared in simulation |
| Core rail clamp `VDD`↔`VSS` | one per core-supply pad, 3.3 V devices | shared substrate-diode path only | — |
| HBM | 2 kV, **design target only** | 1 kV | — |
| CDM | not targeted in this spec | — | design target to be set after a first discharge simulation |

Discharge paths required between every pad-type pair (the *claim* here is that
a path exists in the schematic and layout; sizing is by the later ESD design
issue and judged only by simulation plus rule-clean layout):

| From → to | Intended path |
|---|---|
| GPIO → `DVSS` | pad `diode_nd2ps_06v0` forward to ground; reverse via rail clamp |
| GPIO → `DVDD` | pad `diode_pd2nw_06v0` to the supply rail |
| `DVDD` ↔ `DVSS` | rail clamp |
| GPIO ↔ GPIO | pad diode to a rail, rail clamp, second pad diode (no direct path is drawn) |
| core `VDD` ↔ `VSS` | core rail clamp |
| core rails ↔ I/O rails | shared p-substrate between `DVSS` and `VSS`; `VDD`/`DVDD` coupled by a clamp or diode pair, decision record to follow |
| GPIO → core `VDD`/`VSS` | through the I/O rails and the cross-domain coupling above; never a direct drawn path |

### ESD evidence

Pre-silicon evidence is limited to (1) the clamp network turning on and carrying
the intended current in simulation with the PDK's models across PVT, and (2) a
layout that satisfies the ESD and latch-up rules the tools can check. It proves
nothing about HBM/CDM robustness. Words such as "rated" and "qualified" are
used in this spec only to forbid them. (Rule inherited in draft form from the
origin, `pending: sky130-io-ring#2`.)

## Latch-up and guard rings

| Parameter | Target | Fallback | Stretch |
|---|---|---|---|
| Guard rings | every pad-side NMOS driver and clamp enclosed by a non-broken P+ substrate tap ring tied to `DVSS`; every PMOS by an N+ well-tap ring tied to `DVDD` | rings on the driver devices only | double rings on the output stage |
| Tap spacing, 3.3 V logic | ≤ 20 µm to a tap (deck rule `comp.tap_distance.*.lv.1`) | same | — |
| Tap spacing, 5/6 V devices | stricter-of the foundry DRM and 20 µm until the DRM value is obtained; **not** taken from the open PDK, which does not publish it | 20 µm | — |
| Guard-ring marker layers | `latchup_mk` / `GUARD_RING_MK` rules `GR.1`–`GR.11` where used | not used | used |

Rationale. The foundry's own GR rules (12 µm minimum metal width, 16 µm minimum
PCOMP width, 10 µm space to the prime die) `[ESDRB]` are written for the
marker-based guard ring, not for in-cell rings, so they are not adopted as ring
dimensions; the construction is a design choice recorded when the driver is
drawn.

## PVT corners

Fixed and named (DR-0002):

| Axis | Values |
|---|---|
| Process, MOS | `typical`, `ff`, `ss`, `fs`, `sf` (top-level `.lib` sections at lines 105, 137, 169, 201, 233 of `libs.tech/ngspice/sm141064.ngspice`; corner names also confirmed by `klt pdk corners --pdk gf180mcuD`) |
| Process, passives | `res_typical`, `res_ff`, `res_ss`; `diode_typical`, `diode_ff`, `diode_ss`; `moscap_*`; `mimcap_*`; `bjt_*` where used |
| Temperature | −40 °C, 25 °C, 125 °C |
| `DVDD` | nominal −10 % / nominal / nominal +10 %: 4.5 / 5.0 / 5.5 V in 5 V mode; 2.97 / 3.3 / 3.63 V in 3.3 V mode |
| Core `VDD` | 2.97 / 3.3 / 3.63 V, crossed with `DVDD` for any result involving the level shifter |

**Known limitation, measured.** In the model file, every top-level process
section (`typical`, `ff`, `ss`, `fs`, `sf`) loads the *typical* sections
`nfet_06v0_t`, `pfet_06v0_t`, `nfet_06v0_nvt_t` for the 5/6 V devices; only the
3.3 V FETs have skewed sections. So a process corner moves the core devices
but **not the 5 V devices that carry the ring's I/O path**. `klt pdk corners`
also reports `fs` and `sf` as incomplete (MOS skewed, other families left at
typical). The recorded results must say so, and thick-oxide process spread is
covered only by supply, temperature and an explicit margin, not by a corner.
Reference points: the foundry Liberty set spans `ff_n40C_5v50`, `ff_125C_5v50`,
`ss_125C_4v50`, `tt_025C_5v00` `[LIB]`.

Temperature is 25 °C, not the 27 °C that `[TMDS]` DR-0013 uses, because the
foundry libraries are characterized at 25 °C `[LIB]` and this repo compares
against them.

## klt coverage (answer to open question a)

Source: `klt deck rules --deck gf180mcu` (94 rules) and `klt deck info`
(device classes `nfet, pfet, bjt, cap_mim_2f0_m4m5_noshield, resistor,
diode_nd2ps_06v0, diode_pd2nw_06v0`), `klt` `0.7.1.dev1743+g7ee09483b748`. The
official rule decks are `[ESDRB]`.

| Rule area | Checked by klt's gf180mcu deck? | Gap |
|---|---|---|
| 5/6 V COMP width and spacing (`comp.width.mv.1` 0.3 µm, `comp.space.mv.1` 0.36 µm) | yes | — |
| Dualgate layer rules (enclosure, spacing, overlap), 5/6 V poly and implant rules | no (only `dualgate.ongrid.1`) | **gap** |
| ESD implant `ESD.1`–`ESD.10`, `ESD.pl` | no | **gap** |
| Guard-ring marker rules `GR.1`–`GR.11` | no | **gap** |
| Latch-up: tap distance for 3.3 V logic (`comp.tap_distance.nwell.lv.1`, `comp.tap_distance.psub.lv.1`, 20 µm) | yes | — |
| Latch-up: tap distance for 5/6 V devices, LVPWELL rules, `latchup_mk` | no | **gap** |
| Pad opening: metal5 enclosure of pad (`pad.enclosing.metal5.1`, 2.0 µm), grid | yes | pad size / spacing: not public |
| Diode device recognition (`diode_nd2ps_06v0`, `diode_pd2nw_06v0`) in extraction/LVS | yes | — |
| `DVDD`/`DVSS`/core rail continuity through abutting cells | rule decks: no; `klt` has generic `ring-check`, `tap-distance`, `components` commands | to be confirmed with ring ERC in the ring-assembly issue |

Generic tool gaps to file at `2AMLogic/klayout-tools` (each described as a
tool gap, without design detail):

1. DRC deck lacks Dualgate/5-6 V rule coverage beyond COMP width and spacing: [klayout-tools#3791](https://github.com/2AMLogic/klayout-tools/issues/3791).
2. DRC deck lacks the ESD implant rule set (`ESD.*`) and guard-ring marker rules (`GR.*`): [#3792](https://github.com/2AMLogic/klayout-tools/issues/3792).
3. Latch-up tap distance covers only 3.3 V devices: [#3793](https://github.com/2AMLogic/klayout-tools/issues/3793).
4. `klt pdk corners` shows `fs`/`sf` incomplete for gf180mcu, and the PDK's 5/6 V FET
   models have no process skew sections; there is no way to see this from `klt sim`
   output unless the user checks, so a corner report should flag which device flavors
   do not move: [#3794](https://github.com/2AMLogic/klayout-tools/issues/3794).

These were checked by running `klt deck`/`klt pdk` queries (single-unit, no
layout, no simulation) and were filed on 2026-10-17 as linked above. Not run: a
`klt drc` pass on a drawn layout, since no layout exists yet; the coverage above is
from the deck's rule list, not from a layout run.

## Open questions

- **(a) klt deck coverage**: answered in §klt coverage.
- **(b) Origin harness on gf180mcu**: `pending: sky130-io-ring#2`. The origin has
  no harness (`sim/` is a placeholder at `9cf5d41`), so there is nothing to run.
  When one lands, record whether it runs unchanged or a divergence by decision
  record. Known candidate divergences: the PDK model section names, and the
  typical-only 5/6 V models above.
- **(c) `gf180-tmds-tx` clamp for a general-purpose pad**: answered in DR-0001.
- Rail-clamp device choice and the `VDD`/`DVDD` cross-domain coupling: deferred to
  the ESD design issue; each gets a decision record.
- 5/6 V latch-up tap distance and guard-ring dimensions: DRM values not in the open
  PDK; obtain before the layout issue relies on them.
