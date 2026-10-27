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
is dropped: its DUT is `dvdd_pad`, not `gpio`. The client is klt 0.8.0, matching the fleet runner image.
Records under `records/` are append-only. Do not edit the layout or netlists from here.
