# sim/gpio-bi_t — foundry `gf180mcu_fd_io__bi_t` against the GPIO electrical targets

Comparison anchor for `spec/io-ring.md` §"GPIO electrical targets" (tracker #5). The
foundry cell is simulated across the §PVT corners; the numbers are **reference values,
not results for this block**, and carry no ESD claim.

## Cold start

    sim/gpio-bi_t/run.sh                          # full grid on the batch fleet
    sim/gpio-bi_t/run.sh --dry-run                # translate, generate, validate; no simulation
    sim/gpio-bi_t/run.sh --negative bad-include   # must exit non-zero
                         # also: bad-model-path | bad-load | bad-measure

A passing run exits 0 and writes `records/<UTC stamp>/` (append-only: never edit or delete
one). It exits non-zero if the env check fails (`sim/check_env.sh`), the cell translation
does not match the PDK's own spice netlist, a batch submit fails (there is **no local
fallback**), or any PVT point has a missing, failed or non-finite measurement.

## What runs

- `cdl2ngspice.py` — translates `gf180mcu_fd_io__bi_t` out of the pinned PDK's CDL
  (`M`→`X`, `$[model]`→`model`, `$W/$L`→`r_width/r_length`, `l/w`→`c_length/c_width`) and
  checks all 210 devices against the PDK's `spice/gf180mcu_fd_io.spice` (same cell,
  already in ngspice form), so the translation is verified rather than trusted.
- `gen_requests.py` — 8 decks × 2 modes × 3 `DVDD` = 48 `klt sim` requests, each
  5 process × 3 temperature = 15 corners: 720 PVT points. With `KLT_SIM_BACKEND=batch` a
  multi-corner request goes to the Spot fleet; the models are shipped with the job
  (`stage_model_inputs`), so the fleet simulates the pinned revision.
- `collect.py` — checks every report, writes `results.tsv` (every point) and `record.md`
  (one row per spec parameter: foundry value at its binding corner next to the target).

| Deck | Analysis | Measures |
|---|---|---|
| `vol`, `voh` | op | VOL / VOH at 4 mA (5 V) and 2 mA (3.3 V) |
| `edges` | tran | 10–90 % rise / 90–10 % fall into 15 pF |
| `xfer_cs0`, `xfer_cs1` | tran (slow PAD ramp up/down) | Vt+, Vt−, hysteresis, `CS`=0/1 |
| `pullup`, `pulldown` | op | equivalent R at PAD = `DVDD`/2 |
| `cap` | ac, 1 MHz | PAD capacitance, input mode |

## Conventions and limits

- **`VDD` = `DVDD`** (foundry convention). The spec holds core `VDD` at 3.3 V with `DVDD` at
  5 V; this bench does not exercise that level-shifter crossing. Stated in every record.
- **Thick-oxide process corners are not corners.** The 5/6 V devices load their typical
  section in every process corner (spec §PVT corners); the record quotes that limitation.
- Pins: `PDRV0=PDRV1=0`, `SL=0`; `CS` is 0 or 1 only in the transfer decks.
- **`DVDD` is split across requests**, not a `corners.params` axis: the fleet worker image
  predates that axis (`params_unsupported_worker`).
- The VIL/VIH rows use the receiver convention stated in the record; the spec does not state one.
