# sim/gpio-corners — the drawn GPIO cell against the ratified spec rows

T1 item 5 (tracker #5, issue #18): PVT corner-matrix simulation of `design/gpio.spice` (the
cell from #14) against `spec/io-ring.md` §GPIO electrical targets and §ESD evidence, with
per-row pass/fail and the binding corner recorded. Pre-silicon simulation only: **no cell
here is ESD-rated or qualified.** A row that misses its target is reported as a miss; no
spec row is relaxed.

## Cold start

    sim/gpio-corners/run.sh                    # 21 requests -> `klt sim` batch fleet
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

## `--probe` records are not evidence

`--probe` writes a `records/<UTC stamp>/` of the same shape as a batch run -- `meta.txt`,
`results.tsv`, `rows.json`, `record.md`, the netlists and requests, one `klt/<request>.json`
each -- so a probe is reproducible and reviewable instead of vanishing into a temp dir. It is
still **not evidence**, in three ways that `record.md` and `meta.txt` both state outright:

- **One corner.** Typical process, 25 C, with all nine (`DVDD`, `VDD`) instances still present
  in the gpio decks. No process or temperature spread, which is where this bench's ESD and
  timing rows are binding.
- **The host's engine, not the fleet's.** `--probe` runs the host `ngspice` and the host-wide
  `klt`, where a batch record is made with the runner image's ngspice-46 through the pinned
  `uvx --from klayout-tools==0.8.0 klt` client. `meta.txt` records both.
- **Mechanically refused as a citation.** The record carries `result=PROBE` in `record.txt` and
  `probe=true` in `meta.txt`, and `cite.py` exits on either without touching the manifest. A
  probe record is structurally citable -- it has the same envelopes -- so this is a check
  rather than a naming convention.

A probe never fails the pass: a deck that errs locally is the thing being debugged, so
`record.txt` carries `probe_rc` and `collect_rc` and the run still exits 0. Records are
append-only like any other: never edit or delete one.

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
| `esd_rail` | tran, 130 ns | `DVDD`-`DVSS` rail clamp **unpowered**: peak `DVDD` under the pulse |
| `esd_rail_release` | tran, 5 us | the same clamp with the rail **powered**: release after the pulse, report only |

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
- **Rail clamp release, rail powered** (`esd_rail_release`). DR-0003 Amendment 1 item 3 records
  release after the pulse and absence of latching as **Not evaluated**: `esd_rail` leaves the
  rail unpowered and stops at 130 ns, inside the 100 ns plateau, so it measures no recovery at
  all. `esd_rail_release` is the same pad cell and the same 1.33 A / 10 ns-rise pulse with
  `DVDD` held at its nominal 5 V through a 50 ohm series resistance, over a 5 us window (about
  ten times DR-0003 decision item 1's "order of 0.5 us" trigger RC design intent), read at
  4.5 us. **Every row is report-only and carries no limit**: the spec states no release
  criterion, and `esd_rail`'s 6 V budget is an assumption about the *unpowered* deck, so
  reusing it here would be inventing a limit. The two decks start from different quiescent
  states and answer different questions - this one is not a second opinion on `esd_rail`'s
  peak, and its own peak row is context, not a verdict. The series resistance and the window
  length are declared bench assumptions (`gen_requests.py` documents how each was chosen), not
  spec rows; the current row is the whole rail's current, clamp plus trigger, not the clamp
  FET's drain current. `record.md` lists what a release criterion would have to state as an
  open question for a decision record. Simulated clamp behaviour only: no cell is ESD-rated or
  qualified. The 15-corner batch run of this deck is #45.

## Client and fleet

The fleet runner image is klt 0.8.0 and `run.sh` submits through a throwaway
`uvx --from klayout-tools==0.8.0 klt` (`KLT_CLIENT` overrides it), so the client and the
runner match. Requests are still submitted one at a time and the supply axes are still
instances rather than a `corners.params` axis; that design is unchanged here. Its
provenance block reports the PDK found on the submitting host (`~/.ciel`, open_pdks
`f6eeac7`); the models actually simulated are the ones `stage_model_inputs` ships from
the pinned revision in `sim/toolchain.json`.

Fleet note: a request normally returns in 1-5 minutes; one (`xfer_3v3`) produced no result
for over an hour and was killed and resubmitted, after which it returned in minutes.
`run.sh` itself has no per-request timeout; wrap `KLT_CLIENT` in `timeout` if that matters.
