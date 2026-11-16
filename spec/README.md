# spec

The ratified target specification, the porting plan and decision records.

| Document | Contents |
|---|---|
| [`io-ring.md`](io-ring.md) | Target / fallback / stretch for every parameter, PVT corners, klt rule coverage |
| [`porting-plan.md`](porting-plan.md) | Items inherited from `sky130-io-ring` (with commit), items re-derived, sibling commits read |
| [`decisions/`](decisions/) | Decision records, numbered monotonically across the whole spec |

Decision records:

- [DR-0001](decisions/0001-esd-structure-from-gf180-tmds-tx.md): ESD structure from `gf180-tmds-tx` (partial adopt)
- [DR-0002](decisions/0002-pvt-corner-set.md): PVT corner set and the thick-oxide corner limitation
- [DR-0003](decisions/0003-rail-clamp-devices.md): rail-clamp devices for `DVDD`/`DVSS` and the core rails (Amendment 1: transient sizing)
- [DR-0004](decisions/0004-pex-merged-dvss-vss.md): `DVSS` and `VSS` are one extracted net; pex ties the declared pins
- [DR-0006](decisions/0006-powered-rail-transient-duty.md): duty and peak budget for a transient on a powered `DVDD` rail (DR-0005 is reserved by open PR #50)

Rows marked `pending: sky130-io-ring#2` wait on the origin; when it ratifies, a
decision record updates them. Spec changes go through a decision record.
