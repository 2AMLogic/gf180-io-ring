# Roadmap

gf180-io-ring is a 5 V I/O ring with ESD cells on the gf180mcu open PDK, ported from
[sky130-io-ring](https://github.com/2AMLogic/sky130-io-ring) and verified with
[klayout-tools](https://github.com/2AMLogic/klayout-tools) (`klt`), xschem and ngspice.

**Status as of 2026-11-13, `main` @ `7cc3fa2`.** Tracker: #5 (gap to T1).
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
| 8 Characterization report | unmet, `no_evidence` | nothing committed, #21 |
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

## Now

No open issue carries a ready label today: every open issue is parked or held (see
Blocked and waiting). The items below can start today and do not depend on any hold.

1. **Correct the stale blocker references in the READMEs.** `README.md` still says item 7
   has "#40 and #53 blocking" (both closed), and the header of `sim/gpio-pex/README.md`
   names klayout-tools#5178 as the blocker although its own later section records the fix.
   Done when both files name #61 and the batch runner image as the remaining blocker and
   `klt signoff --attest 10` still passes. No issue yet (seed 1).
2. **Characterization report generator for the rows that already have evidence.** Item 8
   needs one aggregated per-spec-row artifact; items 5 and 6 are on `main`, item 7 is not.
   Done when a committed script regenerates a report from the cited item-5 and item-6
   records, byte-identical on a second run, with every row linked to its record and the
   item-7 column explicitly empty; the manifest does not cite it yet. First slice of #21;
   no issue yet (seed 2).
3. **`esd_rail_release` deck, dry-run and one-corner probe.** DR-0003 Amendment 1 records
   release after the pulse as "Not evaluated". Done when `sim/gpio-corners/gen_requests.py`
   emits a separate powered `esd_rail_release` request, `run.sh --dry-run` validates it and
   a `--probe` record reports gate release and `DVDD` recovery at the one local corner.
   The 15-corner grid stays with #45. No issue yet (seed 3).

## Next

- **Item 7 grid run (#20, #61).** `sim/gpio-pex/run.sh` on the batch fleet, 19 requests,
  every extracted leg numeric. Done when a `klt pex` report with deltas explained per row
  is cited in `manifests/gf180-io-ring.json` and item 7 reads `met`. Blocked on a klt
  release containing klayout-tools PR #5184 (latest on PyPI as read today is 0.9.1; the
  working probe used 0.9.2.dev397) and a batch runner image carrying it; then bump
  `KLT_CLIENT` in `sim/gpio-pex/run.sh` from 0.9.0.
- **Item 5 to `met` (#48, PR #50).** Unblocked by ratification of the two decision records
  on PR #50. Done when the signoff record shows item 5 `met` with no `declared_gaps`.
- **Re-attest item 1 (#49).** `klt netlist --check` on six cells, then
  `klt signoff --attest 1`. Unblocked when PR #50 merges, since the `core_pad` resize it
  re-attests exists only on that branch.
- **Clamp release across corners (#45).** The 15-corner `esd_rail_release` record, after
  Now item 3 and a confirmed batch submit path.
- **Item 8 `met` (#21).** Add the item-7 column to the Now item 2 report, wrap it in a
  generic evidence envelope and cite it. Unblocked when #20 closes.
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
- **#61 and #20 (item 7), on an upstream release and a runner image.** In-repo scope of
  #61 is delivered (PRs #62, #63); only the batch run remains.
- **#49, on PR #50.** The toolchain blocker (xschem 3.4.7) is cleared.
- **#45, on a confirmed batch submit.** Its park record waits for a human to confirm the
  submit path works; nothing in the thread confirms it.
- **#21, on #20.**
- **#66** is an automated hold digest, not work.

## Not planned

- An ESD rating or any HBM/CDM claim before measured silicon (`spec/io-ring.md`).
- The core, the package, or wrapping the foundry `gf180mcu_fd_io` library (README scope).
- Tiers above T1: the signoff record marks them `tier_not_supported` for this build.
- A shuttle seat or silicon measurements: `measurements/` stays empty; no seat exists.
- Relaxing a ratified spec row to make an item pass; changes go through `spec/decisions/`.
