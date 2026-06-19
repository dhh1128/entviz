"""Does blank-colouring help SMALL inputs that carry blanks (LEI, small hex)?

Adds valid LEIs and a sweep of small hex sizes, and reports — in the
background-unchanged stratum — baseline vs the two blank levers
(`blanks` = skip map blank, `blanks_all` = incl. map blank) vs quartile vs
combined_all. Also prints mean blank count and how often the lone blank IS
the map blank (the case my first lever silently skipped).
"""
import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import build_model
from metrics import evaluate_pair
from levers import LEVERS

B36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
HEX = "0123456789abcdef"
T = 10.0


def _lei_num(s):
    return int("".join(c if c.isdigit() else str(ord(c) - 55) for c in s))


def _lei_check(body18):
    return f"{98 - (_lei_num(body18 + '00') % 97):02d}"


def gen_lei(rng):
    body = ("".join(rng.choice(B36) for _ in range(4)) + "00"
            + "".join(rng.choice(B36) for _ in range(12)))
    make = lambda b: b + _lei_check(b)

    def neighbor():
        positions = [i for i in range(18) if i not in (4, 5)]
        i = rng.choice(positions)
        repl = rng.choice([x for x in B36 if x != body[i]])
        return make(body[:i] + repl + body[i + 1:])
    return ("lei", make(body), neighbor)


def gen_hex(nbytes):
    def g(rng):
        h = "".join(rng.choice(HEX) for _ in range(nbytes * 2))

        def neighbor():
            i = rng.randrange(len(h))
            repl = rng.choice([x for x in HEX if x != h[i]])
            return h[:i] + repl + h[i + 1:]
        return (f"hex{nbytes}B", h, neighbor)
    return g


GENS = [gen_lei] + [gen_hex(nb) for nb in (8, 9, 10, 11, 12, 13, 14, 16, 20, 24)]

rng = random.Random(7)
stats = {}
N_PER = 6000
for gen in GENS:
    label = gen(rng)[0]
    d = stats.setdefault(label, {k: 0 for k in
        ["n", "blanks_sum", "lone_map", "bg_same"] + [f"miss_{lv}" for lv in LEVERS]})
    got = 0
    while got < N_PER:
        _, text, neighbor = gen(rng)
        try:
            ma = build_model(text)
            mb = build_model(neighbor())
        except Exception:
            continue
        if ma.cell_count != mb.cell_count:
            continue
        got += 1
        nb = sum(1 for s in ma.slots if s.is_blank)
        d["n"] += 1
        d["blanks_sum"] += nb
        if nb == 1:
            d["lone_map"] += 1   # a single blank is always the map blank
        if ma.bg_color != mb.bg_color:
            continue
        d["bg_same"] += 1
        res = evaluate_pair(ma, mb)
        for lv in LEVERS:
            d[f"miss_{lv}"] += int(res[lv][T]["color_miss"])

cols = ["baseline", "quartile", "blanks_all", "combined", "combined_all"]
print(f"T={T}, miss columns = colour-miss in background-unchanged stratum\n")
print(f"{'type':<9} {'meanBlank':>9} {'%1blank':>7} {'bgSameN':>7} | "
      + " ".join(f"{c:>11}" for c in cols))
for label, d in stats.items():
    m = d["bg_same"] or 1
    pct = lambda lv: f"{100*d[f'miss_{lv}']/m:.1f}%"
    print(f"{label:<9} {d['blanks_sum']/d['n']:>9.2f} {100*d['lone_map']/d['n']:>6.0f}% "
          f"{d['bg_same']:>7} | " + " ".join(f"{pct(c):>11}" for c in cols))
