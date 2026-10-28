Envelopes of `esd_rail` runs that were superseded inside this record, kept as evidence. Each errored
at one corner with "timestep too small" in the trigger moscap; both fleet runs were otherwise complete.

- `esd_rail.first-attempt.json`: `.options itl4=200 gmin=1e-10 reltol=0.003`; `ss/-40C` errored.
- `esd_rail.second-attempt.json`: `.options itl4=500 gmin=1e-9 reltol=0.003 rshunt=1e12`; `ff/125C` errored.

The reported `esd_rail` request uses `itl4=1000 gmin=1e-9 reltol=0.01 abstol=1e-10 rshunt=1e12`
(`gen_requests.py`); `requests/esd_rail.{sp,json}` were regenerated and resubmitted with
`run.sh --resume` after moving the envelope aside. Every other request ran once, unchanged.
Many submits were refused with `BATCH_MAX_CONCURRENT_INSTANCES=8` (fleet saturated by other work)
and were resubmitted with `--resume`; nothing ran locally.
