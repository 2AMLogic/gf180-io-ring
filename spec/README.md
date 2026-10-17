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

Rows marked `pending: sky130-io-ring#2` wait on the origin; when it ratifies, a
decision record updates them. Spec changes go through a decision record.
