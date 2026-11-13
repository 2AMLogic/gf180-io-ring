# Work Log

Chronological record of merged PRs and closed issues, maintained by the Guide
triage role. Newest first.

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
