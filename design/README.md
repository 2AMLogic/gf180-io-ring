# design

## Pad clamp diode sizing (issue #11)

Source: `sim/esd_clamp/records/20261023T172346Z/record.md`. Pre-silicon, simulation
only; the record quotes the spec's ESD-evidence limitation and this note adds no
claim beyond it.

- **Stress current (assumption).** 2 kV / 1.5 kohm = 1.33 A, standard human-body-model
  arithmetic; the spec itself only says "HBM 2 kV, design target only".
- **Budget (assumption).** Forward drop at 1.33 A of at most 3.0 V, half of the
  6.0 V class, leaving the rest for the rail clamp (not chosen yet). The 6.0 V is a
  model-header label; the cards' `bv` (11 / 10.5 V) is reverse breakdown and unused.
- **Result.** Smallest swept area meeting the budget in every diode process section
  and −40/25/125 °C: 178 µm² for both `diode_nd2ps_06v0` (binding: `ss`, −40 °C) and
  `diode_pd2nw_06v0` (binding: `ss`, 125 °C). At 2.5 V / 3.5 V budgets the area is
  237 / 133 µm² (nd2ps) and 237 / 178 µm² (pd2nw).
- **Capacitance.** Both diodes at those areas sum to at most 0.42 pF (0 V, `ss`, 125 °C)
  against the 3 pF added-capacitance target. Reverse leakage at 5.5 V sits at the
  simulator's gmin floor (about 5.5 pA; up to ~29 pA hot), so it is a bound, not a value.
- **Caveats.** 1.33 A is far above the currents the model was characterized at
  (extrapolation, no self-heating); the diode sections do not say anything about
  thick-oxide MOS spread (DR-0002). Areas are on a 10^(1/8) grid, not interpolated.

## Design sources (issue #14, T1 item 1)

xschem schematics (`*.sch`), their symbols (`*.sym`) and the SPICE netlists derived
from them (`*.spice`). Pre-silicon capture only: device sizes are starting points
taken from the spec targets, not results, and no cell here is ESD-rated or
qualified. A single-corner ngspice smoke run (typical, 25 C, 5 V / 3.3 V) loaded
`gpio.spice` and showed the output driver, receiver and enable logic switching the
right way; it is not a recorded result. Verification against the spec is #18, #19
and #20.

| Cell | Schematic | Ports (netlist order) | Content |
|---|---|---|---|
| GPIO pad | `gpio.sch` | `A OE IE PU PD Y PAD DVDD VDD DVSS VSS` | `nfet_06v0`/`pfet_06v0` driver (60 um nfet, 12 fingers / 160 um pfet as 2 x 80 um, `m=2`), Schmitt receiver, pad clamps `diode_pd2nw_06v0` to `DVDD` and `diode_nd2ps_06v0` to `DVSS` at 178 um^2 each (10 x 17.8 um), four 3.3 V to `DVDD` level shifters (`OE`, `A`, `PU`, `PD`), pull-up (`pfet_06v0` L = 1.5 um, W = 1 um) / pull-down (`nfet_06v0` L = 6 um, W = 1 um); `*_03v3` input inverters and `Y` buffer |
| `DVDD` pad | `dvdd_pad.sch` | `DVDD VDD DVSS VSS` | `DVDD`-`DVSS` RC-triggered `nfet_06v0` clamp, 600 um total as 6 x (100 um, 10 fingers) via `m=6` |
| `DVSS` pad | `dvss_pad.sch` | `DVDD VDD DVSS VSS` | same clamp as the `DVDD` pad |
| core-supply pad | `core_pad.sch` | `DVDD VDD DVSS VSS` | `VDD`-`VSS` RC-triggered `nfet_03v3` clamp |
| corner, filler | `corner.sch`, `filler.sch` | `DVDD VDD DVSS VSS` | rail-only, no devices |
| ring | `io_ring.sch` | 8 GPIO (`A0`..`Y7`, `PAD0`..`PAD7`) plus the four rails | 4 corners, 8 GPIO, 4 `DVDD`, 4 `DVSS`, 4 core-supply and 4 filler cells; the core-side ports are left open for the (empty) core |

Rail clamp devices: [DR-0003](../spec/decisions/0003-rail-clamp-devices.md). The cell
set rows are still `pending: sky130-io-ring#2`; if the origin changes one, this
table follows. The `VDD`/`DVDD` cross-domain coupling is not drawn (spec, ESD
network; decision record to follow). Port names are identical in every cell so the
layout and LVS issues (#15, #17) can bind to them. In the supply, corner and filler
cells the rails are ports with no devices attached, standing for continuity by
abutment.

### Regenerate

Netlisting goes through `klt netlist` only (never raw `xschem`). `design/xschemrc`
adds the PDK symbols (`$PDK_ROOT/$PDK`, default `~/.ciel/gf180mcuD`). For each cell
`<c>` in `gpio dvdd_pad dvss_pad core_pad corner filler io_ring`:

    klt netlist --block --rcfile design/xschemrc --pdk gf180mcuD design/<c>.sch -o design/<c>.spice
    klt netlist --check --block --rcfile design/xschemrc --pdk gf180mcuD design/<c>.sch -o design/<c>.spice   # exit 0 = match

The `** sch_path:` header line holds the absolute path of the machine that ran
xschem; `--check` ignores it. Then re-attest item 1 (needs `klt` >= 0.8.0) and
regenerate the verdict of record as described in `manifests/README.md`:

    klt signoff --attest 1 --inventory design/item1-inventory.json -o manifests/evidence/item1.json

Device-family check. Pad side is `*_06v0`; core side is `*_03v3`, except the
receiver's down-shift NOR (`MP_ds*`, `MN_ds*` in `gpio.sch`), which is `*_06v0`
because its inputs swing to `DVDD` while it is supplied from `VDD`:

    grep -ho 'nfet_[0-9a-z]*\|pfet_[0-9a-z]*\|diode_[0-9a-z_]*\|cap_[0-9a-z_]*' design/*.spice | sort | uniq -c
