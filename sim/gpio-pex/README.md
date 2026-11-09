# gpio-pex

T1 item 7 (post-layout verification): the item-5 GPIO spec suite re-run on the netlist extracted
from `layout/gf180_io_ring.gds`, reported by `klt pex` as a per-corner, per-row
schematic-vs-extracted delta. **Status: not met.** See the latest record's `record.md`.

```console
sim/gpio-pex/run.sh           # 19 requests, each a `klt pex --backend batch` (fleet only; no local fallback)
sim/gpio-pex/run.sh --probe   # one corner of one deck, local, for debugging
```

`gen_requests.py` calls `../gpio-corners/gen_requests.py` (one corner grid, not two) and inlines
the PDK switch-parameter include, because `klt pex` swaps exactly one `.include`, the DUT. `esd_rail`
is dropped: its DUT is `dvdd_pad`, not `gpio`. The client is klt 0.9.0, matching the fleet runner image; `--tie-declared-pins` binds the merged `DVSS`/`VSS` net to both declared pins (DR-0004).
The generated schematic-leg `gpio.spice` wraps the design cell in the extracted pin order (`EXTRACTED_PINS` in `gen_requests.py`), so klt's positional `Xdut` line matches on both legs; `design/` is untouched.
Records under `records/` are append-only. Do not edit the layout or netlists from here.

`run.sh` passes `--pdk "$VARIANT"` (the `sim/pdk.json` variant, `gf180mcuD`) next to `--pdk-root`
and fails if a report's `provenance.pdk.name` differs. Without `--pdk`, klt picks a variant from
the shared `<rev>` directory (it picked `gf180mcuA` in `records/20261027T1000Z-probe/`). Pex figures
are citable only from records whose `provenance.pdk.name` is `gf180mcuD`.
