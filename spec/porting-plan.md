# Porting plan: sky130-io-ring → gf180-io-ring

Status: recorded for issue #2. This is the ledger of what this repo inherits
from its origin, what it re-derives for gf180mcu, and which sibling commits
were read. `spec/io-ring.md` holds the resulting targets.

The origin, `2AMLogic/sky130-io-ring`, opened at the same time as this repo.
**As of its `main` @ `9cf5d41` (read 2026-10-17) it has ratified nothing:**
`spec/` holds only the placeholder `README.md`, `sim/` has no harness, and its
own spec issue [sky130-io-ring#2](https://github.com/2AMLogic/sky130-io-ring/issues/2)
is still open. Per the porting rule, an unratified origin item is **not
decided here**: its row stays `pending: sky130-io-ring#2` and is updated by a
decision record when the origin ratifies. Nothing below invents origin content.

## Sibling commits read

| Repo | Commit read | What was read |
|---|---|---|
| `2AMLogic/sky130-io-ring` | `9cf5d41503b5566935da2bc0b74ccb50a00fcfab` | `README.md` (draft table, scope), `spec/README.md`, tree listing |
| `2AMLogic/gf180-tmds-tx` | `9a55961ab5e4608d42ffefb70308adcb4b42213e` | `spec/pad-ring-esd-survey.md`, `spec/decisions/0010-pdk-variant.md`, `0011-pad-esd-strategy.md`, `0013-operating-conditions.md` |
| `2AMLogic/2am` | `b477b950a2b39fd2cd199242ddc4cb1c6949e8da` | `REUSE.md` (stamped-copy and adopt-or-record rules) |

PDK and tool facts in `spec/io-ring.md` were read from the installed PDK
(`gf180mcuD`, open_pdks `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7`, the
revision `klt pdk find` resolves on the build host) and from `klt`
`0.7.1.dev1743+g7ee09483b748`, deck content hash
`sha256:612a48b497a015b1e92d6eb93c98a4dc35e00c954dd7ba93a924d8ea6c49d1e7`
(`klt deck info --deck gf180mcu`, `released: False`, a development build).
The PDK pin itself is issue #3's job; see DR-0002.

## Inherited items

| Item | Origin state | This repo | Source |
|---|---|---|---|
| Draw-vs-adopt decision on foundry cells | not ratified | `pending: sky130-io-ring#2`. Working stance, from this repo's README and CLAUDE.md only: `gf180mcu_fd_io` is reference and comparison, not wrapped or re-tiled | origin `9cf5d41` |
| Cell set | draft only (README table row "Cell set") | draft row mirrored in `spec/io-ring.md` §Cell set, marked `pending: sky130-io-ring#2` | origin `9cf5d41` README |
| GPIO function list | draft only (README table row "GPIO") | mirrored, `pending: sky130-io-ring#2` | origin `9cf5d41` README |
| Ring structure | draft only (README table row "Ring") | mirrored, `pending: sky130-io-ring#2` | origin `9cf5d41` README |
| ESD-evidence rule (what pre-silicon evidence can and cannot show) | draft wording only (README, "ESD robustness is a silicon property") | adopted verbatim as the working rule in `spec/io-ring.md` §ESD evidence; formal ratification `pending: sky130-io-ring#2` | origin `9cf5d41` README |
| Spec structure (target / fallback / stretch columns, decision records) | not ratified; origin `spec/README.md` is a placeholder | followed by convention (target / fallback / stretch; numbered records in `spec/decisions/`), `pending: sky130-io-ring#2` | origin `9cf5d41` |
| Signoff definitions (DRC, LVS, latch-up/guard-ring, ring ERC) | draft only (README table row "Signoff") | mirrored, `pending: sky130-io-ring#2`; the gf180mcu rule coverage of each is re-derived (below) | origin `9cf5d41` README |
| Harness and testbench logic | none exists in the origin (`sim/` is a placeholder) | `pending: sky130-io-ring#2`; no stamped copy possible yet. Whether the harness runs unchanged on gf180mcu cannot be answered until it exists (recorded as an open question in `spec/io-ring.md` §Open questions). When it lands it arrives as a stamped copy per `2am/REUSE.md`, not a rewrite | origin `9cf5d41` tree |

## Re-derived items

| Item | Reason it is re-derived | Where |
|---|---|---|
| Supplies and device flavor per path | gf180mcu is dual gate oxide (3.3 V and 5/6 V); the origin's process has no equivalent split | `io-ring.md` §Supplies and devices |
| GPIO electrical targets | device-level; values depend on 5/6 V devices | §GPIO electrical targets |
| Geometry (pitch, depth, pad, rails) | surveyed from `gf180mcu_fd_io` LEF and the `gf180-tmds-tx` survey, not assumed | §Geometry |
| ESD network and discharge paths | different devices (`diode_nd2ps_06v0`, `diode_pd2nw_06v0`, 6 V GGNMOS with ESD implant); DR-0001 | §ESD network |
| Latch-up and guard rings | gf180mcu rules differ; klt coverage measured | §Latch-up and guard rings |
| PVT corners | process names come from this PDK's model library; the 5/6 V models have no skew sections (DR-0002) | §PVT corners |
| klt deck coverage | the deck and its gaps are per PDK | §klt coverage |

## Same-PDK sibling: adopt or record

`gf180-tmds-tx` drew a custom pad and a diode-clamp ESD structure on this PDK.
Outcome in [DR-0001](decisions/0001-esd-structure-from-gf180-tmds-tx.md):
adopt the device family and the ring-continuity and substrate-tap
requirements; do not adopt its pad-specific sizing, capacitance budget, or the
GGNMOS pad cell. A general-purpose rail clamp is not covered by that sibling
and stays open.

No `consumes:` edge is declared (see CLAUDE.md); reading the sibling is
awareness, not a dependency, and no file was copied from it.
