# gf180-io-ring — agent instructions

Open-source canary block: a 5 V I/O ring with ESD on gf180mcu — GPIO, power
and ground pads, corner and filler cells — designed and verified by AI
agents. A port of `sky130-io-ring`.

- **PDK**: gf180mcu (open PDK). Analog: xschem + ngspice. Layout, DRC, LVS
  and ERC through klayout-tools (`klt`). The dual gate oxide (3.3 V and
  5/6 V devices) is load-bearing: the 5 V I/O path is built from
  thick-oxide devices, the core interface from 3.3 V ones.
- **The PDK is the variable, not the design.** `sky130-io-ring` is the
  origin and master. Inherit its cell set, spec structure, harness and
  decision records; re-derive only what is device-level. Where the origin
  has not ratified something yet, track it there and wait — do not decide
  it twice. Departures go through decision records.
- **The 5 V I/O rules are the point, and the risk.** Thick-oxide device
  rules, guard rings, latch-up spacing, ESD path sizing and continuity of the
  `DVDD`/`DVSS` and core rails through every abutting cell are the rule
  surface under test. Establish which of those klt's gf180mcu deck checks;
  each unchecked rule is a friction item to file.
- **ESD is not proven in simulation.** Simulated clamp behaviour plus
  rule-clean layout is the pre-silicon evidence. Never describe a cell as
  ESD-rated or qualified.
- **Scope discipline.** No `consumes:` edge is declared. The PDK-independent
  half of the work (testbench logic, harness, ring assembly scripts) comes
  from the origin as stamped copies, not rewrites (`REUSE.md` in
  `2AMLogic/2am`). `gf180-tmds-tx` has a same-PDK custom pad cell and
  diode-clamp ESD structure: read it, then adopt or record why not. A
  finding about either sibling is filed on that sibling. The foundry
  `gf180mcu_fd_io` library is reference and comparison only.
- **Friction protocol (the canary's job)**: every time klayout-tools is
  awkward, missing a capability, or wrong for what you need, file an issue at
  `2AMLogic/klayout-tools` describing the tool gap generically — that tracker
  is scoped to the tool, so keep design-specific detail out of it and describe
  the gap, not the design.
- **Verification is the product**: no claim without a testbench. PVT corners
  on every recorded analog result; recorded results are append-only evidence.
- Spec changes go through `spec/` with a decision record; agents do not relax
  the ratified spec to make results pass. `spec/porting-plan.md` names the
  commit of every sibling it read.

<!-- BEGIN LOOM ORCHESTRATION -->
This repository uses [Loom](https://github.com/rjwalters/loom) for AI-powered development orchestration — see the Loom repository for the full guide (roles, labels, worktrees, configuration). When installed, Loom also writes a locally-substituted copy of that guide to `.loom/CLAUDE.md`.

Work is coordinated through `loom:` labels on issues and pull requests, and the same roles run either under `loom-daemon` or by hand in an attended session — daemon mode is optional. Create the labels once with `.loom/scripts/sync-labels.sh` (an install ships `.github/labels.yml` but does not create the labels on the forge). A pull request ready for review carries `loom:review-requested`; Judge reviews it and applies `loom:pr` (approved) or `loom:changes-requested`; Doctor fixes a `loom:changes-requested` pull request and returns it to `loom:review-requested`. Only a `loom:pr` pull request gets merged, and always via this repo's merge script (`.loom/scripts/merge-pr.sh`) — never a raw forge merge command such as `gh pr merge`. Full state machine: `.loom/docs/label-state-machine.md`.
<!-- END LOOM ORCHESTRATION -->

<!-- BEGIN REPO-SKILLS -->
This repository has [Repo Skills](https://github.com/rjwalters/repo) v0.24.3 installed —
general repository hygiene and environment commands invoked as `/repo:<command>`. Run
`/repo:help` for the command list, or see `.claude/skills/repo/SKILL.md` for the full
guide. Hygiene commands apply safe, reversible fixes by default and report each
change; run with `--ask` to review first, and `--prune` to allow irreversible
removals. Managed by `install.sh` — edit outside the markers only.
<!-- END REPO-SKILLS -->
