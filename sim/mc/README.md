# sim/mc — Monte Carlo evidence for the own-design GPIO (T1 item 6)

`klt yield` evidence for the statistical rows of `spec/io-ring.md` §"GPIO electrical targets":
input thresholds (VIL/VIH), hysteresis, pull-up / pull-down, and VOL / VOH, at 5 V and 3.3 V
`DVDD`. The cell is the block's own `design/gpio.spice`, **not** the foundry `bi_t` (that is
`sim/gpio-bi_t/`, comparison only). Pre-silicon simulation: **no ESD claim**, and the 5/6 V
corner sections carry no process skew (DR-0002 §3), so the spread below comes only from the
library's own statistical hooks, never from invented numbers.

## Model finding (pinned open_pdks `c6d73a3`, variant `gf180mcuD`)

Recorded with the commands that produced it; `$F` is `sm141064.ngspice` from `sim/check_env.sh`.

| Question | Answer | Command |
|---|---|---|
| Defaults off? | `design.ngspice` sets `sw_stat_global = 0`, `sw_stat_mismatch = 0`, `mc_skew = 3`. Every sample is identical unless the netlist turns them on. | `grep -n "sw_stat_global\|sw_stat_mismatch\|mc_skew" $PDK_MODELDIR/design.ngspice` |
| Global hooks reach the 06v0 FETs? | Yes: 17 `nfet_06v0`/`pfet_06v0` parameter lines carry `*sw_stat_global*mc_skew` (e.g. `nfet_06v0_vth0='(8e-3*mc_sig_vth+28e-3*mc_sig_vthN)*sw_stat_global*mc_skew'`). | `grep -E "(nfet\|pfet)_06v0" $F \| grep -c sw_stat_global` |
| Mismatch reaches the 06v0 FETs? | Yes: the `nfet_06v0` and `pfet_06v0` subcircuits instantiate `m0 ... delvto='mis_vth*sw_stat_mismatch' mulu0='1-mis_k*sw_stat_mismatch'`, with `mis_vth = agauss(0, var_vth, 1)` (Pelgrom `par_vth/sqrt(area)`). `nfet_06v0` has `par_k = 0` (V<sub>th</sub> mismatch only); `pfet_06v0` has both. | `grep -n "^.subckt \(n\|p\)fet_06v0 " -A32 $F` |
| Pull devices? | The pull-up/pull-down are `pfet_06v0`/`nfet_06v0` channels (`XMP_pu`, `XMN_pd`), **not** poly resistors, so they see the MOS hooks above. The cell has no resistor, so the known gf180mcu resistor-mismatch gap (`mis_r` ships disabled) does not touch these rows. | `grep -n "XMP_pu\|XMN_pd" design/gpio.spice` |

`klt sim` reports `family_mismatch` for the cell as `other`/`active: null` (it classifies the
hierarchy, not the underlying devices); that is the tool's "not independently verified", not
a finding about the devices. The campaign proves the hooks are live empirically instead:
`collect.py` refuses any sample set with zero spread, and `run.sh --negative nostat` shows the
guard firing when the switches are left at their default 0.

## Campaign (reduced, by design)

A full 5 × 3 × 3 corner × MC grid is not run. Each request is one corner with `monte_carlo`
`n = 300`, `seed = 20261027`, `vary = both`:

- **Process**: typical only. The 5/6 V devices load their typical section in every corner
  (spec §PVT corners, DR-0002 §3), so ff/ss/fs/sf would repeat typical for the devices under
  test; the diode/resistor/MOS-cap sections are typical too.
- **Temperature**: −40 / 25 / 125 °C for thresholds, hysteresis, VOL, VOH. Pull rows are
  "at nominal" in the spec, so 25 °C only.
- **Supply**: nominal `DVDD` (5.0 V and 3.3 V), core `VDD` = 3.3 V. The supply-corner spread is
  covered by the PVT records, not repeated here.
- 22 requests × 300 samples = 6600 units, all through `klt sim --backend batch`.

Threshold resolution: the receiver flips within one timestep, so Vt± are interpolated on the
time grid. The ramp is 5 V in 100 µs with `tmax` 0.1 µs, i.e. 5 mV of grid, which is far below the
margins to the limits but is the floor of the measured spread (reported spreads below ~2 mV are
grid-limited, not device-limited).

Spec limits ride in each request (`measurements[].limits`, `target_yield` 0.98 (a campaign choice: the spec states no yield; with zero failures n = 300 gives a Clopper-Pearson lower bound of 0.9878, so 0.99 would need n >= 369)). Receiver
convention (as in `sim/gpio-bi_t`, the spec does not state one): VIL row = lower trip
Vt− ≥ 0.3·`DVDD`; VIH row = upper trip Vt+ ≤ 0.7·`DVDD`.

## Cold start

    KLT_YIELD=<klt with klt_yield_native> sim/mc/run.sh      # KLT_SIM defaults to uvx klayout-tools==0.8.0
    sim/mc/run.sh --dry-run                  # generate, `klt sim --dry-run`, check seed determinism
    sim/mc/run.sh --negative rx|pull|nostat  # must exit non-zero
    sim/mc/run.sh --resume records/<stamp>   # resubmit only the requests without a report

Exit 0: all rows meet their target yield. Exit 3: data valid but a row misses its limit (the
record says which; the spec is not relaxed). Exit 1: invalid data or a harness failure.
Records under `records/<UTC stamp>/` are append-only.

### Tool constraints met while building this

- **Two klt installs.** The Spot fleet runner image is klt 0.8.0 and refuses a different client
  (`batch_runner_version_mismatch`), so `KLT_SIM` defaults to a throwaway `uvx --from
  klayout-tools==0.8.0 klt`. `klt yield` needs the `klt_yield_native` extension, which is not on PyPI
  (`klt-yield-native` unresolvable), so `KLT_YIELD` is a venv built from a klayout-tools checkout
  with `maturin develop` (`native/yield`; the record used `klt 0.8.1.dev61`). Neither is the host-wide klt.
- **OpenMP oversubscription on the fleet.** The runner does not pin `OMP_NUM_THREADS`; with
  several units per instance a transient that takes 0.4 s alone takes minutes (8 identical units:
  all timed out at 100 s), while operating-point decks are unaffected. Each netlist carries
  `.control` / `set num_threads=1` / `.endc`, which restores 0.4 s per unit. (`.options
  num_threads` and `options.threads_per_worker` had no effect on the runner.)
- **Fleet instance cap.** `BATCH_MAX_CONCURRENT_INSTANCES=8` is shared by every sweep; a refused
  launch is retried by `run.sh` with a fixed backoff. Nothing falls back to local ngspice.

## Negative controls

`--negative rx` shrinks the Schmitt feedback devices (`XMN_st3`/`XMP_st3`, `W` → 0.3 µm) and
`--negative pull` cuts the pull channel lengths to 1/4 (floored at 0.7 µm), each with the **same seed** and request
shape as the nominal campaign; `collect.py` pairs them with `klt yield-samples` and requires
`negative_control.verdict = detected` for `hyst` and `r_pulldown`. The pull-up has no control of its own: the pull-down control exercises the same
flow and the pull-up rows are graded against their limits directly. `--negative nostat` leaves
`sw_stat_*` at 0 and must be refused for zero variance. Determinism: `--dry-run` shows
identical per-sample seeds on regeneration and between nominal and known-bad requests, and
each record resubmits `pulldown_5v_25C` and requires bit-identical values.
- **Out-of-bin length fails the whole job.** A negative-control deck with `L` below the 06v0 model
  bin (0.375 µm) made the fleet job fail at once with no per-unit result, so `--negative pull`
  floors the shrunk length at 0.7 µm.

## Results

Record `records/20261028T232951Z/` (committed, append-only; `meta.txt` has the pins). Design under
test: `design/gpio.spice` at repo commit `6db410d`; `gpio.spice.nominal` in the record is the exact
netlist. `klt sim` client 0.8.0 on the batch fleet, `klt yield` over every report.

- 22 requests × 300 samples, seed 20261027, `vary = both`, typical process, −40/25/125 °C for
  thresholds, hysteresis, VOL and VOH, 25 °C for the pulls, at 5 V and 3.3 V `DVDD`.
- All 34 measurement rows meet target yield 0.98 with `sample_size = sufficient` (Clopper-Pearson
  lower bound 0.988 at zero failures); `table.md` lists mean, spread, Cpk per row.
- Negative controls: the mis-sized receiver and the shortened pull devices, same seed, are
  `detected` for hysteresis (6 corners) and r_pulldown (2 modes). `--negative nostat` is refused
  for zero variance. Resubmitting `pulldown_5v_25C` gives bit-identical samples.
- The earlier record `records/20261027T050850Z/` was run on the previous `gpio.spice` (pull-up
  `L = 8 µm`, driver `W = 40 µm`), where the pull-up (183 kΩ at 5 V, 307 kΩ at 3.3 V) and the
  5 V/125 °C VOH row missed their limits. The cell was resized on `main` afterwards; that record
  is kept as history and is not cited.
- Spread is small (σ of a few mV on thresholds, below the ~5 mV time-grid floor on some rows): the
  library's 06v0 statistical hooks are narrow. That is the PDK's number, not an invented skew, and
  no 5/6 V process-corner skew is applied (DR-0002 §3).
- Pre-silicon simulation only: no ESD claim, and nothing here rates or qualifies a cell.
