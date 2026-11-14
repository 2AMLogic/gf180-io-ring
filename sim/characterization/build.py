#!/usr/bin/env python3
"""Aggregate the cited item-5 and item-6 evidence into one per-spec-row report.

    python3 -I build.py <repo-root> [--out DIR] [--check]

Reads manifests/gf180-io-ring.json and, through it, *only* the files that manifest
cites for T1 item 5 (corner matrix) and item 6 (Monte Carlo yield). Writes report.json
(the machine twin: one object per spec row, every number with the file it came from)
and renders report.md from that same object, so the two forms cannot disagree.

  --out DIR   write the two report files to DIR (default: this script's directory)
  --check     build into a temporary directory and byte-compare against the committed
              report; exit 1 on drift, naming the files that differ

This script restates no ratified number. Every limit it prints is read from a cited
envelope's `measurements[].limits`; the row spine is the manifest's `spec_rows["5"]`;
the "no evidence" set is the manifest's own `gap` strings. It runs no simulation and
needs nothing but `python3` and the committed JSON.

Pre-silicon simulation only. Nothing here rates or qualifies a cell for ESD.
"""
import argparse
import difflib
import importlib.util
import json
import os
import posixpath
import sys
import tempfile

SCHEMA_VERSION = 1
MANIFEST = "manifests/gf180-io-ring.json"
#: the report lives here, so links out of it are relative to this directory
REPORT_DIR = "sim/characterization"
#: T1 item ids this report aggregates: the corner matrix and the Monte Carlo campaign
ITEM_CORNER, ITEM_MC = "5", "6"
#: the item-7 (post-layout) column belongs to #21 and has no cited evidence yet
ITEM_POST_LAYOUT = "7"
#: Parameter text for a spine row the manifest neither cites evidence for nor declares a
#: gap on. Such a row still renders as `no evidence` across the board -- never blank and
#: never a pass -- and says why the cell is empty, so the omission is visible in the diff
#: rather than aborting the build.
NO_REASON = ("no cited evidence and no declared `gap` in the manifest -- this row is "
             "neither covered nor explained")

#: Rows whose measurement-derived id differs from the manifest's spec-row id.
#:
#: The report is keyed on `spec_rows["5"]` (the spine). Two different naming
#: conventions have to be joined onto it, and both are covered by this one map:
#:
#:   * item 5 names a measurement, not a row -- `r_pullup`/`r_pulldown` reduce to
#:     `pullup_5v`/`pulldown_5v`, while the manifest cites those envelopes for the
#:     single spec row `pull_5v`; likewise the two pad-clamp forward drops
#:     (`vf_up_hbm`, `vf_dn_hbm`) are both evidence for `esd_pad_clamp`.
#:   * item 6 splits the pull devices into their own spec rows (`pullup_5v`,
#:     `pulldown_5v`), which project back onto the spine's `pull_5v`.
#:
#: Printed in the report's methodology section so the join is auditable rather than
#: implicit. A row key that this map sends somewhere not cited for it is a hard error.
ALIAS = {
    "pullup_5v": "pull_5v",
    "pulldown_5v": "pull_5v",
    "pullup_3v3": "pull_3v3",
    "pulldown_3v3": "pull_3v3",
    "esd_pad_up": "esd_pad_clamp",
    "esd_pad_dn": "esd_pad_clamp",
    "esd_rail": "esd_rail_clamp",
}

#: spine row prefix -> (spec/io-ring.md section, GitHub-style anchor). Navigation only:
#: the parameter prose itself comes from `ROWS` in sim/gpio-corners/collect.py and the
#: numbers from the cited envelopes.
SPEC_SECTIONS = (
    ("esd_", ("ESD network", "esd-network")),
    ("", ("GPIO electrical targets", "gpio-electrical-targets")),
)


def fail(msg):
    sys.exit("characterization: FAIL: " + msg)


def load_collect(repo):
    """Import sim/gpio-corners/collect.py by path for its measurement tables.

    By path, not by `sys.path` insertion: sim/mc/collect.py is also named `collect`,
    so a path insert would make which module wins depend on insert order.
    """
    path = os.path.join(repo, "sim", "gpio-corners", "collect.py")
    if not os.path.isfile(path):
        fail(f"{path} not found (the measurement base-name map lives there)")
    spec = importlib.util.spec_from_file_location("gpio_corners_collect", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for attr in ("ROWS", "CONTEXT", "KEY", "fmt"):
        if not hasattr(mod, attr):
            fail(f"sim/gpio-corners/collect.py no longer exports {attr}")
    return mod


def read_json(repo, relpath):
    """Read a cited file. A missing or unreadable citation fails the build loudly."""
    path = os.path.join(repo, relpath)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        fail(f"cited file {relpath} is missing or unreadable: {e}")


def link(relpath):
    """A link from report.md to a repo-relative cited path."""
    return posixpath.relpath(relpath, REPORT_DIR)


def spec_section(row_id):
    for prefix, section in SPEC_SECTIONS:
        if row_id.startswith(prefix):
            return {"section": section[0], "anchor": section[1]}
    raise AssertionError("SPEC_SECTIONS must end with a catch-all")


def mode_of(stem):
    """Supply mode carried by a request stem, exactly as collect.py derives it."""
    return "3v3" if "3v3" in stem else ("-" if stem.startswith("esd") else "5v")


def derived_id(stem, base, rows_table):
    """(request stem, measurement base name) -> the row id collect.py would emit."""
    rid = rows_table[base][0]
    mode = mode_of(stem)
    return rid if mode == "-" else f"{rid}_{mode}"


def rel_margin(value, limits):
    """Margin to the nearest bound, normalized by that bound.

    Normalized because one envelope can carry several supply instances with
    *different* limits (xfer_5v's trip points scale with DVDD), and the binding
    instance is the one closest to its own limit -- the same reduction
    sim/gpio-corners/collect.py uses. Returns None for a measurement with no bound.
    """
    out = []
    if limits.get("max") is not None:
        out.append((limits["max"] - value) / abs(limits["max"]))
    if limits.get("min") is not None:
        out.append((value - limits["min"]) / abs(limits["min"]))
    return min(out) if out else None


def hard_limits(limits):
    """The pass/fail bounds of a measurement, without the yield target."""
    return {k: v for k, v in (limits or {}).items() if k in ("min", "max") and v is not None}


def target_str(limits, unit, fmt):
    """Render a limit pair. Every value here comes from the cited envelope."""
    parts = []
    if limits.get("min") is not None:
        parts.append(f">= {fmt(limits['min'], unit)}")
    if limits.get("max") is not None:
        parts.append(f"<= {fmt(limits['max'], unit)}")
    return " and ".join(parts) if parts else "report only"


def temp_key(label):
    """Sort key for a corner-id temperature segment ('-40C', '25C', '125C').

    Numeric, so the cited temperatures read -40, 25, 125 rather than in string order.
    An unparseable label sorts last and keeps its text rather than failing the build.
    """
    try:
        return (0, float(label.rstrip("Cc")))
    except ValueError:
        return (1, 0.0)


def measurements_of(repo, relpath, cited_rows, collect):
    """Yield (cited_row, base, measurement) for every limited measurement we can place.

    A measurement whose base name is unknown to both `ROWS` and `CONTEXT` is a hard
    error: it is a new measurement nobody has mapped to a spec row, and dropping it
    silently would understate the evidence. A measurement that resolves to a row this
    file is *not* cited for is skipped -- the manifest decides which rows a file is
    evidence for (xfer_*_<T>.json measures `hyst`, but `hyst_*` is cited through the
    companion `*.hyst-control.json`).
    """
    env = read_json(repo, relpath)
    stem = os.path.basename(relpath)[: -len(".json")]
    placed, unbound = [], []
    for m in env.get("measurements") or []:
        name = m.get("name")
        if not name:
            fail(f"{relpath}: a measurement has no name")
        base = collect.KEY.match(name)["base"]
        if base in collect.CONTEXT:
            continue  # report-only context measurement, carries no limit
        if base not in collect.ROWS:
            fail(f"{relpath}: measurement {name!r} has base name {base!r}, which is in "
                 f"neither ROWS nor CONTEXT of sim/gpio-corners/collect.py -- map it to a "
                 f"spec row there before this report can carry it")
        if not hard_limits(m.get("limits")):
            fail(f"{relpath}: measurement {name!r} maps to a spec row but declares no "
                 f"min/max limit, so no verdict can be read from it")
        did = derived_id(stem, base, collect.ROWS)
        for cand in (did, ALIAS.get(did)):
            if cand is not None and cand in cited_rows:
                placed.append((cand, base, m))
                break
        else:
            unbound.append((did, base, m))

    # Rows this file is cited for that no measurement reached. One such row plus at
    # least one homeless measurement is an unambiguous pairing (a newly cited request
    # whose measurement base maps to a sibling row id); anything else is a real gap in
    # the join and must be reported, never guessed at.
    reached = {row for row, _, _ in placed}
    orphan_rows = [r for r in cited_rows if r not in reached]
    if orphan_rows and unbound:
        if len(orphan_rows) > 1:
            fail(f"{relpath}: cited for {orphan_rows} but no measurement resolves to any of "
                 f"them (unplaced: {[d for d, _, _ in unbound]}); extend ALIAS in "
                 f"{REPORT_DIR}/build.py so the join is declared, not guessed")
        for _, base, m in unbound:
            placed.append((orphan_rows[0], base, m))
    elif orphan_rows:
        fail(f"{relpath}: cited as evidence for {orphan_rows} in {MANIFEST}, but the file "
             f"carries no limited measurement for it")
    return placed


def corner_cell(repo, citations, collect):
    """Per spine row: the least-margin worst case over every cited corner envelope."""
    contributions = {}
    for cit in citations:
        relpath = cit.get("file")
        if not relpath:
            fail(f"{MANIFEST}: an item-{ITEM_CORNER} citation has no 'file'")
        for cited_row, base, m in measurements_of(repo, relpath, cit.get("rows") or [],
                                                  collect):
            spine = ALIAS.get(cited_row, cited_row)
            worst = m.get("worst_case") or {}
            value = worst.get("value")
            if not isinstance(value, (int, float)):
                fail(f"{relpath}: measurement {m['name']!r} has no finite worst_case.value")
            limits = hard_limits(m.get("limits"))
            contributions.setdefault(spine, []).append({
                "base": base,
                "measurement": m["name"],
                "unit": m.get("unit") or collect.ROWS[base][2],
                "label": collect.ROWS[base][1],
                "limits": limits,
                "value": value,
                "binding_corner": worst.get("corner_id"),
                "status": m.get("status"),
                "margin": rel_margin(value, limits),
                "source": relpath,
            })

    cells = {}
    for spine, items in contributions.items():
        units = {i["unit"] for i in items}
        if len(units) != 1:
            fail(f"row {spine}: cited measurements disagree on unit {sorted(units)}")
        # The binding contribution is the one closest to its own limit.
        binding = min(items, key=lambda i: (i["margin"], i["measurement"]))
        statuses = {i["status"] for i in items}
        cells[spine] = {
            "status": "fail" if "fail" in statuses else "pass",
            "unit": binding["unit"],
            "label": "; ".join(sorted({i["label"] for i in items})),
            "limits": binding["limits"],
            "worst_value": binding["value"],
            "binding_corner": binding["binding_corner"],
            "binding_measurement": binding["measurement"],
            "source": binding["source"],
            "contributions": sorted(
                ({"measurement": i["measurement"], "limits": i["limits"], "value": i["value"],
                  "binding_corner": i["binding_corner"], "status": i["status"],
                  "source": i["source"]} for i in items),
                key=lambda c: (c["source"], c["measurement"])),
        }
    return cells


def mc_cell(repo, citations, collect):
    """Per spine row: the weakest cited Monte Carlo yield (lowest CI low bound)."""
    contributions = {}
    for cit in citations:
        relpath = cit.get("file")
        if not relpath:
            fail(f"{MANIFEST}: an item-{ITEM_MC} citation has no 'file'")
        for cited_row, base, m in measurements_of(repo, relpath, cit.get("rows") or [],
                                                  collect):
            spine = ALIAS.get(cited_row, cited_row)
            emp = ((m.get("yield") or {}).get("empirical")) or {}
            low = (emp.get("confidence_interval") or {}).get("low")
            est = emp.get("estimate")
            if not isinstance(low, (int, float)) or not isinstance(est, (int, float)):
                fail(f"{relpath}: measurement {m['name']!r} carries no empirical yield "
                     f"estimate with a confidence interval")
            corners = m.get("source_corners") or []
            if not corners:
                fail(f"{relpath}: measurement {m['name']!r} declares no source_corners, so "
                     f"the conditions behind its yield are unknown")
            contributions.setdefault(spine, []).append({
                "measurement": m["name"],
                "unit": m.get("unit") or collect.ROWS[base][2],
                "limits": hard_limits(m.get("limits")),
                "target_yield": (m.get("limits") or {}).get("target_yield"),
                "estimate": emp["estimate"],
                "ci_low": low,
                "ci_high": (emp.get("confidence_interval") or {}).get("high"),
                "method": emp.get("method"),
                "confidence": emp.get("confidence"),
                "n": emp.get("n"),
                "source_corners": list(corners),
                "negative_control": m.get("negative_control") is not None,
                "status": m.get("status"),
                "source": relpath,
            })

    cells = {}
    for spine, items in contributions.items():
        binding = min(items, key=lambda i: (i["ci_low"], i["measurement"], i["source"]))
        corners = sorted({c for i in items for c in i["source_corners"]})
        cells[spine] = {
            "status": "fail" if "fail" in {i["status"] for i in items} else "pass",
            "unit": binding["unit"],
            "limits": binding["limits"],
            "target_yield": binding["target_yield"],
            "estimate": binding["estimate"],
            "ci_low": binding["ci_low"],
            "ci_high": binding["ci_high"],
            "method": binding["method"],
            "confidence": binding["confidence"],
            "n": binding["n"],
            "binding_measurement": binding["measurement"],
            "source": binding["source"],
            "source_corners": corners,
            "processes": sorted({c.split("/")[0] for c in corners}),
            "temperatures": sorted({c.rsplit("/", 1)[-1] for c in corners}, key=temp_key),
            "has_negative_control": any(i["negative_control"] for i in items),
            "sources": sorted({i["source"] for i in items}),
        }
    return cells


def build(repo):
    """Assemble report.json: the single object both report forms are rendered from."""
    collect = load_collect(repo)
    manifest = read_json(repo, MANIFEST)
    for key in ("spec_rows", "evidence"):
        if key not in manifest:
            fail(f"{MANIFEST} has no {key!r} -- it is not a block manifest")
    spine_rows = manifest["spec_rows"].get(ITEM_CORNER)
    mc_rows = manifest["spec_rows"].get(ITEM_MC) or []
    if not spine_rows:
        fail(f"{MANIFEST} cites no spec_rows for item {ITEM_CORNER}")
    if manifest["evidence"].get(ITEM_POST_LAYOUT):
        fail(f"{MANIFEST} now cites evidence for item {ITEM_POST_LAYOUT} (post-layout). "
             f"This report renders that column as 'no evidence' unconditionally; teach it "
             f"to read the citation before the manifest lands (see issue #21)")

    corners = corner_cell(repo, manifest["evidence"].get(ITEM_CORNER) or [], collect)
    mcs = mc_cell(repo, manifest["evidence"].get(ITEM_MC) or [], collect)

    # Every spec row of item 6 must land on the spine, or the report would silently
    # drop statistical evidence the manifest cites.
    spine_ids = [r["id"] for r in spine_rows]
    for r in mc_rows:
        projected = ALIAS.get(r["id"], r["id"])
        if projected not in spine_ids:
            fail(f"item-{ITEM_MC} spec row {r['id']!r} projects to {projected!r}, which is "
                 f"not an item-{ITEM_CORNER} spec row; extend ALIAS in {REPORT_DIR}/build.py")

    rows = []
    for entry in spine_rows:
        rid = entry["id"]
        gap = entry.get("gap")
        corner, mc = corners.get(rid), mcs.get(rid)
        if gap:
            # A declared gap is read from the manifest, never hard-coded here: #48 /
            # PR #50 is in flight to close both of the current ones.
            status = "no_evidence"
        elif corner is None and mc is None:
            status = "no_evidence"
        else:
            status = (corner or mc)["status"]
        label = gap or (corner or mc or {}).get("label") or NO_REASON
        rows.append({
            "row": rid,
            "parameter": label,
            "spec": spec_section(rid),
            "status": status,
            "declared_gap": gap,
            "corner": corner,
            "monte_carlo": mc,
            "mc_limits_differ": bool(
                corner and mc and corner["limits"] != mc["limits"]),
            "post_layout": {
                "status": "no_evidence",
                "note": f"T1 item {ITEM_POST_LAYOUT} (post-layout extraction) cites no "
                        f"evidence in the manifest; tracked in issue #21",
            },
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "block": manifest.get("block"),
        "kind": manifest.get("kind"),
        "manifest": MANIFEST,
        "spine": f'{MANIFEST} spec_rows["{ITEM_CORNER}"]',
        "alias_map": dict(sorted(ALIAS.items())),
        "evidence_file_count": {
            ITEM_CORNER: len(manifest["evidence"].get(ITEM_CORNER) or []),
            ITEM_MC: len(manifest["evidence"].get(ITEM_MC) or []),
        },
        "rows": rows,
    }


# --------------------------------------------------------------------------- render


def pct(x):
    return f"{x * 100:.4g} %"


def render_md(report, fmt):
    """Render report.md from report.json and nothing else."""
    n5 = report["evidence_file_count"][ITEM_CORNER]
    n6 = report["evidence_file_count"][ITEM_MC]
    out = [
        f"# {report['block']} - per-spec-row characterization report",
        "",
        "Aggregated **pre-silicon simulation** of the drawn GPIO cell, one line per "
        f"ratified spec row. Generated by `{REPORT_DIR}/build.py` from "
        f"[`{report['manifest']}`]({link(report['manifest'])}) and, through it, only the "
        f"{n5 + n6} files that manifest cites as T1 item-{ITEM_CORNER} "
        f"({n5}, corner matrix) and item-{ITEM_MC} ({n6}, Monte Carlo yield) evidence. "
        "Do not edit by hand: regenerate with `sim/characterization/run.sh`.",
        "",
        "These are measurements, not ratings. No cell here is ESD-rated or qualified; "
        "the ESD rows are simulated clamp behaviour only.",
        "",
        "## Per-row results",
        "",
        "Every limit and every number below is read from a cited envelope. The binding "
        "corner is the point closest to its own limit; the Monte Carlo cell reports the "
        "weakest cited campaign for that row.",
        "",
        "| Row | Parameter | Spec section | Limit | Worst | Binding corner | Meets limit |"
        " Monte Carlo (typical process only) | Post-layout |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for r in report["rows"]:
        spec = r["spec"]
        speccell = f"[{spec['section']}]({link('spec/io-ring.md')}#{spec['anchor']})"
        if r["declared_gap"]:
            out.append(
                f"| `{r['row']}` | {r['parameter']} | {speccell} | no evidence | no evidence "
                f"| no evidence | **no evidence** | no evidence | no evidence |")
            continue

        c, mc = r["corner"], r["monte_carlo"]
        if c:
            unit = c["unit"]
            limit = target_str(c["limits"], unit, fmt)
            worst = fmt(c["worst_value"], unit)
            corner = f"`{c['binding_corner']}` ([envelope]({link(c['source'])}))"
            meets = "yes" if c["status"] == "pass" else "**NO**"
        else:
            limit = worst = corner = "no evidence"
            meets = "**no evidence**"

        if mc:
            mcunit = mc["unit"]
            temps = ", ".join(mc["temperatures"])
            parts = [f"yield {pct(mc['estimate'])}",
                     f"CI low {pct(mc['ci_low'])} ({mc['method']}, "
                     f"{mc['confidence']:g} confidence, n = {mc['n']})",
                     f"{temps}"]
            if r["mc_limits_differ"]:
                parts.append(f"against its own limit {target_str(mc['limits'], mcunit, fmt)}")
            if mc["target_yield"] is not None:
                parts.append(f"target {pct(mc['target_yield'])}")
            if mc["has_negative_control"]:
                parts.append("negative control cited for this row")
            mccell = (f"{'; '.join(parts)} ([envelope]({link(mc['source'])}))")
        else:
            mccell = "no evidence (row is not statistical / not cited for item "
            mccell += f"{ITEM_MC})"

        out.append(f"| `{r['row']}` | {r['parameter']} | {speccell} | {limit} | {worst} "
                   f"| {corner} | {meets} | {mccell} | no evidence |")

    # ------------------------------------------------------------------ methodology
    gaps = [r for r in report["rows"] if r["declared_gap"]]
    differing = [r for r in report["rows"] if r["mc_limits_differ"]]
    out += [
        "",
        "## What has no evidence, and why",
        "",
        f"- **Post-layout (item {ITEM_POST_LAYOUT}).** Every row's post-layout cell reads "
        "`no evidence`: the manifest cites no post-layout extraction, so there is nothing "
        "to aggregate. That column is tracked in issue #21 and is deliberately out of "
        "scope here. A `no evidence` cell is never a pass.",
        f"- **Declared gaps.** {len(gaps)} of the {len(report['rows'])} spec rows carry a "
        f"`gap` string in the manifest and are reported as `no evidence`, quoting that "
        "string as their parameter. The gap set is read from "
        f"`spec_rows[\"{ITEM_CORNER}\"][*].gap` on every build, never hard-coded, so this "
        "report follows the manifest when a gap is closed or added:",
    ]
    for r in gaps:
        out.append(f"  - `{r['row']}`: {r['declared_gap']}")
    if not gaps:
        out.append("  - (none in the manifest as built)")

    out += [
        "",
        "## Methodology",
        "",
        "### Where each number comes from",
        "",
        "- **The row spine** is the manifest's "
        f"`spec_rows[\"{ITEM_CORNER}\"]`, in manifest order. `spec/io-ring.md` names its "
        "parameters in prose and carries no row ids, so the spec section is linked for the "
        "human-readable parameter and the ids come from the manifest.",
        "- **Limits** are read from each cited envelope's `measurements[].limits`. This "
        "report holds no copy of a ratified number; a limit that changes in the spec "
        "reaches this table only by way of a re-run bench and a re-cited envelope.",
        "- **The binding corner** is the cited measurement instance closest to its own "
        "limit, normalized by that limit. The normalization matters: one envelope carries "
        "nine supply instances whose trip-point limits scale with `DVDD`, so the smallest "
        "absolute margin is not always the binding one. This is the same reduction "
        f"[`sim/gpio-corners/collect.py`]({link('sim/gpio-corners/collect.py')}) applies, "
        "and its `ROWS` measurement table is imported from there rather than retyped.",
        "- **Content hashes are not verified here.** The manifest's item-"
        f"{ITEM_CORNER} `content_hash` is the envelope's own `environment.netlist_sha256`, "
        f"not the sha256 of the cited file, and item-{ITEM_MC} citations carry none. "
        "Artifact freshness is `klt signoff`'s job, enforced on every PR by "
        f"[`.github/workflows/signoff.yml`]({link('.github/workflows/signoff.yml')}).",
        "- **The row-to-file mapping is asserted, not derived.** The manifest states which "
        "spec rows each envelope is evidence for (`klt signoff` records every item-"
        f"{ITEM_CORNER} row source as `asserted`), and this report inherits that assertion. "
        "It checks the mapping for consistency -- a cited row no measurement can supply, or "
        "a measurement whose base name is unknown, fails the build -- but it does not "
        "independently prove that a given envelope measures the row it is cited for.",
        "",
        "### The alias map",
        "",
        "Item 5 names measurements and item 6 splits the pull devices into their own spec "
        "rows, so both have to be joined onto the spine. That join is this map, and it is "
        "the one design decision in this report:",
        "",
        "| Measurement-derived or item-6 row id | Spine row |",
        "|---|---|",
    ]
    for k, v in report["alias_map"].items():
        out.append(f"| `{k}` | `{v}` |")
    out += [
        "",
        "A row key that this map sends to a row the manifest does not cite it for is a hard "
        "error, not a silent drop; so is a measurement base name absent from `ROWS`.",
        "",
        "### Monte Carlo is not corner coverage",
        "",
        "Every cited yield campaign samples the **`typical` process section only** "
        f"(`measurements[].source_corners`), so an item-{ITEM_MC} figure can never stand in "
        f"for an item-{ITEM_CORNER} corner verdict, and a row with a Monte Carlo cell but no "
        "corner cell is not covered across process. The temperatures actually cited differ "
        "per row and are printed in each cell: the output-level and transfer rows are cited "
        "at three temperatures, the pull-device rows at 25 C alone. Where a row's cited "
        "campaigns disagree, the cell reports the weakest of them (lowest confidence-interval "
        "low bound).",
        "",
        "### The two columns do not always share a limit",
        "",
    ]
    if differing:
        out.append(
            f"{len(differing)} rows carry a different limit in the two columns, and the "
            "Monte Carlo cell renders its own limit inline for them:")
        out.append("")
        out.append("| Row | Corner-matrix limit | Monte Carlo limit |")
        out.append("|---|---|---|")
        for r in differing:
            c, mc = r["corner"], r["monte_carlo"]
            out.append(f"| `{r['row']}` | {target_str(c['limits'], c['unit'], fmt)} "
                       f"| {target_str(mc['limits'], mc['unit'], fmt)} |")
        out += [
            "",
            "Both are correct readings of the one ratified rule (VIL <= 0.3 * `DVDD`, "
            "VIH >= 0.7 * `DVDD`): the corner matrix evaluates it at the binding `DVDD` "
            "extreme, the Monte Carlo campaign at nominal `DVDD`. Neither is relaxed and "
            "neither is reconciled here -- reconciling them would be a spec change, which "
            "belongs in a decision record.",
        ]
    else:
        out.append("As built, every row's two columns agree on its limit.")

    # --------------------------------------------------------------- evidence index
    out += [
        "",
        "## Evidence index",
        "",
        "Every file read for each row, which is exactly the set the manifest cites.",
        "",
        "| Row | Corner-matrix evidence | Monte Carlo evidence |",
        "|---|---|---|",
    ]
    for r in report["rows"]:
        c, mc = r["corner"], r["monte_carlo"]
        cfiles = sorted({x["source"] for x in c["contributions"]}) if c else []
        mcfiles = mc["sources"] if mc else []
        cell = (", ".join(f"[`{posixpath.basename(f)}`]({link(f)})" for f in cfiles)
                or "no evidence")
        mcell = (", ".join(f"[`{posixpath.basename(f)}`]({link(f)})" for f in mcfiles)
                 or "no evidence")
        out.append(f"| `{r['row']}` | {cell} | {mcell} |")

    out += [
        "",
        "## Regenerating this report",
        "",
        "    sim/characterization/run.sh           # rewrite report.md and report.json",
        "    sim/characterization/run.sh --check   # fail if the committed report is stale",
        "",
        f"`--check` runs on every pull request. Any change to [`{report['manifest']}`]"
        f"({link(report['manifest'])}) -- a new citation, a closed or added `gap`, a "
        "re-pointed record -- must be accompanied by a regenerated report in the same pull "
        "request, the same obligation the committed `klt signoff` record already carries.",
        "",
    ]
    return "\n".join(out)


def write(outdir, report, fmt):
    os.makedirs(outdir, exist_ok=True)
    jpath = os.path.join(outdir, "report.json")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")
    mpath = os.path.join(outdir, "report.md")
    with open(mpath, "w", encoding="utf-8") as f:
        f.write(render_md(report, fmt))
    return [jpath, mpath]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo", help="repository root")
    ap.add_argument("--out", help="output directory (default: this script's directory)")
    ap.add_argument("--check", action="store_true",
                    help="build to a temporary directory and byte-compare against the "
                         "committed report; exit 1 on drift")
    args = ap.parse_args()

    repo = os.path.abspath(args.repo)
    here = os.path.dirname(os.path.abspath(__file__))
    committed = os.path.abspath(args.out) if args.out else here
    collect = load_collect(repo)
    report = build(repo)

    if not args.check:
        for p in write(committed, report, collect.fmt):
            print(f"characterization: wrote {os.path.relpath(p, repo)}")
        rows = report["rows"]
        gaps = sum(1 for r in rows if r["declared_gap"])
        print(f"characterization: {len(rows)} spec rows, "
              f"{sum(1 for r in rows if r['status'] == 'pass')} meeting their limit, "
              f"{gaps} declared gap(s) with no evidence")
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        drift = []
        for fresh in write(tmp, report, collect.fmt):
            name = os.path.basename(fresh)
            old = os.path.join(committed, name)
            with open(fresh, "rb") as f:
                new_bytes = f.read()
            try:
                with open(old, "rb") as f:
                    old_bytes = f.read()
            except OSError as e:
                print(f"characterization: {name} is missing: {e}", file=sys.stderr)
                drift.append(name)
                continue
            if old_bytes != new_bytes:
                drift.append(name)
                print(f"---- {name}: committed (-) vs fresh (+) ----", file=sys.stderr)
                diff = difflib.unified_diff(
                    old_bytes.decode("utf-8", "replace").splitlines(),
                    new_bytes.decode("utf-8", "replace").splitlines(),
                    fromfile=f"committed/{name}", tofile=f"fresh/{name}", lineterm="")
                for i, line in enumerate(diff):
                    if i >= 80:
                        print("... (diff truncated)", file=sys.stderr)
                        break
                    print(line, file=sys.stderr)
        if drift:
            verb = "differs" if len(drift) == 1 else "differ"
            print(f"characterization: FAIL: the committed report is stale: "
                  f"{', '.join(drift)} {verb} from a fresh build. Regenerate and commit it "
                  f"in this same change:\n  sim/characterization/run.sh", file=sys.stderr)
            return 1
        print("characterization: committed report is fresh (report.md and report.json "
              "match a fresh build)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
