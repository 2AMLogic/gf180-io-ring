# sim/gpio-corners — the drawn GPIO cell against the ratified spec rows

T1 item 5 (tracker #5, issue #18): PVT corner-matrix simulation of `design/gpio.spice` (the
cell from #14) against `spec/io-ring.md` §GPIO electrical targets and §ESD evidence, with
per-row pass/fail and the binding corner recorded. Pre-silicon simulation only: **no cell
here is ESD-rated or qualified.** A row that misses its target is reported as a miss; no
spec row is relaxed.

## Cold start

    sim/gpio-corners/run.sh                    # 21 requests -> `klt sim` batch fleet
    sim/gpio-corners/run.sh --only esd_rail_release   # one request into a new record
    sim/gpio-corners/run.sh --dry-run          # generate and validate every request; no simulation
    sim/gpio-corners/run.sh --resume RECORD    # resubmit only the requests without a report
    sim/gpio-corners/run.sh --probe            # local, ONE corner per deck (typical, 25 C): debug only
    python3 -I sim/gpio-corners/cite.py RECORD manifests/gf180-io-ring.json   # cite it as item 5 evidence

A run writes `records/<UTC stamp>/` (append-only: never edit or delete one):
`record.md` (per-row verdict, worst value, binding corner and supply pair, the quoted
DR-0002 limitation), `rows.json`, `results.tsv` (every point), the generated netlists and
requests, and one `klt/<request>.json` envelope each. It exits non-zero if the env check
fails, a batch submit fails (there is **no local fallback**), or any corner has a missing,
errored or non-finite measurement. A row that misses its target does not fail the run: it is
the result, and the request's envelope reads `fail`, which keeps item 5 unmet.

Then regenerate `manifests/gf180-io-ring.signoff.json` (see `manifests/README.md`).

## What runs

`gen_requests.py` writes one `klt sim` request per (deck, supply mode), each 5 process x
3 temperature = 15 corners, with the spec limit as the measurement's own `limits`.
`DVDD` (nominal -10 % / nominal / +10 %) crossed with core `VDD` (2.97 / 3.3 / 3.63 V) is
nine independent DUT instances in one netlist, not a `corners.params` axis (see "Client and
fleet" below): 135 points per row.

| Request | Analysis | Row(s) |
|---|---|---|
| `vol_*`, `voh_*` | op | VOL / VOH drop at 4 mA (5 V), 2 mA (3.3 V) |
| `edges_*` | tran | rise / fall 10-90 % into 15 pF |
| `xfer_*` | tran (slow PAD ramp up/down) | VIL (Vt-), VIH (Vt+), hysteresis |
| `cap_*` | ac, 1 MHz | PAD capacitance, input mode |
| `pullup_*_nominal`, `pulldown_*_nominal` | op, 1 corner | pull R 25-100 kohm at nominal (typical, 25 C) |
| `pullup_*`, `pulldown_*` | op | the same over the whole grid, report only |
| `esd_pad` | op | pad clamp diodes in the cell, forward drop at 1.33 A and 1 mA |

## Conventions and limits

- **Thick-oxide process corners are not corners.** The 5/6 V devices load their typical
  section in every process corner (DR-0002); `fs`/`sf` are incomplete. Every record quotes it.
- **VIL/VIH convention**: receiver convention (Vt- >= 0.3·DVDD, Vt+ <= 0.7·DVDD); the spec
  text does not state one. `Y` is read at `VDD`/2.
- **ESD assumptions, not spec rows**: 1.33 A is 2 kV / 1.5 kohm HBM arithmetic and the 3.0 V
  forward-drop budget is the one recorded in `design/README.md`. The spec states no number
  for either. Turn-on (forward drop at 1 mA) is reported without a limit.
- **Declared gaps** (manifest `spec_rows`): the core `VDD`-`VSS` rail clamp (no spec'd voltage
  budget for 3.3 V devices) and the `VDD`/`DVDD` coupling (not drawn). They keep item 5 unmet.
- **Rail clamp on the fleet.** `gen_requests.py` always writes the `esd_rail` request: a 1.33 A /
  10 ns-rise pulse into `dvdd_pad.spice`, peak `DVDD` against the 6 V budget (the `*_06v0`
  device class of `design/README.md`; an assumption, not a spec row). Simulated clamp behaviour
  only: no cell is ESD-rated or qualified. The fleet (ngspice-46) fails to bin any single
  instance wider than about 100 um (`could not find a valid modelname`, klayout-tools#1214; it is
  not reproducible on the host): a 600 um clamp FET and a 160 um driver both erred there, so
  wide devices are drawn as `m=` copies of at most 100 um (clamp 48 x 100 um since issue #38, `pfet` driver
  2 x 80 um). The ngspice-42 probe (about 11.7 V) of the earlier record is not evidence.
  The trigger `cap_nmos_06v0` makes the transient fragile ("timestep too small" at some
  corners), so the request carries `.options itl4=1000 gmin=1e-9 reltol=0.01 abstol=1e-10
  rshunt=1e12`; the earlier tighter sets are kept under the record's `superseded/`.

## Client and fleet

The fleet runner image is klt 0.7.0 and refuses a 0.8.x client with
`batch_runner_version_mismatch` (`runner_compatibility: mismatch`): the host's `klt` and
the current release (0.8.0) cannot use the batch backend at all today. `run.sh` therefore
submits through a throwaway `uvx --from klayout-tools==0.7.0 klt` (`KLT_CLIENT`
overrides it). That client has no `--batch-set` or `--report-out`, so requests are
submitted one at a time, and it **silently ignores `corners.params`** (it returns the one
nominal corner), which is the second reason the supply axes are instances rather than a
params axis. `sim` envelopes from it carry no `spec_row` tags, so item 5 row coverage is
asserted by the manifest, not derived. Its provenance block reports the PDK found on the
submitting host (`~/.ciel`, open_pdks `f6eeac7`); the models actually simulated are the ones
`stage_model_inputs` ships from the pinned revision in `sim/toolchain.json`.

Fleet note: a request normally returns in 1-5 minutes; one (`xfer_3v3`) produced no result
for over an hour and was killed and resubmitted, after which it returned in minutes.
`run.sh` itself has no per-request timeout; wrap `KLT_CLIENT` in `timeout` if that matters.
