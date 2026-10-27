#!/usr/bin/env python3
"""Cite a gpio-corners record as T1 item 5 evidence in the block manifest.

    python3 -I cite.py <recorddir> <manifest.json>

Sets evidence["5"] to one citation per `klt sim` envelope of the record (file path relative to
the repo root, the envelope's own provenance.input.content_hash, the spec rows it covers) and declares the row set and
the gaps under spec_rows["5"]. Everything else in the manifest is left as is. Regenerate
manifests/gf180-io-ring.signoff.json afterwards (manifests/README.md).
"""
import json
import os
import sys

MODES = ("5v", "3v3")
COVERS = {}
for m in MODES:
    COVERS[f"vol_{m}"] = [f"vol_{m}"]
    COVERS[f"voh_{m}"] = [f"voh_{m}"]
    COVERS[f"edges_{m}"] = [f"rise_{m}", f"fall_{m}"]
    COVERS[f"xfer_{m}"] = [f"vil_{m}", f"vih_{m}", f"hyst_{m}"]
    COVERS[f"cap_{m}"] = [f"cap_{m}"]
    COVERS[f"pullup_{m}_nominal"] = [f"pull_{m}"]
    COVERS[f"pulldown_{m}_nominal"] = [f"pull_{m}"]
COVERS["esd_pad"] = ["esd_pad_clamp"]

GAPS = [
    {"id": "esd_rail_clamp",
     "gap": "DVDD-DVSS rail clamp transient not evaluable on the batch fleet: its 600 um / 60-finger nfet_06v0 fails to bin under the fleet's ngspice-46 (see sim/gpio-corners/README.md)"},
    {"id": "esd_core_rail_clamp",
     "gap": "core VDD-VSS rail clamp (3.3 V devices) not simulated: the spec gives no voltage budget for it"},
    {"id": "esd_vdd_dvdd_coupling",
     "gap": "VDD/DVDD cross-domain coupling is not drawn yet (spec: decision record to follow)"},
]


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    rec, manifest = os.path.abspath(sys.argv[1]), sys.argv[2]
    root = os.path.dirname(os.path.dirname(os.path.abspath(manifest)))
    cites = []
    for stem, rows in COVERS.items():
        path = os.path.join(rec, "klt", stem + ".json")
        env = json.load(open(path))
        cites.append({"file": os.path.relpath(path, root),
                      "content_hash": env["provenance"]["input"]["content_hash"],
                      "rows": rows})
    ids = []
    for c in cites:
        for r in c["rows"]:
            if r not in ids:
                ids.append(r)
    m = json.load(open(manifest))
    m["evidence"]["5"] = cites
    m["spec_rows"] = {"5": [{"id": i} for i in ids] + GAPS}
    with open(manifest, "w") as f:
        json.dump(m, f, indent=2)
        f.write("\n")
    print(f"cite: {len(cites)} citations, {len(ids)} rows, {len(GAPS)} declared gaps")


if __name__ == "__main__":
    main()
