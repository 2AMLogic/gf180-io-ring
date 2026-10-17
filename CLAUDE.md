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
