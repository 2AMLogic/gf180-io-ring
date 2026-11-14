# DR-0006: An ESD-like transient on a powered `DVDD` rail — clamp duty and peak budget

**Status: Proposed.** Nothing in this record is ratified. The operator rules by
letter per decision item, as on DR-0004 (ruling q91, option c) — e.g. "1b, 2c,
3b". Until a ruling lands, `esd_rail_release_peak` stays report-only, no limit
is wired into any deck, and no spec row changes. Numbering note: `main` holds
DR-0001–DR-0004; open PR #50 proposes two more (its `0004-…` already collides
with `main`'s DR-0004, and its `0005-vdd-dvdd-coupling.md`), so the next unused
number at the time of writing is 0006.

## Context

Issue #85, filed from the `esd_rail_release` probe record of PR #83. That bench
(`gen_requests.py`, `esd_rail_release_netlist`) injects the same 1.33 A /
10 ns-rise pulse the unpowered `esd_rail` deck uses, but with `DVDD` held at its
nominal 5 V through a 50 Ω series resistance — an ESD-like transient arriving on
a rail that is already up. Its peak row is reported without a target: the spec
states no ceiling for it. This record is the decision the bench asked for; it
changes no bench, no manifest row and no spec row.

What the ratified spec actually asks this clamp to survive (`spec/io-ring.md`
§ESD network): exactly two stress rows, `HBM | 2 kV, design target only` and
`CDM | not targeted in this spec`. Both are component-handling models — events
a part experiences unpowered. **The spec has no row for a powered-state,
system-level or EOS-like transient at all.** That absence is a ratified fact and
the strongest single input to decision item 1.

What grounding exists for any ceiling (`design/README.md`, "Budget
(assumption)"): the 6 V figure the unpowered `esd_rail` deck carries
(`V_RAIL_BUDGET = 6.0` in `sim/gpio-corners/gen_requests.py`, a declared
assumption, not a spec row — DR-0003 Amendment 1 item 3) is "a model-header
label; the cards' `bv` (11 / 10.5 V) is reverse breakdown and unused". No PDK
absolute maximum sits behind it, so a powered-rail ceiling cannot be derived
from the PDK either.

Two things the word "budget" can mean, kept separate throughout (they have
different owners):

- **Duty** — which stress events the clamp must handle. A spec choice; the
  operator owns it (§ESD network rows).
- **Device limit** — what the silicon tolerates. A PDK fact; this PDK does not
  document one for the thick-oxide devices' operating voltage.

A number can be simultaneously "outside every budget, because none exists" and
"a number nobody should be relaxed about". This record answers duty and limit
separately for exactly that reason.

## The number this record is about, and where each figure comes from

Every figure below is **simulated clamp behaviour** at one corner (typical
process, 25 °C), host-run and therefore a probe, not evidence: `cite.py`
(`refuse_probe`) refuses the record these rows live in, and each is admissible
here only on the footing DR-0003 Amendment 1 item 2 uses for its host probes —
supporting detail, never item-5 evidence.

| Figure | Value | Source |
|---|---|---|
| `esd_rail` peak, unpowered deck | 4.43749 V | `sim/gpio-corners/records/20261114T185642Z/rows.json`, row `esd_rail` (result=PROBE) |
| `esd_rail_release_peak`, powered deck | 8.65956 V | same record, row `esd_rail_release_peak`, target "report only" |
| clamp gate peak, powered deck | 2.53352 V | same record, row `esd_rail_release_gate_peak` |
| release at 4.5 µs | gate 5.36836e-06 V, `DVDD` 4.99999 V, rail current 2.74663e-07 A | same record, rows `esd_rail_release_*` |
| 1.33 A / 10 ns pulse | bench input | 2 kV / 1.5 kΩ HBM arithmetic (`design/README.md`, "Stress current (assumption)"); spec row is "HBM 2 kV, design target only" |
| 50 Ω series, 5 µs window | bench assumptions | `gen_requests.py` (`R_RAIL_SERIES`, `T_REL_STOP`), declared, not spec rows |
| 6 V | unpowered-deck budget | `V_RAIL_BUDGET`, `gen_requests.py`; provenance `design/README.md` (model-header label); DR-0003 Amendment 1 item 3 |

**Reproduction and instrumentation** (2026-11-14, worktree of this record's PR;
host ngspice-47, open_pdks `f6eeac7` read from `~/.ciel`, the same PDK build,
engine version and input-netlist sha256 `91533316…` as the record above; the
committed deck untouched — a throwaway copy with `.meas` cards added on the
trigger nodes). All five committed measurements above reproduced to every
printed digit. New, previously unrecorded values from the instrumented copies:

| Node | powered deck | unpowered deck |
|---|---|---|
| trigger sense node `tio`, quiescent (1 ns) | 4.99998 V | ≈ 0 V (−1.3e-17 V) |
| `tio`, peak through the pulse | 5.51545 V | 0.911374 V |
| `tio` at 60 ns | 5.32844 V | — |
| `DVDD` at 60 ns | 8.43124 V | — |
| clamp gate `gio` at 60 ns | 2.40438 V | — |
| clamp gate `gio`, peak | 2.53352 V | 3.88437 V |

Mechanism, now measured rather than inferred: in the powered deck the trigger RC
sense node `tio` idles at `DVDD` (the trigger resistor is a `pfet_06v0` with its
gate on `DVSS` — DR-0003 decision item 1 — so it conducts always), which holds
the inverter's `nfet` on in quiescence. On the pulse `tio` follows the RC and
reaches only 5.52 V while `DVDD` is at 8.43 V, so the inverter `pfet` (DR-0003
Amendment 1: 10 × 10 µm, `m=10`) and `nfet` fight, and the clamp gate peaks at
2.53 V — 1.35 V below the unpowered deck's 3.88 V gate peak. The clamp conducts
weakly instead of hard, and the rail peaks 4.22 V higher: 8.65956 V against
4.43749 V. Release itself is clean at this corner (gate back to 5.4e-06 V, rail
within 10 µV of the supply, 275 nA at 4.5 µs).

No refutation: the 8.65956 V peak is real at this corner, and the trigger-ratio
mechanism the filing suspected is consistent with every instrumented value. The
open question is therefore the one the issue names — duty and ceiling — not
whether the number exists.

## Decision items

### 1. Is a transient on an already-powered `DVDD` in this clamp's duty at all?

- **(a) Yes, under the ratified stress model.** Rejected: the only ratified
  stress rows are HBM and CDM, both unpowered handling events; there is no
  powered-state row for anything to be in duty under.
- **(b) No — outside the ratified duty as the spec stands.** (Recommended.) The
  clamp's ratified job is the unpowered HBM-like event the `esd_rail` deck
  models. A powered-rail transient is a different stress event; whether this
  clamp, a separate structure, or no structure owns it is a spec choice the
  operator makes by ratifying a stress row in §ESD network — a bench result
  cannot decide it. "Outside duty" is not "impossible": powered rails do see
  such events in the field; the spec simply does not yet ask this clamp to
  handle one.
- **(c) Yes, as a declared design target without a spec row.** Rejected: it
  writes a bound outside the spec, which ages into a de-facto limit without
  ratification — the exact move DR-0003 Amendment 1 item 3 declines for the
  unpowered case ("stays an assumption … not a spec row").

### 2. If the event is ever in duty, what peak `DVDD` ceiling applies with the rail up?

- **(a) Reuse the 6 V figure.** Rejected: it is the `*_06v0` model-header label
  declared for the unpowered deck (`design/README.md`; `gen_requests.py`
  `V_RAIL_BUDGET`), kept an assumption even there by DR-0003 Amendment 1 item 3.
  Applying it to a different quiescent state compounds one assumption into two.
- **(b) Set a different number.** Rejected: nothing sources one. The PDK
  documents no absolute maximum behind the 6 V label, and no ratified row gives
  a powered ceiling — a number here would be invented to make 8.65956 V resolve,
  either way.
- **(c) Attach no ceiling now.** (Recommended.) The row stays report-only until
  a sourced number exists: a foundry absolute-maximum statement for the
  thick-oxide devices, or an operator-set design target written into §ESD
  network alongside the stress row of item 1(b). Either is the operator's call.

### 3. Does `esd_rail_release_peak` become a pass/fail row, or stay report-only?

- **(a) Pass/fail now.** Rejected twice over. No ceiling exists to fail against
  (item 2). And the manifest cost is real: there is no `esd_rail_release` row id
  in `manifests/gf180-io-ring.json`, and `COVERS` in `sim/gpio-corners/cite.py`
  maps only `esd_pad` and `esd_rail` — a pass/fail row is a new *declared* spec
  row, which tracker item 5 (klt rule coverage) grades **uncovered** until a
  15-corner record cites it, against item 5's current `partial_coverage` that
  #48 / PR #50 is working to clear.
- **(b) Stay report-only.** (Recommended, and implied by 1(b) + 2(c).) Nobody
  should read `esd_rail_release_peak` as a pass or a failure while this record
  is `Proposed` — or after a ruling that picks 1(b)/2(c), until the path in
  Consequences below is walked.

## Consequences

- Until the operator rules (and under the recommended ruling, until the full
  path below is walked): the powered-deck peak rows stay report-only with no
  target; 8.65956 V at typical/25 °C is context, not a verdict; the release
  itself remains the only thing that record shows.
- **Path to a budgeted row**, if the operator ratifies this record as proposed:
  (i) ratify a powered/system-level stress row in §ESD network; (ii) source or
  set the peak ceiling for it; (iii) land #45's 15-corner `esd_rail_release`
  record; (iv) only then a later issue adds the `lim()`, the manifest row and
  the `COVERS` entry. Each step is its own ratification or evidence gate.
- The manifest cost of item 3(a) stands as written there: choosing pass/fail
  today would add an uncovered declared row and work against item 5's current
  grade.
- **Scope boundary**: this record answers duty and ceiling only. What counts as
  *release* — gate ceiling, `DVDD` recovery tolerance, quiescent-current
  ceiling, and the time by which each holds — is a separate question, owned by
  #45's acceptance criteria. One record, one question.
- **No deck change accompanies this record**: `gen_requests.py`'s
  `esd_rail_release_netlist` measurements stay unbounded and `V_RAIL_BUDGET` is
  untouched in the PR carrying this record. Wiring any limit in waits for
  ratification plus #45's record.
- If a future ruling ever puts the powered event in duty, the trigger topology —
  sized for the unpowered case (DR-0003, Amendment 1) — is where the redesign
  conversation starts, not the 6 V assumption.
- Simulated clamp behaviour only: nothing here is an ESD rating, and no cell
  gains any ESD claim from it.
