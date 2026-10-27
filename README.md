# gf180-io-ring

A 5 V I/O ring with ESD on the [gf180mcu](https://github.com/google/gf180mcu-pdk)
open PDK — general-purpose I/O, power and ground pads, corner cells and
fillers, assembled into a closed ring — designed by AI agents driving
[klayout-tools](https://github.com/2AMLogic/klayout-tools) and the
open-source xschem + ngspice flow.

**Status: specification ratified; pre-silicon evidence is simulation-only.** The spec is
ratified, the PDK is pinned, and the smoke, ESD-clamp sizing and foundry `bi_t`
characterization records are committed under `sim/*/records/`. No pad cell is drawn yet.

**Built agent-native.** Every specification, decision record, testbench, and
line of documentation here is produced by AI agents working from a ratified
spec and an append-only evidence trail — not human-authored work that agents
merely assisted with. Verification is the product: every claim traces to a
recorded result under PVT corners. Where the agents hit friction with the
open-source tooling — most often
[klayout-tools](https://github.com/2AMLogic/klayout-tools) — that friction is
filed as a public issue against the tool itself, so the fix benefits everyone
using gf180mcu, not just this repo.

## Why this block, on this PDK

This is a **port, not a new design**. It follows
[sky130-io-ring](https://github.com/2AMLogic/sky130-io-ring), which is
master for the cell set, the spec structure, the verification harness and
the decision records. The experimental design is the one every fleet port
uses: **the PDK is the variable, not the design.** Anything that breaks here
should be assumed to be the PDK, the deck or the tools before it is assumed
to be the ring.

Both repos open at the same time, so the port runs behind its origin: what
the origin has ratified is inherited; what it has not is tracked there, not
decided twice here.

The difference that matters is voltage. gf180mcu is a dual-gate-oxide
process with 3.3 V and 5/6 V devices, and its foundry I/O library
(`gf180mcu_fd_io`) is a 5 V wide-range GPIO library whose cells carry an
I/O-domain supply pair (`DVDD`/`DVSS`) alongside the core pair. A 5 V ring
reopens the device-level choices — the ESD devices, the clamp, the level
shifter, guard-ring construction and latch-up spacing — and each of those is
re-derived here, with departures from the origin argued in decision records.

Same-PDK prior work exists: `gf180-tmds-tx` drew a custom pad cell with a
diode-clamp ESD structure on this PDK and recorded a pad-ring/ESD survey.
Read it before designing a clamp; adopt what fits or record why not.

## Scope

- **In scope**: a bidirectional GPIO pad cell (driver, receiver, core-side
  level shifting, ESD), I/O-supply and core-supply pad cells with clamps, a
  corner cell, fillers, and a small demonstration ring around an empty core.
- **Not in scope**: the core, the package, and any ESD rating claim before
  measured silicon. The foundry `gf180mcu_fd_io` library is the reference
  and comparison, not something this repo wraps or re-tiles.

## Target specification

The ratified targets (target / fallback / stretch, with rationale) are in
[`spec/io-ring.md`](spec/io-ring.md); what is inherited from the origin and
what is re-derived is in [`spec/porting-plan.md`](spec/porting-plan.md). All
figures are design targets, not results and not ratings. Summary of the target
column (the spec is authoritative):

| Parameter | Target |
|---|---|
| Cell set | GPIO, `DVDD` pad, `DVSS` pad, core-supply pad, corner, fillers |
| I/O supply `DVDD` | 5 V ±10 % (fallback 3.3 V ±10 %) |
| Core interface | 3.3 V ±10 % `VDD`, level-shifted in the pad |
| Pad-side devices | 5/6 V thick-oxide (`nfet_06v0`, `pfet_06v0`, `diode_nd2ps_06v0`, `diode_pd2nw_06v0`) |
| Output drive, 5 V | VOL ≤ 0.4 V at 4 mA sink; VOH ≥ `DVDD` − 0.5 V at 4 mA source |
| Rise/fall (10–90 %) | ≤ 5 ns into 15 pF at 5 V; ≤ 8 ns at 3.3 V |
| Input thresholds | VIL ≤ 0.3·`DVDD`, VIH ≥ 0.7·`DVDD`; hysteresis ≥ 0.4 V at 5 V |
| Pad capacitance | ≤ 3 pF added by the pad, input mode |
| Geometry | 75 µm pitch, 350 µm depth, 355 × 355 µm corner |
| ESD network | pad diodes to `DVDD`/`DVSS` plus a rail clamp; HBM 2 kV is a design target only |
| PVT | 5 process × −40/25/125 °C × `DVDD` ±10 %; 5/6 V devices have no process skew in the open models |

ESD robustness is a silicon property. Pre-silicon, this repo can show that
the clamp network turns on and carries the intended current in simulation
and that the layout satisfies the ESD and latch-up rules — nothing more.

Maturity ladder: porting plan recorded → spec ratified → GPIO cell simulated
across PVT → cells DRC/LVS-clean → ring assembled, DRC/LVS/ERC-clean →
shuttle seat → measured silicon. **Current position: spec ratified
(`spec/io-ring.md`); smoke simulation, ESD-clamp sizing and the foundry `bi_t`
comparison are recorded; the first drawn cell is next.**

## Reproduce

Every committed result regenerates from a cold start. Simulation records are
append-only: a run adds a new `records/<UTC stamp>/`, it never edits one. On a
dispatch worker the multi-corner grids go to the batch fleet.

```console
sim/smoke/run.sh                      # model smoke bench; --bad-model-path is its negative control
sim/esd_clamp/run.sh                  # pad-clamp diode sizing; --bad-model-path is its negative control
sim/gpio-bi_t/run.sh                  # foundry bi_t vs targets; --dry-run validates without simulating
uvx --from "klayout-tools==0.8.0" klt signoff \
    --manifest manifests/gf180-io-ring.json \
    --tiers-doc manifests/design-evidence-tiers.md \
    --format json > manifests/gf180-io-ring.signoff.json
```

See [`sim/README.md`](sim/README.md) and [`manifests/README.md`](manifests/README.md).

## Repo layout

```
spec/          ratified spec, porting plan + decision records
design/        pad cell schematics (xschem): driver, receiver, level shifter, ESD
sim/           testbenches + PVT corner results (ngspice)
layout/        cell and ring GDS + DRC/LVS/ERC reports
measurements/  silicon characterization (empty until tape-out)
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).
