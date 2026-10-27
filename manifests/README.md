# Block manifest and tier-verdict record

This directory holds this block's `klt signoff` input and its committed
output: the machine-readable gap-to-T1 checklist.

## Files

- **`gf180-io-ring.json`**: the block manifest (`block: gf180-io-ring`,
  `kind: analog`). Evidence is cited here one item at a time as it lands, each
  pinned to the cited artifact's `content_hash`. Item 1 cites
  `evidence/item1.json` and item 10 cites `item10-attestation.json`; every
  other item is still `unmet` / `no_evidence`.
- **`evidence/item1.json`**: the item-1 attestation envelope, produced from
  `design/item1-inventory.json` (`klt signoff --attest 1`, needs `klt` >= 0.8.0,
  hence the pin). Regenerate it whenever a design source or netlist changes; see
  [`design/README.md`](../design/README.md).
- **`design-evidence-tiers.md`**: the T1-T4 checklist the grader parses.
  Vendored **byte-identical** from
  [`2AMLogic/klayout-tools@31a3e3c41c08bbd58719e0b99a3b6d19beb9be63`](https://github.com/2AMLogic/klayout-tools/blob/31a3e3c41c08bbd58719e0b99a3b6d19beb9be63/docs/design-evidence-tiers.md)
  `docs/design-evidence-tiers.md` (upstream is MIT-licensed; this repo's
  license does not relicense the vendored copy). When upstream moves,
  re-vendor and regenerate the record in the same PR.
- **`item10-inventory.json`** / **`item10-attestation.json`**: the T1 item 10
  (repo hygiene) attestation inventory and its committed envelope, cited by the
  manifest. Regenerate the envelope with the command below.
- **`gf180-io-ring.signoff.json`**: the verdict of record, the committed
  output of the command below. Never hand-edit it.

## Regenerate

```console
uvx --from "klayout-tools==0.8.0" klt signoff \
    --manifest manifests/gf180-io-ring.json \
    --tiers-doc manifests/design-evidence-tiers.md \
    --format json > manifests/gf180-io-ring.signoff.json
```

Attest item 10 (needs klt >= 0.8.0; run this first, then regenerate the record
above, because the manifest cites the envelope's `content_hash`):

```console
uvx --from "klayout-tools==0.8.0" klt signoff --attest 10 \
    --inventory manifests/item10-inventory.json \
    -o manifests/item10-attestation.json
```

Exit `3` means at least one T1 item is `unmet` (a valid run); `0` means all
are met. Any change that affects the verdict (new evidence, a manifest edit,
a vendored-doc bump, a `klt` pin bump) regenerates and commits the record in
the same PR.

CI ([`.github/workflows/signoff.yml`](../.github/workflows/signoff.yml))
re-runs this on every push and byte-compares against the committed record.
