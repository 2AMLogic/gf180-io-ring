# gpio cell (design/gpio.spice): ONE-CORNER LOCAL PROBE, not the PVT result

**This record is a single-corner local debug probe, not evidence.** It is one corner (typical process, 25 C) run locally on the submitting host, not the DR-0002 PVT set, and the host's ngspice and klt are not the fleet runner's (see the provenance block below). It does NOT establish any row, it is NOT the PVT result, and `cite.py` refuses it as T1 item 5 evidence. Results are measurements, not ratings: no cell is ESD-rated or qualified, and the ESD rows below are simulated clamp behaviour only.

- date (UTC): 20261114T185642Z
- **probe: one corner (typical, 25 C), run locally. NOT the PVT result and not citable evidence.**
- probe=true
- open_pdks revision (pinned, sim/toolchain.json): `c6d73a35f524070e85faff4a6a9eef49553ebc2b`, variant `gf180mcuD`
- ngspice on this host: `ngspice-47` -- the fleet runner image's own is ngspice-46, so this is not the engine a batch record is made with
- klt client: `klt 0.9.2.dev1029+g76f47afa48f1` (the host klt, NOT the `uvx --from klayout-tools==0.8.0 klt` the fleet runner matches); backend: local
- repo commit: `046f15e8c00702a35a58dbf729ffa1b22a8e6836`; DUT: `design/gpio.spice`, `design/dvdd_pad.spice`
- models: read from the host PDK install, NOT staged per job (`stage_model_inputs` is a batch-backend step). Compare each envelope's own `provenance.pdk` and `provenance.deck.content_hash` against a batch record's before reading any number here as comparable.

## Known limitation (quoted from spec/io-ring.md, section PVT corners; DR-0002)

> **Known limitation, measured.** In the model file, every top-level process
> section (`typical`, `ff`, `ss`, `fs`, `sf`) loads the *typical* sections
> `nfet_06v0_t`, `pfet_06v0_t`, `nfet_06v0_nvt_t` for the 5/6 V devices; only the
> 3.3 V FETs have skewed sections. So a process corner moves the core devices
> but **not the 5 V devices that carry the ring's I/O path**. `klt pdk corners`
> also reports `fs` and `sf` as incomplete (MOS skewed, other families left at
> typical). The recorded results must say so, and thick-oxide process spread is
> covered only by supply, temperature and an explicit margin, not by a corner.
> Reference points: the foundry Liberty set spans `ff_n40C_5v50`, `ff_125C_5v50`,
> `ss_125C_4v50`, `tt_025C_5v00` `[LIB]`.

Every row below therefore moves with supply and temperature, and with process only through the 3.3 V devices and the passives; `ff`/`ss` say nothing about 5/6 V process spread, and `fs`/`sf` are incomplete corners (`klt pdk corners`).

## Grid

ONE corner: typical process, 25 C, with all nine (`DVDD`, `VDD`) instances still present in the gpio decks, so a gpio row has 9 points and a single-instance ESD deck has 1. The full bench is 5 process x -40/25/125 C = 15 corners per request (135 points per gpio row); none of that was run here. A probe cannot show process or temperature spread, which is where every ESD and timing row of this bench is binding, so read every number below as one point of an unmeasured distribution.

## Per-row verdict

A row passes only if every point of the grid is within its target. The binding point is the one with the least margin (or the extreme value for report-only rows).

| Row | Parameter | Target | Worst | Binding corner | Binding supply | Meets target | Failing points | Request |
|---|---|---|---|---|---|---|---|---|
| cap_3v3 | PAD capacitance, input mode, 1 MHz | <= 3 pF | 0.3607 pF | `typical/novdd/25C` | DVDD 2.97 V, VDD 2.97 V | yes | 0/9 | cap_3v3 |
| cap_5v | PAD capacitance, input mode, 1 MHz | <= 3 pF | 0.3295 pF | `typical/novdd/25C` | DVDD 4.5 V, VDD 2.97 V | yes | 0/9 | cap_5v |
| fall_3v3 | fall 90-10 % into 15 pF | <= 8 ns | 3.9 ns | `typical/novdd/25C` | DVDD 2.97 V, VDD 2.97 V | yes | 0/9 | edges_3v3 |
| rise_3v3 | rise 10-90 % into 15 pF | <= 8 ns | 3.953 ns | `typical/novdd/25C` | DVDD 2.97 V, VDD 2.97 V | yes | 0/9 | edges_3v3 |
| fall_5v | fall 90-10 % into 15 pF | <= 5 ns | 2.891 ns | `typical/novdd/25C` | DVDD 4.5 V, VDD 3.63 V | yes | 0/9 | edges_5v |
| rise_5v | rise 10-90 % into 15 pF | <= 5 ns | 2.673 ns | `typical/novdd/25C` | DVDD 4.5 V, VDD 3.63 V | yes | 0/9 | edges_5v |
| esd_pad_dn | pad clamp from DVSS, forward drop at the 1.33 A stress current | <= 3 V | 1.265 V | `typical/novdd/25C` | - | yes | 0/1 | esd_pad |
| esd_pad_up | pad clamp to DVDD, forward drop at the 1.33 A stress current | <= 3 V | 1.113 V | `typical/novdd/25C` | - | yes | 0/1 | esd_pad |
| esd_rail | DVDD-DVSS rail clamp, peak DVDD under a 1.33 A / 10 ns-rise pulse | <= 6 V | 4.437 V | `typical/novdd/25C` | - | yes | 0/1 | esd_rail |
| esd_rail_release_irail | supply current into DVDD at the end of the window (clamp + trigger; a latched clamp would hold this high) | report only | 0.0002747 mA | `typical/novdd/25C` | - | n/a | 0/1 | esd_rail_release |
| esd_rail_release_dvdd | DVDD at the end of the window, rail powered (recovered = back to the supply less the series-R drop) | report only | 5 V | `typical/novdd/25C` | - | n/a | 0/1 | esd_rail_release |
| esd_rail_release_gate_peak | peak rail clamp gate with the rail powered (how hard the RC trigger drives it from a powered start) | report only | 2.534 V | `typical/novdd/25C` | - | n/a | 0/1 | esd_rail_release |
| esd_rail_release_gate | rail clamp gate at the end of the window, rail powered (released = back to 0 V) | report only | 5.368e-06 V | `typical/novdd/25C` | - | n/a | 0/1 | esd_rail_release |
| esd_rail_release_peak | peak DVDD under the same pulse with the rail powered (context for the release rows; NOT esd_rail's 6 V budget row) | report only | 8.66 V | `typical/novdd/25C` | - | n/a | 0/1 | esd_rail_release |
| pulldown_3v3 | pull-down equivalent R, PAD at DVDD/2 | report only | 48.8 kohm | `typical/novdd/25C` | DVDD 2.97 V, VDD 2.97 V | n/a | 0/9 | pulldown_3v3 |
| pulldown_5v | pull-down equivalent R, PAD at DVDD/2 | report only | 31.51 kohm | `typical/novdd/25C` | DVDD 4.5 V, VDD 2.97 V | n/a | 0/9 | pulldown_5v |
| pullup_3v3 | pull-up equivalent R, PAD at DVDD/2 | report only | 64.02 kohm | `typical/novdd/25C` | DVDD 2.97 V, VDD 2.97 V | n/a | 0/9 | pullup_3v3 |
| pullup_5v | pull-up equivalent R, PAD at DVDD/2 | report only | 38.59 kohm | `typical/novdd/25C` | DVDD 4.5 V, VDD 2.97 V | n/a | 0/9 | pullup_5v |
| voh_3v3 | VOH drop, DVDD - VOH, at the spec load | <= 0.4 V | 0.1439 V | `typical/novdd/25C` | DVDD 2.97 V, VDD 2.97 V | yes | 0/9 | voh_3v3 |
| voh_5v | VOH drop, DVDD - VOH, at the spec load | <= 0.5 V | 0.1993 V | `typical/novdd/25C` | DVDD 4.5 V, VDD 2.97 V | yes | 0/9 | voh_5v |
| vol_3v3 | VOL at the spec load | <= 0.4 V | 0.1123 V | `typical/novdd/25C` | DVDD 2.97 V, VDD 2.97 V | yes | 0/9 | vol_3v3 |
| vol_5v | VOL at the spec load | <= 0.4 V | 0.1633 V | `typical/novdd/25C` | DVDD 4.5 V, VDD 2.97 V | yes | 0/9 | vol_5v |
| hyst_3v3 | hysteresis Vt+ - Vt- | >= 0.25 V | 0.5513 V | `typical/novdd/25C` | DVDD 2.97 V, VDD 3.3 V | yes | 0/9 | xfer_3v3 |
| vil_3v3 | VIL as lower trip Vt- (reads low up to the limit) | >= 0.891 V | 1.124 V | `typical/novdd/25C` | DVDD 2.97 V, VDD 2.97 V | yes | 0/9 | xfer_3v3 |
| vih_3v3 | VIH as upper trip Vt+ (reads high from the limit) | <= 2.079 V | 1.675 V | `typical/novdd/25C` | DVDD 2.97 V, VDD 3.63 V | yes | 0/9 | xfer_3v3 |
| hyst_5v | hysteresis Vt+ - Vt- | >= 0.4 V | 0.6428 V | `typical/novdd/25C` | DVDD 4.5 V, VDD 3.63 V | yes | 0/9 | xfer_5v |
| vil_5v | VIL as lower trip Vt- (reads low up to the limit) | >= 1.35 V | 1.763 V | `typical/novdd/25C` | DVDD 4.5 V, VDD 2.97 V | yes | 0/9 | xfer_5v |
| vih_5v | VIH as upper trip Vt+ (reads high from the limit) | <= 3.15 V | 2.406 V | `typical/novdd/25C` | DVDD 4.5 V, VDD 2.97 V | yes | 0/9 | xfer_5v |

## Reading the rows

- **Input thresholds.** VIL/VIH use the receiver convention: Vt- >= 0.3*`DVDD` and Vt+ <= 0.7*`DVDD`, read from a slow PAD ramp up then down at the point where `Y` crosses `VDD`/2. The spec text does not state a convention; the raw Vt+/Vt- are in results.tsv.
- **Pull resistance** is a nominal-point row: the `*_nominal` requests (typical, 25 C, nominal `DVDD`) carry the 25-100 kohm limit; the full-grid `pullup_*`/`pulldown_*` requests are report-only context.
- **ESD pad clamps.** The cell is unpowered (every rail at 0 V) and a current source forces 1.33 A (2 kV / 1.5 kohm, the HBM arithmetic of design/README.md) into PAD towards `DVDD` (`diode_pd2nw_06v0`) and out of PAD from `DVSS` (`diode_nd2ps_06v0`). The spec states no forward-drop number; the 3.0 V budget is the assumption recorded in design/README.md (half the 6.0 V device class) and is not a spec row. Turn-on voltage at 1 mA is reported (`vf_*_1ma`, results.tsv), without a limit.
- **ESD rail clamp (simulated transient).** The `DVDD` pad cell (RC-triggered `nfet_06v0`, DR-0003 as amended; 48 x 100 um via `m=48`, trigger-inverter `pfet` 10 x 10 um via `m=10`, since one wider instance does not bin on the fleet) is unpowered; a 1.33 A / 10 ns-rise pulse is forced into `DVDD`. The 6 V peak limit is the `*_06v0` device class, an assumption and not a spec row. Simulated clamp behaviour only: nothing here is an ESD rating.
- **ESD rail clamp release, rail powered (`esd_rail_release`).** The same pad cell and the same 1.33 A / 10 ns-rise pulse as `esd_rail`, but `DVDD` is held at its nominal 5 V through a 50 ohm series resistance and the window runs to 5 us, about ten times DR-0003 decision item 1's "order of 0.5 us" trigger RC design intent, with the rows read at 4.5 us. This is the gap DR-0003 Amendment 1 item 3 records as **Not evaluated** (release after the pulse and absence of latching). **Every row of this request is report-only and carries no limit**: the spec states no release criterion, and `esd_rail`'s 6 V budget is an assumption about the *unpowered* deck, so reusing it here would be inventing a limit. The two decks start from different quiescent states and answer different questions - this one is not a second opinion on `esd_rail`'s peak. The series resistance and the window length are declared bench assumptions (`gen_requests.py`), not spec rows. The current row is the whole rail's current (clamp plus trigger), not the clamp FET's drain current. Simulated clamp behaviour only: nothing here is an ESD rating.
- **Not covered (declared gaps).** The core `VDD`-`VSS` rail clamp (3.3 V devices; the spec gives no voltage budget for it) and the `VDD`/`DVDD` cross-domain coupling (spec: decision record to follow) are not simulated here.

## Open questions for a decision record

These are questions this bench raises and cannot answer. None is a limit, none is written into `spec/`, and nothing below was relaxed to make a row pass.

- **What counts as release?** `spec/io-ring.md` gives no criterion for the rail clamp after the pulse: no gate-voltage ceiling, no recovery tolerance on `DVDD`, no quiescent-current ceiling, and no time by which any of them must hold. The `esd_rail_release_*` rows are therefore reported against no target. Turning them into pass/fail rows needs a decision record to state the three numbers and the time - that is not this bench's call.
- **Is a transient on a POWERED rail in the clamp's duty at all, and under what budget?** The 6 V figure `esd_rail` carries is the `*_06v0` device class applied to the unpowered HBM-like case. Whether the same ceiling, a different one, or none applies when the rail is already up is undecided, so `esd_rail_release_peak` is reported without one. A decision record should settle it before anyone reads that row as a pass or a failure.
- **Latch-up is not fully covered by this bench.** A quiescent rail current back at its pre-pulse value is evidence the clamp released, not proof that no parasitic structure latched: the pad-side latch-up and guard-ring rules remain a klt deck gap (klayout-tools#3793, DR-0003 Amendment 1 item 3), so there is no rule check to pair with this measurement.

## Requests

| Request | Status | Job | Runner klt | ngspice |
|---|---|---|---|---|
| `vol_5v` | pass | `None` | `None` | `47` |
| `vol_3v3` | pass | `None` | `None` | `47` |
| `voh_5v` | pass | `None` | `None` | `47` |
| `voh_3v3` | pass | `None` | `None` | `47` |
| `edges_5v` | pass | `None` | `None` | `47` |
| `edges_3v3` | pass | `None` | `None` | `47` |
| `xfer_5v` | pass | `None` | `None` | `47` |
| `xfer_3v3` | pass | `None` | `None` | `47` |
| `pullup_5v` | pass | `None` | `None` | `47` |
| `pullup_3v3` | pass | `None` | `None` | `47` |
| `pulldown_5v` | pass | `None` | `None` | `47` |
| `pulldown_3v3` | pass | `None` | `None` | `47` |
| `cap_5v` | pass | `None` | `None` | `47` |
| `cap_3v3` | pass | `None` | `None` | `47` |
| `esd_pad` | pass | `None` | `None` | `47` |
| `esd_rail` | pass | `None` | `None` | `47` |
| `esd_rail_release` | pass | `None` | `None` | `47` |
