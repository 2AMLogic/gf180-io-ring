#!/usr/bin/env python3
"""Translate one subcircuit of the foundry gf180mcu_fd_io CDL into ngspice syntax.

    python3 -I cdl2ngspice.py <cdl-file> <subckt-name> [--check-against <spice-file>]

The CDL is not directly includable: it writes MOS as bare `M` cards and models as
`$[model]`, while sm141064.ngspice defines every device as a subcircuit. The rules
(exhaustive for gf180mcu_fd_io__bi_t; anything else is an error, never passed through):

    M<n> d g s b <model> k=v ...            ->  X<n> d g s b <model> k=v ...
    C<n> a b $[<model>] m= l= w=            ->  X<n> a b <model> m= c_length= c_width=
    R<n> a b $SUB=<s> $[<model>] $W= $L= .. ->  X<n> a b <s> <model> r_width= r_length= ..
    D<n> ...                                ->  unchanged (AREA/PJ are case-insensitive)

With --check-against the result is compared device by device (name, nodes, model,
parameter values) with the same subcircuit in the PDK's own `spice/` netlist, and a
difference exits non-zero. Output goes to stdout; the caller keeps it in the record.
"""
import re
import sys


def read_subckt(path, name):
    lines, grab = [], False
    for raw in open(path, encoding="utf-8", errors="replace"):
        raw = raw.rstrip("\n")
        if re.match(r"^\.subckt\s+" + re.escape(name) + r"\s", raw, re.I):
            grab = True
        if grab:
            lines.append(raw)
            if re.match(r"^\.ends", raw, re.I):
                return lines
    sys.exit(f"cdl2ngspice: subckt {name} not found in {path}")


def join_continuations(lines):
    out = []
    for ln in lines:
        if ln.startswith("+") and out:
            out[-1] += " " + ln[1:].strip()
        else:
            out.append(ln)
    return out


def translate_card(card):
    tok = card.split()
    kind = tok[0][0].upper()
    if kind == "M":
        return " ".join(["X" + tok[0][1:]] + tok[1:])
    if kind == "D":
        return card
    if kind == "C":
        m = re.match(r"^C(\S+)\s+(\S+)\s+(\S+)\s+\$\[(\w+)\]\s+(.*)$", card)
        if not m:
            sys.exit(f"cdl2ngspice: unrecognised C card: {card}")
        n, a, b, model, rest = m.groups()
        rest = re.sub(r"\bl=", "c_length=", rest)
        rest = re.sub(r"\bw=", "c_width=", rest)
        return f"X{n} {a} {b} {model} {rest}"
    if kind == "R":
        m = re.match(r"^R(\S+)\s+(\S+)\s+(\S+)\s+\$SUB=(\S+)\s+\$\[(\w+)\]\s+(.*)$", card)
        if not m:
            sys.exit(f"cdl2ngspice: unrecognised R card: {card}")
        n, a, b, sub, model, rest = m.groups()
        rest = re.sub(r"\$W=", "r_width=", rest)
        rest = re.sub(r"\$L=", "r_length=", rest)
        if "$" in rest:
            sys.exit(f"cdl2ngspice: unhandled CDL token in: {card}")
        return f"X{n} {a} {b} {sub} {model} {rest}"
    sys.exit(f"cdl2ngspice: unsupported card type '{kind}': {card}")


def translate(path, name):
    out = []
    for card in join_continuations(read_subckt(path, name)):
        if not card.strip() or card.lstrip().startswith("*"):
            continue
        if card.lower().startswith((".subckt", ".ends")):
            out.append(card)
        else:
            out.append(translate_card(card))
    return out


def norm_params(toks):
    return sorted(t.lower() for t in toks if "=" in t)


def device_map(cards):
    d = {}
    for c in cards:
        if c.startswith("."):
            continue
        t = c.split()
        d[t[0].upper()] = t
    return d


def check(translated, spice_path, name):
    ref = device_map(join_continuations(read_subckt(spice_path, name)))
    got = device_map(translated)
    bad = []
    if set(ref) != set(got):
        bad.append(f"device set differs: only-ref={sorted(set(ref) - set(got))[:5]} "
                   f"only-translated={sorted(set(got) - set(ref))[:5]}")
    for k in sorted(set(ref) & set(got)):
        a, b = ref[k], got[k]
        plain = lambda t: [x.lower() for x in t if "=" not in x]  # noqa: E731
        if plain(a) != plain(b) or norm_params(a) != norm_params(b):
            bad.append(f"{k}: ref `{' '.join(a)}` != translated `{' '.join(b)}`")
    return ref, bad


def main():
    args = sys.argv[1:]
    if len(args) not in (2, 4) or (len(args) == 4 and args[2] != "--check-against"):
        sys.exit(__doc__)
    cdl, name = args[0], args[1]
    out = translate(cdl, name)
    if len(args) == 4:
        ref, bad = check(out, args[3], name)
        if bad:
            for b in bad[:10]:
                print(f"cdl2ngspice: CHECK FAIL: {b}", file=sys.stderr)
            sys.exit(1)
        print(f"cdl2ngspice: check OK: {len(ref)} devices match {args[3]}", file=sys.stderr)
    print("\n".join(out))


if __name__ == "__main__":
    main()
