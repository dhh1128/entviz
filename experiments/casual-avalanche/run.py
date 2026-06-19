"""Casual-avalanche experiment runner.

Samples N independent one-character-neighbour pairs across the input types
entviz handles, builds both casual models with the reference implementation,
scores casual discriminability under each candidate lever, and writes
stratified miss-rates with Wilson 95% CIs.

Usage:
    uv run python experiments/casual-avalanche/run.py --n 100000 --seed 1
    uv run python experiments/casual-avalanche/run.py --selftest
"""
import argparse
import json
import math
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import build_model            # noqa: E402
from metrics import evaluate_pair, THRESHOLDS  # noqa: E402
from levers import LEVERS                 # noqa: E402
from ciede2000 import selftest as ciede_selftest  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
HEX = "0123456789abcdef"
B64URL = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


def _flip(core, alphabet, rng):
    """Return core with one random position changed to a different alphabet
    char (same length → same grid)."""
    i = rng.randrange(len(core))
    c = core[i]
    repl = rng.choice([x for x in alphabet if x != c])
    return core[:i] + repl + core[i + 1:]


def _uuid(rng):
    h = "".join(rng.choice(HEX) for _ in range(32))
    fmt = lambda s: f"{s[:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:]}"
    return ("uuid", fmt(h), lambda: fmt(_flip(h, HEX, rng)))


def _hexn(rng, nbytes, label):
    h = "".join(rng.choice(HEX) for _ in range(nbytes * 2))
    return (label, h, lambda: _flip(h, HEX, rng))


def _b64n(rng, nchars, label):
    s = "".join(rng.choice(B64URL) for _ in range(nchars))
    return (label, s, lambda: _flip(s, B64URL, rng))


B36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _lei_check(body18):
    n = int("".join(c if c.isdigit() else str(ord(c) - 55) for c in body18 + "00"))
    return f"{98 - (n % 97):02d}"


def _lei(rng):
    body = ("".join(rng.choice(B36) for _ in range(4)) + "00"
            + "".join(rng.choice(B36) for _ in range(12)))
    make = lambda b: b + _lei_check(b)

    def neighbor():
        pos = rng.choice([i for i in range(18) if i not in (4, 5)])
        repl = rng.choice([x for x in B36 if x != body[pos]])
        return make(body[:pos] + repl + body[pos + 1:])
    return ("lei", make(body), neighbor)


# (weight, generator) — weights set the type mix; "large" (>512 bit) is its
# own stratum so the fingerprint-cell regime is reported separately.
GENERATORS = [
    (3, lambda r: _uuid(r)),
    (2, lambda r: _lei(r)),                       # 18-char base36, 1 (map) blank
    (2, lambda r: _hexn(r, 8, "hex64")),          # small, single-blank
    (2, lambda r: _hexn(r, 9, "hex72")),          # small, single-blank
    (2, lambda r: _hexn(r, 16, "hex128")),        # full grid, no blanks
    (2, lambda r: _hexn(r, 32, "hex256")),
    (2, lambda r: _hexn(r, 64, "hex512")),
    (2, lambda r: _b64n(r, 43, "b64url256")),
    (1, lambda r: _hexn(r, 200, "large1600")),    # >512 bit → truncated layout
]


def _pick_gen(rng):
    total = sum(w for w, _ in GENERATORS)
    x = rng.randrange(total)
    for w, g in GENERATORS:
        if x < w:
            return g
        x -= w


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    center = (p + z * z / (2 * n)) / d
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return (p, max(0.0, center - half), min(1.0, center + half))


def _blank_acc():
    return {"n": 0, "color_miss": 0, "whole_miss": 0, "singleton_sum": 0,
            "has_singleton": 0}


def run(n, seed):
    rng = random.Random(seed)
    # strata keys: ("all",), ("type", <type>), ("bg", same|diff)
    # each stratum -> lever -> T -> accumulator
    acc = {}

    def bucket(stratum, lever, T):
        return acc.setdefault(stratum, {}).setdefault(lever, {}).setdefault(T, _blank_acc())

    audit = {"ellipse_moved": 0, "colorbar_changed": 0}
    done = 0
    skipped = 0
    t0 = time.time()
    while done < n:
        label, text, neighbor = _pick_gen(rng)(rng)
        nb = neighbor()
        # reconstruct typed neighbour input matching the generator's framing
        if label == "uuid":
            text_b = nb  # _uuid's flip already reformats with dashes
        else:
            text_b = nb
        try:
            ma = build_model(text)
            mb = build_model(text_b)
        except Exception:
            skipped += 1
            continue
        if ma.cell_count != mb.cell_count:
            skipped += 1
            continue

        res = evaluate_pair(ma, mb)
        audit["ellipse_moved"] += res["ellipse_moved"]
        audit["colorbar_changed"] += res["colorbar_changed"]
        bg_stratum = "same" if ma.bg_color == mb.bg_color else "diff"
        strata = [("all",), ("type", label), ("bg", bg_stratum)]
        for lever in LEVERS:
            for T in THRESHOLDS:
                cell = res[lever][T]
                for st in strata:
                    a = bucket(st, lever, T)
                    a["n"] += 1
                    a["color_miss"] += cell["color_miss"]
                    a["whole_miss"] += cell["whole_miss"]
                    a["singleton_sum"] += cell["singletons"]
                    a["has_singleton"] += 1 if cell["singletons"] > 0 else 0
        done += 1
        if done % 20000 == 0:
            print(f"  {done}/{n} pairs ({done/(time.time()-t0):.0f}/s)", flush=True)

    return acc, audit, skipped, time.time() - t0


def _fmt_rate(k, n):
    p, lo, hi = wilson(k, n)
    return f"{100*p:6.2f}%  [{100*lo:5.2f}, {100*hi:5.2f}]"


def write_results(acc, audit, skipped, elapsed, n, seed):
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    raw = {"n": n, "seed": seed, "elapsed_s": elapsed, "skipped": skipped,
           "audit": audit, "thresholds": list(THRESHOLDS), "strata": {}}
    for st, levers in acc.items():
        key = "|".join(st)
        raw["strata"][key] = {}
        for lever, Ts in levers.items():
            raw["strata"][key][lever] = {}
            for T, a in Ts.items():
                raw["strata"][key][lever][str(T)] = a
    with open(os.path.join(HERE, "results", "raw.json"), "w") as fh:
        json.dump(raw, fh, indent=2)

    Tref = 10.0
    lines = []
    lines.append(f"# Casual-avalanche results\n")
    lines.append(f"- pairs: **{n}**  seed: {seed}  skipped(resampled): {skipped}  "
                 f"elapsed: {elapsed:.1f}s\n")
    lines.append(f"- audit channels (fraction of pairs that move): "
                 f"ellipse {100*audit['ellipse_moved']/n:.1f}%, "
                 f"colour-bar order {100*audit['colorbar_changed']/n:.1f}%\n")
    lines.append(f"\nMiss-rate = fraction of one-char neighbours a glance would "
                 f"call identical. Lower is better. ΔE00 threshold T={Tref:g} "
                 f"('clear at a glance'); Wilson 95% CI in brackets.\n")

    def table(stratum, title):
        if stratum not in acc:
            return
        lines.append(f"\n## {title}  (n={acc[stratum][LEVERS[0]][Tref]['n']})\n")
        lines.append("| lever | colour-miss | whole-miss | mean singletons | ≥1 singleton |")
        lines.append("|---|---|---|---|---|")
        for lever in LEVERS:
            a = acc[stratum][lever][Tref]
            ms = a["singleton_sum"] / a["n"] if a["n"] else 0
            hs = 100 * a["has_singleton"] / a["n"] if a["n"] else 0
            lines.append(f"| {lever} | {_fmt_rate(a['color_miss'], a['n'])} | "
                         f"{_fmt_rate(a['whole_miss'], a['n'])} | {ms:.2f} | {hs:.1f}% |")

    table(("all",), "All pairs")
    table(("bg", "same"), "Background-unchanged stratum (the hard ¼)")
    table(("bg", "diff"), "Background-changed stratum")

    # threshold sensitivity on the headline stratum
    lines.append("\n## Threshold sensitivity — colour-miss, background-unchanged stratum\n")
    lines.append("| lever | " + " | ".join(f"T={int(T)}" for T in THRESHOLDS) + " |")
    lines.append("|---|" + "---|" * len(THRESHOLDS))
    for lever in LEVERS:
        cells = []
        for T in THRESHOLDS:
            a = acc[("bg", "same")][lever][T]
            p, _, _ = wilson(a["color_miss"], a["n"])
            cells.append(f"{100*p:.2f}%")
        lines.append(f"| {lever} | " + " | ".join(cells) + " |")

    # per-type colour-miss: baseline vs quartile-only vs the LOCKED hybrid.
    lines.append("\n## Per-type colour-miss (all pairs, T=10) — locked `hybrid`\n")
    lines.append("| type | baseline | quartile only | hybrid (locked) |")
    lines.append("|---|---|---|---|")
    for st in sorted(k for k in acc if k[0] == "type"):
        b = acc[st]["baseline"][Tref]
        q = acc[st]["quartile"][Tref]
        h = acc[st]["hybrid"][Tref]
        pb, _, _ = wilson(b["color_miss"], b["n"])
        pq, _, _ = wilson(q["color_miss"], q["n"])
        ph, _, _ = wilson(h["color_miss"], h["n"])
        lines.append(f"| {st[1]} (n={b['n']}) | {100*pb:.2f}% | {100*pq:.2f}% | {100*ph:.2f}% |")

    out = "\n".join(lines) + "\n"
    with open(os.path.join(HERE, "results", "RESULTS.md"), "w") as fh:
        fh.write(out)
    print(out)


def selftest():
    print(ciede_selftest())
    A = "550e8400-e29b-41d4-a716-446655440000"
    B = "550e8400-e29b-41d5-a716-446655440000"
    ma, mb = build_model(A), build_model(B)
    assert ma.bg_color == mb.bg_color == "#ffffff", "demo pair should be white/white"
    res = evaluate_pair(ma, mb)
    base = res["baseline"][10.0]
    comb = res["combined"][10.0]
    print(f"demo pair (bg unchanged): baseline color_miss={base['color_miss']} "
          f"singletons={base['singletons']}; combined color_miss={comb['color_miss']} "
          f"singletons={comb['singletons']}")
    # the whole point: baseline misses this pair on colour, combined should not
    assert base["color_miss"] is True, "baseline should casually miss the demo pair"
    assert comb["color_miss"] is False, "combined should casually catch the demo pair"
    print("model + metric selftest OK")
    # tiny aggregate smoke
    acc, audit, skipped, el = run(300, seed=7)
    a_base = acc[("bg", "same")]["baseline"][10.0]
    a_comb = acc[("bg", "same")]["combined"][10.0]
    print(f"smoke n=300 bg-same: baseline miss {a_base['color_miss']}/{a_base['n']}, "
          f"combined miss {a_comb['color_miss']}/{a_comb['n']}, skipped {skipped}")
    print("selftest complete")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
    else:
        acc, audit, skipped, elapsed = run(args.n, args.seed)
        write_results(acc, audit, skipped, elapsed, args.n, args.seed)
