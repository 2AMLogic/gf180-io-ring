# Roadmap

gf180-io-ring is a 5 V I/O ring with ESD cells on the gf180mcu open PDK, ported from
[sky130-io-ring](https://github.com/2AMLogic/sky130-io-ring) and verified with
[klayout-tools](https://github.com/2AMLogic/klayout-tools) (`klt`), xschem and ngspice.

**Status as of 2026-11-14, `main` @ `cf59481`.** Tracker: #5 (gap to T1).
`WORK_PLAN.md` is the machine-generated label view; this file is the reasoned plan.

## Where it stands

The verdict of record, `manifests/gf180-io-ring.signoff.json` (klt 0.8.0, checked by
`.github/workflows/signoff.yml`), grades **8 of 11 T1 items `met`**. Everything here is
pre-silicon evidence; nothing is ESD-rated.

| Item | Grade | Evidence or open work |
|---|---|---|
| 1 Design sources | met | `design/*.sch`, `*.spice`, `manifests/evidence/item1.json` (PR #27) |
| 2 Layout | met | `layout/gen_ring.py`, `layout/gf180_io_ring.gds`, `manifests/evidence/item2.json` (PR #29, #34) |
| 3 DRC clean | met | `manifests/evidence/item3/` (PR #33) |
| 4 LVS clean | met | `manifests/evidence/item4/` (PR #36); declared `DVSS`/`VSS` substrate join |
| 5 Corner verification | unmet, `partial_coverage` | GPIO rows cited from `sim/gpio-corners/records/20261027T091449Z/`; two declared ESD gaps, #48 / PR #50 |
| 6 Monte Carlo | met | `sim/mc/records/` (PR #51) |
| 7 Post-layout | unmet, `no_evidence` | `sim/gpio-pex/` harness and six probe records; no grid run yet, #20 |
| 8 Characterization report | unmet, `no_evidence` | report on `main` (`sim/characterization/`), not cited in the manifest; #21 |
| 9 Testbenches shipped | met | `attest/item9.json`, `manifests/evidence/item9.json` (PR #26) |
| 10 Repo hygiene | met | `manifests/item10-attestation.json` (PR #25) |
| 11 Power delivery | met | `manifests/evidence/item11/` (PR #42) |

Decision records on `main`: DR-0001 (ESD structure), DR-0002 (PVT corner set), DR-0003
(rail clamp devices, Amendment 1 sizes the `DVDD` clamp to 4800 um), DR-0004 (merged
`DVSS`/`VSS` in pex, Accepted).

Post-layout progress since the last README refresh: the extracted-cell binding is solved
(#40, #53, #58 closed; PRs #54, #59, #60). The remaining failure was a tool gap, `klt`
writing diode instances as `A=`/`P=`, fixed upstream by klayout-tools PR #5184 (issue
klayout-tools#5178). With a klt development build carrying that fix, a one-corner local
probe gives numeric schematic-vs-extracted deltas of about 1.5 to 1.7 % on the `vol_5v`
rows with `body_bias` biased (`sim/gpio-pex/records/20261109T2200Z-probe-klt-diode-fix/record.md`).
A single probe corner is not item-7 evidence.

Delivered on 2026-11-14, closing all three items the previous "Now" section carried
(measured against `main` @ `cf59481`): the stale README blocker references were corrected
(#71, PR #77, merged 2026-11-14T04:11:32Z); the per-spec-row report generator landed as
`sim/characterization/`, aggregating the cited item-5 and item-6 evidence (#72, PR #81,
merged 2026-11-14T09:41:21Z); and the powered `esd_rail_release` request, `--dry-run`
validation and a one-corner probe record (`sim/gpio-corners/records/20261114T185642Z/`)
landed on `main` (#73, PR #83, merged 2026-11-14T19:25:56Z). The 15-corner grid stays
with #45.

## Now

Measured 2026-11-14 (`main` @ `3b8fece`): no open issue carries the ready label
(`loom:issue`) right now — #75 and #85, ready at the previous stamp, have both moved to
`loom:building`. Four items are in flight behind open reviews or builds (#48 via PR #50,
on a ratification decision; #75 via PR #88, the item below; #82 via PR #89; #85, no PR
yet), six are parked or held (see Blocked and waiting), and none await triage. The
previous stamp also carried "#69 via PR #78, in changes-requested"; PR #78 has since
merged (`3b8fece`). No ready label is not the same as nothing moving: the in-flight work
above is mid-flight, not startable.

1. **Delete the never-read `ROW` map in `sim/mc/collect.py` (#75).** The map is
   defined and never consulted — the MC collector emits raw measurement names — and
   its docstring describes a lookup that does not happen. Done when the dead map and
   the stale docstring are gone with no behaviour change to the committed item-6
   record path.

## Next

- **Item 7 grid run (#20, #61).** `sim/gpio-pex/run.sh` on the batch fleet, 19 requests,
  every extracted leg numeric. Done when a `klt pex` report with deltas explained per row
  is cited in `manifests/gf180-io-ring.json` and item 7 reads `met`. The klt-release half
  of the blocker is satisfied: 0.9.2 is on PyPI (released 2026-11-14T07:48:37Z) and
  contains klayout-tools PR #5184 (the fix commit `7a1de82` is an ancestor of the
  `v0.9.2` tag, verified 2026-11-14). What remains is a batch runner image carrying it —
  the fleet image still serves klt 0.9.0 (`sim/gpio-pex/run.sh`, measured 2026-11-14);
  when it exists, bump `KLT_CLIENT` there.
- **Item 5 to `met` (#48, PR #50).** Unblocked by ratification of the two decision records
  on PR #50. Done when the signoff record shows item 5 `met` with no `declared_gaps`.
- **Re-attest item 1 (#49).** `klt netlist --check` on six cells, then
  `klt signoff --attest 1`. Unblocked when PR #50 merges, since the `core_pad` resize it
  re-attests exists only on that branch.
- **Clamp release across corners (#45).** The 15-corner `esd_rail_release` record, after
  the delivered one-corner probe (#73, PR #83) and a confirmed batch submit path.
- **Item 8 `met` (#21).** Add the item-7 column to the delivered per-row report
  (`sim/characterization/`, #72, PR #81), wrap it in a generic evidence envelope and cite
  it. Unblocked when #20 closes.
- **Close the tracker (#5).** When `klt signoff` grades the block T1.

## Later

- **One klt pin.** Signoff CI, `sim/gpio-corners` and `sim/mc` pin klt 0.8.0; `sim/gpio-pex`
  pins 0.9.0. Question first: does regenerating items 3, 4 and 11 under a newer klt
  change any verdict or hash?
- **Rows inherited from the origin.** `spec/io-ring.md` marks the cell set, GPIO function
  list, ring structure and the ESD-evidence wording `pending: sky130-io-ring#2`, which is
  still open. Question first: what does the origin ratify, and does any row diverge here
  by decision record?
- **Origin harness on gf180mcu** (spec open question b). Question first: does the origin
  ship a harness, and does it run unchanged with this PDK's model section names?
- **Item-5 margins on the extracted netlist.** Question first: do the item-7 deltas move
  any GPIO row across its limit at the binding corner?
- **Stretch rows** (analog pass-through pad, selectable drive, slew control). Question
  first: is T1 closed, and does the origin define them?

## Blocked and waiting

- **PR #50 (item 5), on a ratification decision.** Its records are Status: Proposed; the
  PR itself says item 5 must not be read as `met` until they are Accepted. Separately,
  the branch predates PR #54: it adds `0004-core-rail-clamp-budget.md` and
  `0005-vdd-dvdd-coupling.md`, while `main` now has `0004-pex-merged-dvss-vss.md`. Git
  reports no conflict, so the two records need renumbering (0005, 0006) and
  `spec/io-ring.md` re-pointed before merge.
- **#61 and #20 (item 7), on a batch runner image.** In-repo scope of #61 is delivered
  (PRs #62, #63); only the batch run remains. The klt-release blocker is gone — 0.9.2 hit
  PyPI 2026-11-14 with klayout-tools PR #5184 in it — leaving the runner image, which
  still serves klt 0.9.0.
- **#49, on PR #50.** The toolchain blocker (xschem 3.4.7) is cleared.
- **#45, parked and waiting on a human.** Its park record (human, 2026-10-29) waits on
  the Spot batch credential being valid again — that is the condition the hold waits on,
  not a report that it was met, and nothing in the thread confirms it (Guide's
  2026-11-02 note read it as resolved and retracted that on 2026-11-06). The 15-corner
  `esd_rail_release` record still does not exist on `main` and the issue still carries
  `loom:blocked` (measured 2026-11-14). Release needs a human to confirm a fleet submit
  works, then clear the park record.
- **#21, on #20.**
- **#66** is an automated hold digest, not work.

## Not planned

- An ESD rating or any HBM/CDM claim before measured silicon (`spec/io-ring.md`).
- The core, the package, or wrapping the foundry `gf180mcu_fd_io` library (README scope).
- Tiers above T1: the signoff record marks them `tier_not_supported` for this build.
- A shuttle seat or silicon measurements: `measurements/` stays empty; no seat exists.
- Relaxing a ratified spec row to make an item pass; changes go through `spec/decisions/`.
