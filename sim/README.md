# sim

Pinned toolchain and the model smoke bench. Scope: see the repo README.

- `pdk.json`, `toolchain.json` — pinned gf180mcu open_pdks revision/variant and
  ngspice/python floors. The ngspice floor is 42 (what the dispatch workers run).
- `check_env.sh` — verifies the pins; exits non-zero naming the mismatched
  field. Models resolve from the pinned revision, never from `current`.
- `smoke/` — typical-corner, 27 C, single operating point: 3.3 V NMOS,
  thick-oxide (`*_06v0`; this revision has no `*_05v0`) NMOS and two diodes.

- `gpio-bi_t/` — foundry `gf180mcu_fd_io__bi_t` against the ratified GPIO electrical
  targets across the PVT set (comparison anchor, reference values only); grid goes to
  the batch fleet via `klt sim`. See its README.

## Cold start

    sim/smoke/run.sh                   # exit 0 = all sections loaded and conducting
    sim/smoke/run.sh --bad-model-path  # negative control: must exit non-zero

Each passing run writes `sim/smoke/records/<UTC stamp>/` (netlist, log,
measurements, `record.txt` with PDK revision and ngspice version). Records are
append-only; never edit or delete one. The runner fails on a model/include error
in the log or a missing/zero/non-finite current, not only on the exit code.
