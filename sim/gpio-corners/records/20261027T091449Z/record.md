# gpio cell (design/gpio.spice) versus the ratified GPIO electrical targets

Pre-silicon simulation of the drawn cell across the DR-0002 PVT set. Results are measurements, not ratings: no cell is ESD-rated or qualified, and the ESD rows below are simulated clamp behaviour only.

- date (UTC): 20261027T091449Z
- open_pdks revision (pinned, sim/toolchain.json): `c6d73a35f524070e85faff4a6a9eef49553ebc2b`, variant `gf180mcuD`
- ngspice on the submitting host: `ngspice-46` (the fleet's own is per request below)
- klt client: `klt 0.7.0`; backend: batch (one `klt sim` request at a time)
- repo commit: `4789d4538941fa67d3e5dd8b4cdf100b9d3e00b9`; DUT: `design/gpio.spice`, `design/dvdd_pad.spice`
- models staged with each job (`stage_model_inputs`): the pinned revision's sm141064.ngspice

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

Process (typical, ff, ss, fs, sf) x -40/25/125 C = 15 corners per request; `DVDD` nominal -10 % / nominal / +10 % (4.5/5/5.5 V in 5 V mode, 2.97/3.3/3.63 V in 3.3 V mode) crossed with core `VDD` 2.97/3.3/3.63 V, as nine independent DUT instances per netlist: 135 points per row (the `*_nominal` requests are one corner: typical, 25 C, nominal `DVDD`, `VDD` 3.3 V). Pins not named by a deck are 0; core-side inputs swing 0..`VDD`. Diode, resistor and MOS-capacitor sections follow typical/ff/ss; fs and sf use typical passives.

## Per-row verdict

A row passes only if every point of the grid is within its target. The binding point is the one with the least margin (or the extreme value for report-only rows).

| Row | Parameter | Target | Worst | Binding corner | Binding supply | Meets target | Failing points | Request |
|---|---|---|---|---|---|---|---|---|
| cap_3v3 | PAD capacitance, input mode, 1 MHz | <= 3 pF | 0.4266 pF | `ss/novdd/125C` | DVDD 2.97 V, VDD 2.97 V | yes | 0/135 | cap_3v3 |
| cap_5v | PAD capacitance, input mode, 1 MHz | <= 3 pF | 0.4051 pF | `ss/novdd/125C` | DVDD 5.5 V, VDD 2.97 V | yes | 0/135 | cap_5v |
| fall_3v3 | fall 90-10 % into 15 pF | <= 8 ns | 6.146 ns | `ss/novdd/125C` | DVDD 2.97 V, VDD 2.97 V | yes | 0/135 | edges_3v3 |
| rise_3v3 | rise 10-90 % into 15 pF | <= 8 ns | 6.485 ns | `ss/novdd/125C` | DVDD 2.97 V, VDD 3.3 V | yes | 0/135 | edges_3v3 |
| fall_5v | fall 90-10 % into 15 pF | <= 5 ns | 4.384 ns | `ss/novdd/125C` | DVDD 4.5 V, VDD 2.97 V | yes | 0/135 | edges_5v |
| rise_5v | rise 10-90 % into 15 pF | <= 5 ns | 4.153 ns | `ss/novdd/125C` | DVDD 4.5 V, VDD 3.63 V | yes | 0/135 | edges_5v |
| esd_pad_dn | pad clamp from DVSS, forward drop at the 1.33 A stress current | <= 3 V | 1.283 V | `ss/novdd/-40C` | - | yes | 0/15 | esd_pad |
| esd_pad_up | pad clamp to DVDD, forward drop at the 1.33 A stress current | <= 3 V | 1.149 V | `sf/novdd/-40C` | - | yes | 0/15 | esd_pad |
| esd_rail | DVDD-DVSS rail clamp, peak DVDD under a 1.33 A / 10 ns-rise pulse | <= 6 V | 5.39 V | `ss/novdd/125C` | - | yes | 0/15 | esd_rail |
| pulldown_3v3 | pull-down equivalent R, PAD at DVDD/2 | report only | 84.28 kohm | `ss/novdd/125C` | DVDD 2.97 V, VDD 2.97 V | n/a | 0/135 | pulldown_3v3 |
| pulldown_3v3_nominal | pull-down equivalent R, PAD at DVDD/2 | >= 25 kohm and <= 100 kohm | 43 kohm | `typical/novdd/25C` | DVDD 3.3 V, VDD 3.3 V | yes | 0/1 | pulldown_3v3_nominal |
| pulldown_5v | pull-down equivalent R, PAD at DVDD/2 | report only | 54.48 kohm | `ss/novdd/125C` | DVDD 4.5 V, VDD 2.97 V | n/a | 0/135 | pulldown_5v |
| pulldown_5v_nominal | pull-down equivalent R, PAD at DVDD/2 | >= 25 kohm and <= 100 kohm | 28.92 kohm | `typical/novdd/25C` | DVDD 5.0 V, VDD 3.3 V | yes | 0/1 | pulldown_5v_nominal |
| pullup_3v3 | pull-up equivalent R, PAD at DVDD/2 | report only | 103.1 kohm | `ss/novdd/125C` | DVDD 2.97 V, VDD 2.97 V | n/a | 0/135 | pullup_3v3 |
| pullup_3v3_nominal | pull-up equivalent R, PAD at DVDD/2 | >= 25 kohm and <= 100 kohm | 55.34 kohm | `typical/novdd/25C` | DVDD 3.3 V, VDD 3.3 V | yes | 0/1 | pullup_3v3_nominal |
| pullup_5v | pull-up equivalent R, PAD at DVDD/2 | report only | 60.02 kohm | `ss/novdd/125C` | DVDD 4.5 V, VDD 2.97 V | n/a | 0/135 | pullup_5v |
| pullup_5v_nominal | pull-up equivalent R, PAD at DVDD/2 | >= 25 kohm and <= 100 kohm | 34.78 kohm | `typical/novdd/25C` | DVDD 5.0 V, VDD 3.3 V | yes | 0/1 | pullup_5v_nominal |
| voh_3v3 | VOH drop, DVDD - VOH, at the spec load | <= 0.4 V | 0.2517 V | `ss/novdd/125C` | DVDD 2.97 V, VDD 2.97 V | yes | 0/135 | voh_3v3 |
| voh_5v | VOH drop, DVDD - VOH, at the spec load | <= 0.5 V | 0.3294 V | `ss/novdd/125C` | DVDD 4.5 V, VDD 2.97 V | yes | 0/135 | voh_5v |
| vol_3v3 | VOL at the spec load | <= 0.4 V | 0.1956 V | `ss/novdd/125C` | DVDD 2.97 V, VDD 2.97 V | yes | 0/135 | vol_3v3 |
| vol_5v | VOL at the spec load | <= 0.4 V | 0.2793 V | `ss/novdd/125C` | DVDD 4.5 V, VDD 2.97 V | yes | 0/135 | vol_5v |
| hyst_3v3 | hysteresis Vt+ - Vt- | >= 0.25 V | 0.4512 V | `ff/novdd/125C` | DVDD 2.97 V, VDD 2.97 V | yes | 0/135 | xfer_3v3 |
| vil_3v3 | VIL as lower trip Vt- (reads low up to the limit) | >= 0.891 V | 1.024 V | `fs/novdd/-40C` | DVDD 2.97 V, VDD 2.97 V | yes | 0/135 | xfer_3v3 |
| vih_3v3 | VIH as upper trip Vt+ (reads high from the limit) | <= 2.079 V | 1.764 V | `sf/novdd/-40C` | DVDD 2.97 V, VDD 3.63 V | yes | 0/135 | xfer_3v3 |
| hyst_5v | hysteresis Vt+ - Vt- | >= 0.4 V | 0.5847 V | `ff/novdd/125C` | DVDD 4.5 V, VDD 3.63 V | yes | 0/135 | xfer_5v |
| vil_5v | VIL as lower trip Vt- (reads low up to the limit) | >= 1.35 V | 1.615 V | `fs/novdd/125C` | DVDD 4.5 V, VDD 2.97 V | yes | 0/135 | xfer_5v |
| vih_5v | VIH as upper trip Vt+ (reads high from the limit) | <= 3.15 V | 2.547 V | `sf/novdd/-40C` | DVDD 4.5 V, VDD 2.97 V | yes | 0/135 | xfer_5v |

## Reading the rows

- **Input thresholds.** VIL/VIH use the receiver convention: Vt- >= 0.3*`DVDD` and Vt+ <= 0.7*`DVDD`, read from a slow PAD ramp up then down at the point where `Y` crosses `VDD`/2. The spec text does not state a convention; the raw Vt+/Vt- are in results.tsv.
- **Pull resistance** is a nominal-point row: the `*_nominal` requests (typical, 25 C, nominal `DVDD`) carry the 25-100 kohm limit; the full-grid `pullup_*`/`pulldown_*` requests are report-only context.
- **ESD pad clamps.** The cell is unpowered (every rail at 0 V) and a current source forces 1.33 A (2 kV / 1.5 kohm, the HBM arithmetic of design/README.md) into PAD towards `DVDD` (`diode_pd2nw_06v0`) and out of PAD from `DVSS` (`diode_nd2ps_06v0`). The spec states no forward-drop number; the 3.0 V budget is the assumption recorded in design/README.md (half the 6.0 V device class) and is not a spec row. Turn-on voltage at 1 mA is reported (`vf_*_1ma`, results.tsv), without a limit.
- **ESD rail clamp (simulated transient).** The `DVDD` pad cell (RC-triggered `nfet_06v0`, DR-0003 as amended; 48 x 100 um via `m=48`, trigger-inverter `pfet` 10 x 10 um via `m=10`, since one wider instance does not bin on the fleet) is unpowered; a 1.33 A / 10 ns-rise pulse is forced into `DVDD`. The 6 V peak limit is the `*_06v0` device class, an assumption and not a spec row. Simulated clamp behaviour only: nothing here is an ESD rating.
- **Not covered (declared gaps).** The core `VDD`-`VSS` rail clamp (3.3 V devices; the spec gives no voltage budget for it) and the `VDD`/`DVDD` cross-domain coupling (spec: decision record to follow) are not simulated here.

## Requests

| Request | Status | Job | Runner klt | ngspice |
|---|---|---|---|---|
| `vol_5v` | pass | `klt-sim-36a5276372b2` | `0.7.0` | `46` |
| `vol_3v3` | pass | `klt-sim-e7dfa446eaf0` | `0.7.0` | `46` |
| `voh_5v` | pass | `klt-sim-f98e309fa68d` | `0.7.0` | `46` |
| `voh_3v3` | pass | `klt-sim-ec8901513416` | `0.7.0` | `46` |
| `edges_5v` | pass | `klt-sim-bdfdc118a9b9` | `0.7.0` | `46` |
| `edges_3v3` | pass | `klt-sim-8bc606bd552d` | `0.7.0` | `46` |
| `xfer_5v` | pass | `klt-sim-b634d6218bf1` | `0.7.0` | `46` |
| `xfer_3v3` | pass | `klt-sim-2c82dfff54fd` | `0.7.0` | `46` |
| `pullup_5v` | pass | `klt-sim-f39446122362` | `0.7.0` | `46` |
| `pullup_3v3` | pass | `klt-sim-d4c71056ab04` | `0.7.0` | `46` |
| `pulldown_5v` | pass | `klt-sim-6459b5ce71ac` | `0.7.0` | `46` |
| `pulldown_3v3` | pass | `klt-sim-c372f3c71fd7` | `0.7.0` | `46` |
| `cap_5v` | pass | `klt-sim-322ca0dbe5b1` | `0.7.0` | `46` |
| `cap_3v3` | pass | `klt-sim-b40ab288c100` | `0.7.0` | `46` |
| `esd_pad` | pass | `klt-sim-1949f9d5da86` | `0.7.0` | `46` |
| `esd_rail` | pass | `klt-sim-bc92101352b6` | `0.7.0` | `46` |
| `pullup_5v_nominal` | pass | `klt-sim-2934c8de7011` | `0.7.0` | `46` |
| `pullup_3v3_nominal` | pass | `klt-sim-a3f42a64c35a` | `0.7.0` | `46` |
| `pulldown_5v_nominal` | pass | `klt-sim-9f26ccc23909` | `0.7.0` | `46` |
| `pulldown_3v3_nominal` | pass | `klt-sim-264a4fb57137` | `0.7.0` | `46` |
