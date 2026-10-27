# gpio-pex probe, 2026-10-27 (item 7 NOT met)

A local single-corner probe (typical, 25 C, deck `vol_5v`; one corner is the only thing this
host may run locally). **No grid was run and no batch job was submitted**: the probe shows the
extracted netlist cannot be bound to the schematic DUT, so every delta row errors, on any
backend. Running the 19-request grid on the fleet would only reproduce nine errored rows per request.

- klt client `0.7.0` (the fleet runner's version; `klt pex` and the `body_bias` block exist in it).
  `klt 0.8.0` has the same verb and block; its `--extract-only` extraction gives the same netlist
  topology (`extract-only-0.8.0.json`).
- Layout `layout/gf180_io_ring.gds`, `--top gpio`, deck `gf180mcu`, PDK root pinned with `--pdk-root`
  (without it klt warns that two installs provide `gf180mcuD` and reads `~/.ciel`; the 0.8.0
  extract-only run without the pin bound every MOS to the default flavour `nfet`/`pfet`; with the pin
  the extracted devices are `nfet_03v3`, `nfet_06v0`, `pfet_03v3`, `pfet_06v0`, `diode_nd2ps_06v0`,
  `diode_pd2nw_06v0`: 76 devices, 33 nets).
- Reports: `pex-vol_5v.json` (probe), `extracted-gpio.spice`, `extract-only-0.8.0.json`.

## Result

| check | outcome |
|---|---|
| `body_bias` | `status: biased`, `unbiased_device_count: 0`, `unbiased_nets: []`, `unbiased_pmos_body_nets: []` (no anonymous body nets) |
| delta rows | 9 of 9 `error`, code `pin_count_mismatch` (extracted side) |
| `model_mismatch` | fires, but its reference side parsed the schematic's `W='...'` expressions as model names (`'`, `W'`); a scan artifact, the extracted model set is the expected six |

`pin_count_mismatch`: the extracted `.SUBCKT gpio` has 10 pins
(`A DVDD DVSS|VSS IE OE PAD PD PU VDD Y`); the schematic declares 11 (`DVSS` and `VSS` separately).
This is the substrate join item 4 needed (`manifests/evidence/item4.md`, hint `short_nets`): the
layout ties `DVSS` and `VSS` through the shared p-substrate, so extraction reports one net
`DVSS|VSS`. `klt pex` re-runs the testbench's unmodified instantiation line on both legs, and
`--pins ... --rename-declared-pins` cannot split a net whose two names are both declared (0.7.0 has
no such flag). Fixing it means changing the layout (deep-Nwell isolation) or the schematic
interface, both out of scope for this issue ("do not edit the layout or netlists to make it clean").

## Acceptance criteria

1. A `klt pex` report with every row's delta explained: **not met**; no row produced an extracted value.
2. `body_bias` shows no anonymous body nets: **met in this probe** (`biased`, nothing unbiased).
3. Manifest cites item 7 and the verdict reads `met`: **not done**; item 7 stays `unmet`.

## Next

Blocked on a design decision (split `DVSS`/`VSS` in the layout, or declare the merged-net interface
for the schematic leg) and on gf180-io-ring#40 (design decision) and 2AMLogic/klayout-tools#4383 (tool gaps). Re-run `sim/gpio-pex/run.sh` on the
batch fleet once the DUT interfaces match. Thick-oxide process corners are not corners (DR-0002);
this applies to the full run as it does to item 5. Nothing here is ESD-rated or qualified.
