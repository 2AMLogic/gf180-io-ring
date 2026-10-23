# gf180mcu_fd_io__bi_t versus the ratified GPIO electrical targets

Reference values for the foundry cell, not results for this block. No ESD claim.

- date (UTC): 20261023T173526Z (completed by --resume: requests refused for fleet capacity were resubmitted; see set-report.resume-*.json)
- open_pdks revision (pinned, sim/toolchain.json): `c6d73a35f524070e85faff4a6a9eef49553ebc2b`, variant `gf180mcuD`
- ngspice on the submitting host: `ngspice-46` (the fleet's own is per job below)
- klt: `klt 0.7.1.dev2517+g6bb7cf233677`; backend: batch (`klt sim --batch-set`)
- repo commit: `9d1fc2542af5509a09616829b5953c2c362ff7f1`
- cell netlist: `bi_t.sp`, translated from the pinned CDL by cdl2ngspice.py and cross-checked
  device by device against the PDK's own spice netlist
- models staged with each job (`stage_model_inputs`): the pinned revision's sm141064.ngspice

## Supply convention

Foundry convention: `VDD` = `DVDD` (every logic device in `bi_t` is thick-oxide, so this is electrically consistent). This departs from the ratified spec, which holds core `VDD` at 3.3 V while `DVDD` is 5 V; the level-shifter crossing is NOT exercised by this record.

## Known limitation (quoted from spec/io-ring.md, section PVT corners)

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

## Grid

48 requests, 720 PVT points: process (typical, ff, ss, fs, sf) x -40/25/125 C x DVDD (4.5/5/5.5 V in 5 V mode; 2.97/3.3/3.63 V in 3.3 V mode). Pins: PDRV0=PDRV1=0, SL=0, PU=PD=0 unless the row says otherwise. Diode, resistor and MOS-capacitor sections follow typical/ff/ss; fs and sf use typical passives.

## Comparison

| Mode | Parameter | Target | Foundry (binding corner) | Binding | Corner | Meets target |
|---|---|---|---|---|---|---|
| 5v | VOL at 4 mA | <= 0.4 V | 0.3791 V | max | `ss/novdd/125C` | yes |
| 5v | VOH at 4 mA (DVDD - VOH) | <= 0.5 V | 0.5967 V | max drop | `ss/novdd/125C` | NO |
| 5v | rise 10-90 % into 15 pF | <= 5 ns | 7.658 ns | max | `ss/novdd/125C` | NO |
| 5v | fall 90-10 % into 15 pF | <= 5 ns | 5.789 ns | max | `ss/novdd/125C` | NO |
| 5v | VIL as lower trip Vt-, CS=0 | >= 0.3*DVDD (reads low up to 0.3*DVDD) | 0.296*DVDD | min | `fs/novdd/125C` | NO |
| 5v | VIH as upper trip Vt+, CS=0 | <= 0.7*DVDD (reads high from 0.7*DVDD) | 0.342*DVDD | max | `sf/novdd/-40C` | yes |
| 5v | hysteresis, CS=0 | >= 0.4 V | -0.002421 V | min | `fs/novdd/125C` | NO |
| 5v | VIL as lower trip Vt-, CS=1 | >= 0.3*DVDD (reads low up to 0.3*DVDD) | 0.251*DVDD | min | `fs/novdd/125C` | NO |
| 5v | VIH as upper trip Vt+, CS=1 | <= 0.7*DVDD (reads high from 0.7*DVDD) | 0.386*DVDD | max | `sf/novdd/-40C` | yes |
| 5v | hysteresis, CS=1 | >= 0.4 V | 0.4348 V | min | `ff/novdd/-40C` | yes |
| 5v | pull-up equivalent R (PAD at DVDD/2) | 25-100 kohm at nominal | 132 kohm nominal; 105.9 kohm .. 159.3 kohm over the grid | nominal | `typical/novdd/25C` | NO |
| 5v | pull-down equivalent R (PAD at DVDD/2) | 25-100 kohm at nominal | 130.4 kohm nominal; 104.6 kohm .. 157.3 kohm over the grid | nominal | `typical/novdd/25C` | NO |
| 5v | PAD capacitance, input mode, 1 MHz | <= 3 pF | 2.246 pF | max | `ss/novdd/125C` | yes |
| 3v3 | VOL at 2 mA | <= 0.4 V | 0.2676 V | max | `ss/novdd/125C` | yes |
| 3v3 | VOH at 2 mA (DVDD - VOH) | <= 0.4 V | 0.4609 V | max drop | `ss/novdd/125C` | NO |
| 3v3 | rise 10-90 % into 15 pF | <= 8 ns | 12.2 ns | max | `ss/novdd/125C` | NO |
| 3v3 | fall 90-10 % into 15 pF | <= 8 ns | 8.368 ns | max | `ss/novdd/125C` | NO |
| 3v3 | VIL as lower trip Vt-, CS=0 | >= 0.3*DVDD (reads low up to 0.3*DVDD) | 0.325*DVDD | min | `fs/novdd/125C` | yes |
| 3v3 | VIH as upper trip Vt+, CS=0 | <= 0.7*DVDD (reads high from 0.7*DVDD) | 0.396*DVDD | max | `sf/novdd/-40C` | yes |
| 3v3 | hysteresis, CS=0 | >= 0.25 V | -0.001596 V | min | `ff/novdd/-40C` | NO |
| 3v3 | VIL as lower trip Vt-, CS=1 | >= 0.3*DVDD (reads low up to 0.3*DVDD) | 0.281*DVDD | min | `fs/novdd/125C` | NO |
| 3v3 | VIH as upper trip Vt+, CS=1 | <= 0.7*DVDD (reads high from 0.7*DVDD) | 0.466*DVDD | max | `ss/novdd/-40C` | yes |
| 3v3 | hysteresis, CS=1 | >= 0.25 V | 0.3571 V | min | `ff/novdd/125C` | yes |
| 3v3 | pull-up equivalent R (PAD at DVDD/2) | 25-100 kohm at nominal | 133.3 kohm nominal; 106.7 kohm .. 162.1 kohm over the grid | nominal | `typical/novdd/25C` | NO |
| 3v3 | pull-down equivalent R (PAD at DVDD/2) | 25-100 kohm at nominal | 130.9 kohm nominal; 104.9 kohm .. 158 kohm over the grid | nominal | `typical/novdd/25C` | NO |
| 3v3 | PAD capacitance, input mode, 1 MHz | <= 3 pF | 2.45 pF | max | `ss/novdd/125C` | yes |

Input thresholds: VIL/VIH are read from a slow PAD ramp up then down (Vt+ at the rising crossing of Y = DVDD/2, Vt- at the falling one). The rows use the receiver convention (reads low up to 0.3*DVDD means Vt- >= 0.3*DVDD; reads high from 0.7*DVDD means Vt+ <= 0.7*DVDD). The spec text does not state the convention; the raw Vt+/Vt- are in results.tsv. Hysteresis is compared in the Schmitt setting (CS=1); CS=0 is listed as measured.

## Jobs

- `cap_3v3_2v97`: job `klt-sim-ff2b789cd54d`, engine `46`, host `worker`
- `cap_3v3_3v30`: job `klt-sim-7eda33a21094`, engine `46`, host `worker`
- `cap_3v3_3v63`: job `klt-sim-cd70c2744b61`, engine `46`, host `worker`
- `cap_5v_4v50`: job `klt-sim-ebe69f821d65`, engine `46`, host `worker`
- `cap_5v_5v00`: job `klt-sim-6117b78c1356`, engine `46`, host `worker`
- `cap_5v_5v50`: job `klt-sim-9023f35ac10c`, engine `46`, host `worker`
- `edges_3v3_2v97`: job `klt-sim-663a4c214517`, engine `46`, host `worker`
- `edges_3v3_3v30`: job `klt-sim-8760795befd9`, engine `46`, host `worker`
- `edges_3v3_3v63`: job `klt-sim-ac7fbfaa9ce2`, engine `46`, host `worker`
- `edges_5v_4v50`: job `klt-sim-e7faea48112c`, engine `46`, host `worker`
- `edges_5v_5v00`: job `klt-sim-84d3047b532f`, engine `46`, host `worker`
- `edges_5v_5v50`: job `klt-sim-f215890ae83b`, engine `46`, host `worker`
- `pulldown_3v3_2v97`: job `klt-sim-b6cd8486e72b`, engine `46`, host `worker`
- `pulldown_3v3_3v30`: job `klt-sim-0b3ca637bde1`, engine `46`, host `worker`
- `pulldown_3v3_3v63`: job `klt-sim-5ed7518b0b0d`, engine `46`, host `worker`
- `pulldown_5v_4v50`: job `klt-sim-e501ab67f748`, engine `46`, host `worker`
- `pulldown_5v_5v00`: job `klt-sim-1d359954425d`, engine `46`, host `worker`
- `pulldown_5v_5v50`: job `klt-sim-ba007df656f7`, engine `46`, host `worker`
- `pullup_3v3_2v97`: job `klt-sim-9167103c6380`, engine `46`, host `worker`
- `pullup_3v3_3v30`: job `klt-sim-af0094713d83`, engine `46`, host `worker`
- `pullup_3v3_3v63`: job `klt-sim-8821ada50194`, engine `46`, host `worker`
- `pullup_5v_4v50`: job `klt-sim-370559f20d32`, engine `46`, host `worker`
- `pullup_5v_5v00`: job `klt-sim-724ab9477c19`, engine `46`, host `worker`
- `pullup_5v_5v50`: job `klt-sim-ea7a901cb8a1`, engine `46`, host `worker`
- `voh_3v3_2v97`: job `klt-sim-1bc8f9f8b485`, engine `46`, host `worker`
- `voh_3v3_3v30`: job `klt-sim-7d303f276914`, engine `46`, host `worker`
- `voh_3v3_3v63`: job `klt-sim-90f61f87df4a`, engine `46`, host `worker`
- `voh_5v_4v50`: job `klt-sim-8d85aebf098e`, engine `46`, host `worker`
- `voh_5v_5v00`: job `klt-sim-e869721dfb50`, engine `46`, host `worker`
- `voh_5v_5v50`: job `klt-sim-cb9322d1d0a0`, engine `46`, host `worker`
- `vol_3v3_2v97`: job `klt-sim-915f000a4a5d`, engine `46`, host `worker`
- `vol_3v3_3v30`: job `klt-sim-6b82624f42ac`, engine `46`, host `worker`
- `vol_3v3_3v63`: job `klt-sim-d41e9eadbe2e`, engine `46`, host `worker`
- `vol_5v_4v50`: job `klt-sim-eb1baa5dc2db`, engine `46`, host `worker`
- `vol_5v_5v00`: job `klt-sim-883e19cbf295`, engine `46`, host `worker`
- `vol_5v_5v50`: job `klt-sim-9e6c3dfd010c`, engine `46`, host `worker`
- `xfer_cs0_3v3_2v97`: job `klt-sim-7191b8ffd7cb`, engine `46`, host `worker`
- `xfer_cs0_3v3_3v30`: job `klt-sim-50a5eead13c9`, engine `46`, host `worker`
- `xfer_cs0_3v3_3v63`: job `klt-sim-1029d69fb750`, engine `46`, host `worker`
- `xfer_cs0_5v_4v50`: job `klt-sim-3df48f889203`, engine `46`, host `worker`
- `xfer_cs0_5v_5v00`: job `klt-sim-f7c76f328a5d`, engine `46`, host `worker`
- `xfer_cs0_5v_5v50`: job `klt-sim-60648a3b44b2`, engine `46`, host `worker`
- `xfer_cs1_3v3_2v97`: job `klt-sim-5e443ea9f85d`, engine `46`, host `worker`
- `xfer_cs1_3v3_3v30`: job `klt-sim-f2240b17ccaf`, engine `46`, host `worker`
- `xfer_cs1_3v3_3v63`: job `klt-sim-2c03a9834d7c`, engine `46`, host `worker`
- `xfer_cs1_5v_4v50`: job `klt-sim-cb29a70d1a5b`, engine `46`, host `worker`
- `xfer_cs1_5v_5v00`: job `klt-sim-a1a0104f8e63`, engine `46`, host `worker`
- `xfer_cs1_5v_5v50`: job `klt-sim-28d19cec69ef`, engine `46`, host `worker`
