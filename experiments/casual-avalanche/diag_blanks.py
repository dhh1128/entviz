"""Diagnostic: why does the blank-colouring lever barely move the miss rate?

Hypothesis: (a) the inputs that suffer casual collisions (UUID, hex-128) are
full grids with ZERO blank cells, so the blank lever has nothing to colour
there; and (b) the inputs that DO have blanks almost never collide anyway,
because a fingerprint-driven blank *position* shift already cascades the grid.

Prints, per type: mean blank count, and (background-unchanged stratum) the
baseline / blanks / quartile colour-miss, plus how often blanks even moved.
"""
import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import build_model
from metrics import evaluate_pair
from run import _pick_gen, _flip, HEX, B64URL  # reuse generators

rng = random.Random(42)
T = 10.0
stats = {}   # type -> dict


def bump(label, **kw):
    d = stats.setdefault(label, {"n": 0, "blanks_sum": 0, "bg_same": 0,
                                 "base_miss": 0, "blank_miss": 0, "quart_miss": 0,
                                 "blank_positions_moved": 0, "has_any_blank": 0})
    for k, v in kw.items():
        d[k] += v


N = 40000
done = 0
while done < N:
    label, text, neighbor = _pick_gen(rng)(rng)
    try:
        ma = build_model(text)
        mb = build_model(neighbor())
    except Exception:
        continue
    if ma.cell_count != mb.cell_count:
        continue
    done += 1
    nblank = sum(1 for s in ma.slots if s.is_blank)
    blanks_a = {s.pos for s in ma.slots if s.is_blank}
    blanks_b = {s.pos for s in mb.slots if s.is_blank}
    bump(label, n=1, blanks_sum=nblank, has_any_blank=1 if nblank else 0)
    if ma.bg_color != mb.bg_color:
        continue  # only the hard (background-unchanged) stratum below
    res = evaluate_pair(ma, mb)
    bump(label, bg_same=1,
         base_miss=int(res["baseline"][T]["color_miss"]),
         blank_miss=int(res["blanks"][T]["color_miss"]),
         quart_miss=int(res["quartile"][T]["color_miss"]),
         blank_positions_moved=1 if blanks_a != blanks_b else 0)

print(f"n={done}, T={T}, background-unchanged stratum for miss columns\n")
print(f"{'type':<11} {'mean_blanks':>11} {'%has_blank':>10} | "
      f"{'bg=same n':>9} {'base':>7} {'blanks':>7} {'quart':>7} {'blanksMoved':>11}")
for label in sorted(stats):
    d = stats[label]
    n = d["n"]; m = d["bg_same"]
    mb_ = lambda k: (100*d[k]/m if m else 0)
    print(f"{label:<11} {d['blanks_sum']/n:>11.2f} {100*d['has_any_blank']/n:>9.0f}% | "
          f"{m:>9} {mb_('base_miss'):>6.1f}% {mb_('blank_miss'):>6.1f}% "
          f"{mb_('quart_miss'):>6.1f}% {(100*d['blank_positions_moved']/m if m else 0):>10.0f}%")
