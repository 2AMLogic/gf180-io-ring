# Work Log

Chronological record of merged PRs and closed issues, maintained by the Guide
triage role. Newest first.

### 2026-11-20

- **PR #130**: fix: keep selftest sandboxes and build outputs under the shared temp dir
- **Issue #128** (closed): Clean up temporary sandboxes after the characterization self-test

### 2026-11-18

- **PR #120**: ci: add merge_group trigger to the signoff workflow
- **Issue #119** (closed): Merge queue: add the merge_group trigger to the required-check workflow(s)

### 2026-11-17

- **PR #115**: build: replace always-green package.json stubs with real repo checks
- **Issue #116** (closed): CI does not run the new pnpm test entry point (join-refusal selftest is agent-only)
- **Issue #112** (closed): Replace vacuous package.json test/lint/check scripts that always exit 0
- **PR #111**: chore(loom): resync installed Loom to v0.19.1306

### 2026-11-16

- **PR #106**: docs: mark DR-0006 Accepted per operator ruling q107 (1b/2c/3b)
- **Issue #96** (closed): Operator ruling: DR-0006 powered-rail transient duty and peak budget
- **PR #104**: chore(loom): resync installed Loom to v0.19.1302

### 2026-11-15

- **PR #101**: docs: record gpio-bi_t capacity-policy exception at the batch-set call site
- **Issue #100** (closed): Decide gpio-bi_t's batch capacity policy: --wait-for-capacity 600 alongside --capacity-retries 3, or record the exception
- **PR #99**: docs: cite tracker item 5 by its real title in DR-0006 item 3(a)
- **Issue #97** (closed): DR-0006 glosses tracker item 5 as "klt rule coverage"; item 5 is "Full corner verification vs a ratified spec"
- **PR #95**: fix: write spec_rows per-key in gpio-corners cite.py
- **Issue #84** (closed): bug: cite.py replaces the whole spec_rows map, silently deleting item 6's declared rows
- **PR #94**: sim: use klt --wait-for-capacity 600 instead of a hand-rolled retry loop
- **Issue #93** (closed): Replace hand-rolled batch-capacity retry in sim/mc/run.sh with klt's --wait-for-capacity
- **PR #90**: spec: propose DR-0006 on powered-rail transient duty and peak budget
- **Issue #85** (closed): Decision record needed: is a transient on a POWERED DVDD rail in the clamp's duty, and under what peak budget?
- **PR #92**: refactor: centralize input-threshold and pad-capacitance spec limits in sim/gpio_common.py
- **Issue #79** (closed): Share the 3 pF pad-capacitance limit and the 0.3/0.7 input-threshold fractions via sim/gpio_common.py
- **PR #89**: characterization: refuse an unresolvable citation join instead of pairing onto an orphan row
- **Issue #82** (closed): sim/characterization: a mis-cited envelope is absorbed by the single-orphan-row join rung instead of failing the build
- **PR #88**: refactor(sim): drop the never-read ROW map in the MC collector and fix its stale docstring
- **Issue #75** (closed): Delete the never-read ROW map in sim/mc/collect.py and correct its stale docstring
- **PR #86**: docs: refresh ROADMAP.md against the 2026-11-14 tracker — all three Now items delivered

### 2026-11-14

- **PR #78**: refactor: define the ratified GPIO spec limits once in sim/gpio_common.py
- **Issue #69** (closed): Share the ratified spec limits via sim/gpio_common.py instead of five literal copies
- **PR #83**: feat(sim): add a powered-rail esd_rail_release deck and make --probe write a record
- **Issue #73** (closed): esd_rail_release request: powered deck, dry-run validation and a one-corner probe (first slice of #45)
- **PR #81**: feat(sim): aggregate cited item-5/item-6 evidence into a per-spec-row report
- **Issue #72** (closed): Characterization report generator for the item-5 and item-6 rows (first slice of #21)
- **PR #74**: refactor(layout): drop dead tie_bar(), STUB_X and stub_stack text= flag
- **Issue #68** (closed): Remove born-dead code in layout/gen_ring.py: tie_bar(), STUB_X, stub_stack text= parameter
- **PR #77**: docs: point item-7 blocker at the runner-image rebake, not closed #40/#53
- **Issue #71** (closed): Correct stale item-7 blocker references in README.md and sim/gpio-pex/README.md
- **PR #70**: docs: roadmap as of 2026-11-13

### 2026-11-12

- **PR #64**: Bump Repo Skills 0.25.10 -> 0.26.1

### 2026-11-09

- **PR #63**: docs(gpio-pex): record extracted leg running with klt diode fix
- **PR #62**: docs(gpio-pex): record A=/P= diode params as cause of extracted-leg ngspice_fatal
- **Issue #53** (closed): gpio-pex: wrap schematic DUT in extracted pin order (pin_order_mismatch)
- **PR #60**: feat(gpio-pex): wrap schematic leg and reorder Xdut to extracted pin order
- **Issue #40** (closed): gpio: DVSS and VSS merge through the substrate, so pex cannot bind the extracted cell
- **PR #54**: feat: tie declared DVSS/VSS pins in gpio-pex, add DR-0004

### 2026-11-08

- **Issue #58** (closed): pex: extraction probe uses gf180mcuA while the repo pins gf180mcuD
- **PR #59**: fix(gpio-pex): pass pinned PDK variant to klt pex and assert it in provenance

### 2026-11-07

- **PR #57**: Bump Repo Skills 0.25.1 -> 0.25.10

### 2026-11-06

- **Issue #55** (closed): Bring README status, maturity position and Reproduce section in line with the signoff record
- **PR #56**: docs: align README status, reproduce and layout with the signoff record

### 2026-11-01

- **PR #52**: Bump Repo Skills 0.24.7 -> 0.25.1

### 2026-10-29

- **Issue #19** (closed): T1 item 6 (Monte Carlo): klt yield campaign for the GPIO input thresholds, hysteresis and pull resistance
- **PR #51**: feat: Monte Carlo yield evidence for GPIO thresholds, pulls and drive (T1 item 6)

### 2026-10-27

- **Issue #46** (closed): Bump klayout-tools pin 0.7.0 → 0.8.0
- **PR #47**: chore: pin sim clients and runner prose to klt 0.8.0
- **Issue #37** (closed): Dedupe helpers shared by sim/gpio-bi_t and sim/gpio-corners
- **PR #44**: refactor: share GPIO bench helpers via sim/gpio_common.py
- **Issue #38** (closed): Size the DVDD-DVSS rail clamp: simulated peak 10-13.5 V against the 6 V device-class budget
- **PR #43**: feat: size DVDD/DVSS rail clamp to 4800 um and draw m= copies in the ring layout
- **Issue #24** (closed): T1 item 11 (power delivery): klt erc supply spec for DVDD/DVSS/VDD/VSS ring continuity
- **PR #42**: feat: add klt erc supply evidence for the ring and cite it as T1 item 11
- **PR #41**: feat: add gpio-pex harness and probe record for post-layout verification
- **Issue #35** (closed): Follow-on from PR #31: GPIO cell sizing for corner misses; rail-clamp transient binning
- **PR #39**: feat: resize GPIO driver and pull-up, split rail clamp into m= copies, record fleet corner run
- **Issue #17** (closed): T1 item 4 (LVS clean): klt lvs match of each cell and the ring against the item-1 netlists
- **PR #36**: feat: LVS-compare the ring and its cells against the item-1 netlists
- **Issue #32** (closed): Layout: draw intra-cell signal/rail routing and tap ties so the ring is LVS-comparable
- **PR #34**: feat: wire ring cells from their netlists and join rails through the corner
- **Issue #18** (closed): T1 item 5 (corner verification): PVT corner matrix of the GPIO pad against every ratified spec row
- **PR #31**: feat(sim): GPIO cell PVT corner verification as T1 item 5 evidence
- **Issue #16** (closed): T1 item 3 (DRC clean): klt drc clean on every cell and on the assembled ring, with deck coverage quoted
- **PR #33**: fix: make ring layout klt drc clean and cite DRC evidence for T1 item 3
- **Issue #28** (closed): Fix esd_clamp negative control: accepted control exits 0, contradicting 'must exit non-zero'
- **PR #30**: fix: exit 3 when a negative control is accepted
- **Issue #15** (closed): T1 item 2 (layout): generated GDS for each ring cell and the assembled demonstration ring, with documented provenance
- **PR #29**: feat: add KLayout ring generator and committed GDS for T1 item 2
- **Issue #23** (closed): T1 item 10 (repo hygiene): current README status and reproduction steps, hygiene inventory, klt signoff --attest 10
- **PR #25**: docs: attest T1 item 10 hygiene, refresh README, pin klt 0.8.0
- **Issue #22** (closed): T1 item 9 (testbenches shipped): testbench inventory and klt signoff --attest 9
- **PR #26**: feat(signoff): attest T1 item 9 testbench inventory and gate it in CI
- **Issue #14** (closed): T1 item 1 (design sources): xschem schematics and derived netlists for the GPIO, supply and corner cells and the demonstration ring
- **PR #27**: feat(design): xschem sources and derived netlists for the I/O cells and ring

### 2026-10-23

- **Issue #10** (closed): sim: characterize the foundry gf180mcu_fd_io__bi_t against the ratified GPIO electrical targets across the PVT set (comparison anchor)
- **PR #13**: feat(sim): foundry bi_t PVT characterization bench against the GPIO targets
- **Issue #11** (closed): sim: pad-clamp diode I-V, leakage and capacitance vs area across PVT to size the ESD pad clamps (HBM design target only)
- **PR #12**: feat(sim): pad-clamp diode I-V, leakage and capacitance bench with area derivation

### 2026-10-21

- **PR #9**: Bump Repo Skills 0.24.3 -> 0.24.7

### 2026-10-20

- **Issue #4** (closed): Commit a T1 block manifest and a klt signoff CI job (T1 item 10)
- **PR #7**: ci: add klt signoff manifest, verdict record and freshness check

### 2026-10-17

- **Issue #3** (closed): Pin gf180mcu and ngspice and commit a smoke simulation (T1 item 9 groundwork)
- **PR #8**: feat(sim): pin gf180mcu toolchain and add model smoke bench
- **Issue #2** (closed): Draft and ratify the target spec
- **PR #6**: docs(spec): ratify gf180 I/O ring target spec and porting plan
- **PR #1**: chore(loom): Install Loom 0.19.1180
