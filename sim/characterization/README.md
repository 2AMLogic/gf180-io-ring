# sim/characterization

One aggregated, current artifact giving per-spec-row performance across conditions,
with the evidence record behind each number. The first slice of T1 item 8 (issue #21):
the corner-matrix and Monte Carlo columns, which are already cited on `main`. The
post-layout column stays with #21.

    sim/characterization/run.sh           # rewrite report.md and report.json
    sim/characterization/run.sh --check   # fail if the committed report is stale

- `build.py` — the generator. Reads `manifests/gf180-io-ring.json` and, through it,
  only the files that manifest cites as T1 item-5 (corner matrix) and item-6
  (Monte Carlo yield) evidence.
- `run.sh` — runner; `--check` builds into a temporary directory and byte-compares
  against the committed report.
- `report.json` — the machine twin, written first: one object per spec row, every
  number with the cited file it came from.
- `report.md` — rendered from `report.json` and nothing else, so the two forms cannot
  disagree.

It runs **no simulation** and needs nothing but `python3` — no klt, no PDK, no
ngspice — which is why `--check` is cheap enough to run on every pull request.

## What this report is not

It aggregates **pre-silicon simulation**. Nothing in it rates or qualifies anything:
the ESD rows are simulated clamp behaviour, and simulated clamp behaviour plus
rule-clean layout is pre-silicon evidence, not an ESD rating.

It is also **not** a second source of truth for the ratified spec. The generator
restates no limit of its own: every limit it prints is read from a cited envelope's
`measurements[].limits`, and the row spine is the manifest's `spec_rows["5"]`. A
changed spec limit reaches this table only by way of a re-run bench and a re-cited
envelope — never by editing this directory.

## Regenerate it in the same change as the manifest

**Any change to `manifests/gf180-io-ring.json` must come with a regenerated report in
the same pull request.** A new citation, a re-pointed record, a `gap` closed or added
— all of them change this report, and `.github/workflows/signoff.yml` runs
`run.sh --check` on every pull request, so a stale committed report turns that job red
on whichever change moves the manifest next. This is the same obligation the committed
`klt signoff` record (`manifests/gf180-io-ring.signoff.json`) already carries, so it is
a known workflow rather than a new burden.

## Caveats the report carries, and why they are there

**The two columns do not always share a limit.** Four rows (`vil_5v`, `vih_5v`,
`vil_3v3`, `vih_3v3`) carry a different limit in the corner-matrix column than in the
Monte Carlo column. Both are correct readings of the one ratified rule
(VIL <= 0.3 * `DVDD`, VIH >= 0.7 * `DVDD`): the corner matrix evaluates it at the
binding `DVDD` extreme and the Monte Carlo campaign at nominal `DVDD`. The report
renders the Monte Carlo limit inline for those rows. Neither is relaxed and neither is
reconciled — reconciling them would be a spec change and belongs in a decision record.

**Monte Carlo is never corner coverage.** Every cited yield campaign samples the
`typical` process section only, and the temperatures cited differ per row (three for
the output-level and transfer rows, 25 C alone for the pull devices). A Monte Carlo
figure therefore cannot stand in for a missing corner verdict, and the report says so
in each cell and in its methodology section.

**The row-to-file mapping is asserted, not derived.** The manifest states which spec
rows each envelope is evidence for; `klt signoff` records every item-5 row source as
`asserted`. This report inherits that assertion. It checks the mapping for consistency
— a cited row no measurement can supply, an ambiguous join, or a measurement base name
unknown to `ROWS` all fail the build loudly — but it does not independently prove that
a given envelope measures the row it is cited for.

**Content hashes are not verified here.** The manifest's item-5 `content_hash` is the
envelope's own `environment.netlist_sha256`, not the sha256 of the cited file, and
item-6 citations carry none. Re-hashing cited files would fail on all 46. Artifact
freshness belongs to `klt signoff`, which `.github/workflows/signoff.yml` already
enforces on every pull request.

**"No evidence" is never a pass.** The post-layout cell of every row reads
`no evidence` because the manifest cites no post-layout extraction. Each spec row
carrying a `gap` string reads `no evidence` too, quoting that string. The gap set is
read from `spec_rows["5"][*].gap` on every build and is never hard-coded, so the report
follows the manifest when a gap is closed or added.

## Design notes

- **The spine is the manifest, not the spec document.** `spec/io-ring.md` names its
  parameters in prose and carries no row ids, so the ids come from
  `manifests/gf180-io-ring.json` `spec_rows` and the report links the spec section for
  the human-readable parameter name.
- **`rows.json` and `results.tsv` are not read.** They sit in the corner-matrix record
  directory and are convenient, but the manifest cites neither, and this report's
  provenance has to be the manifest's. Each cited envelope already carries the
  per-measurement reduction (`measurements[].worst_case`), so nothing in
  `sim/gpio-corners/collect.py`'s margin logic is reimplemented here. `rows.json` makes
  a good independent cross-check for a reviewer precisely because it is not an input.
- **The measurement base-name map is imported, not retyped.** `ROWS`, `CONTEXT`, `KEY`
  and `fmt` come from `sim/gpio-corners/collect.py`, loaded **by path**
  (`importlib.util.spec_from_file_location`) rather than through a `sys.path` insert:
  `sim/mc/collect.py` is also named `collect`, so a path insert would make which module
  wins depend on insert order.
- **The alias map is the one real design decision.** Item 5 names measurements
  (`r_pullup`, `vf_up_hbm`) while the manifest cites those envelopes for single spec
  rows (`pull_5v`, `esd_pad_clamp`), and item 6 splits the pull devices into their own
  spec rows (`pullup_5v`, `pulldown_5v`) which project back onto the spine's `pull_5v`.
  One `ALIAS` map in `build.py` covers both directions and is printed in the report so
  the join is auditable rather than implicit.
- **The binding point is the least *relative* margin.** One envelope carries nine
  supply instances whose trip-point limits scale with `DVDD`, so the smallest absolute
  margin is not always the binding one. This is the same normalization
  `sim/gpio-corners/collect.py` applies.
- **Where a row's cited campaigns disagree, the weakest is reported** — the lowest
  confidence-interval low bound for Monte Carlo, the least relative margin for the
  corner matrix.

There is no `klt` verb that produces this artifact. On the repo pin
(`klayout-tools==0.8.0`), `klt report` refuses a `klt sim` envelope outright
(`unrecognized shape (schema_version=3)`) and `klt signoff --manifest` grades T1-T4
tier *items*, not spec *rows*. That tool gap is filed upstream per the repo's friction
protocol as `2AMLogic/klayout-tools#5691`; if a future pin grows an aggregation verb,
this generator should be retired in favour of it.
