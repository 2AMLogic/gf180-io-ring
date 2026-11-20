# gpio-pex

T1 item 7 (post-layout verification): the item-5 GPIO spec suite re-run on the netlist extracted
from `layout/gf180_io_ring.gds`, reported by `klt pex` as a per-corner, per-row
schematic-vs-extracted delta. **Status: not met.** See the latest record's `record.md`.
Blocker (#61, `records/20261109T2200Z-probe-klt-diode-fix/record.md`): the batch run needs a runner image whose klt carries the diode `area=`/`pj=` fix (klayout-tools PR #5184). The fix exists upstream and the extracted leg runs locally with a newer client, so what remains is a runner-image rebake, not a tool gap.

```console
sim/gpio-pex/run.sh           # 19 requests, each a `klt pex --backend batch` (fleet only; no local fallback)
sim/gpio-pex/run.sh --probe   # one corner of one deck, local, for debugging
```

`gen_requests.py` calls `../gpio-corners/gen_requests.py` (one corner grid, not two) and inlines
the PDK switch-parameter include, because `klt pex` swaps exactly one `.include`, the DUT. Requests
are selected by what the deck instantiates, not by name: only a deck carrying the `.include
gpio.spice` card (the cell the pex run extracts) is kept; a deck for any other DUT (the `dvdd_pad`
rail clamps `esd_rail` and `esd_rail_release`) is removed from the output directory, `.sp` and
`.json`, so a new non-GPIO deck in the corner generator cannot silently break pex generation. The
client default is klt 0.9.0 (`run.sh`); `--tie-declared-pins` binds the merged `DVSS`/`VSS` net to both declared pins (DR-0004).
The generated schematic-leg `gpio.spice` wraps the design cell in the extracted pin order (`EXTRACTED_PINS` in `gen_requests.py`), so klt's positional `Xdut` line matches on both legs; `design/` is untouched.
Records under `records/` are append-only. Do not edit the layout or netlists from here.

`run.sh` passes `--pdk "$VARIANT"` (the `sim/pdk.json` variant, `gf180mcuD`) next to `--pdk-root`
and fails if a report's `provenance.pdk.name` differs. Without `--pdk`, klt picks a variant from
the shared `<rev>` directory (it picked `gf180mcuA` in `records/20261027T1000Z-probe/`). Pex figures
are citable only from records whose `provenance.pdk.name` is `gf180mcuD`.

## Extracted-leg diode parameters (#61)

klt 0.9.0 (the `run.sh` default) writes diodes with `A=`/`P=`, which ngspice rejects
(`ngspice_fatal` on every extracted leg). The fix shipped in klt 0.9.2: `klt pex` adapts the diode
cards before submitting the extracted request, and the standard and heavy fleet image configurations
now pin klt 0.9.2 (deployment still pending, #61). The submitting client needs the fix as well as the runner image (#61, comment of
2026-11-20), so the 0.9.0 default in `run.sh` cannot produce an extracted leg without a
`KLT_CLIENT` override (`KLT_CLIENT="uvx --from klayout-tools==0.9.2 klt" sim/gpio-pex/run.sh --probe`).
See `records/20261109T2200Z-probe-klt-diode-fix/record.md`.
