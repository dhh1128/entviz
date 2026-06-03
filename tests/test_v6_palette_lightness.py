"""
v6 palette lightness / CVD floor test (closes adversarial finding F3's
"add a CVD snapshot test either way").

The palette is spaced primarily along CIELAB lightness (L*), because
lightness is the only channel that survives color-vision deficiency,
monochrome rendering, and CSS color filtering. This test pins that design:

  1. Under NORMAL vision every pair of palette colors is separated by
     ΔL* >= 20 (the design floor). Gold sits at the maximin point between
     its neighbours, so white/gold ≈ gold/red.

  2. Under simulated dichromacy the floor CANNOT hold for every pair --
     red darkens under protanopia until red/blue collapse, and no gold
     choice fixes it (see spec palette-rationale honesty caveat). Rather
     than pretend otherwise, we ENUMERATE the pairs allowed to fall below
     20 per CVD type and pin their values. A regression that introduces a
     new sub-floor pair, or worsens a known one, fails here.

CVD simulation uses the Machado, Oliveira & Fernandes (2009) severity-1.0
matrices (the same model cited in the paper). All math is pure-Python so
the test carries no numpy/render dependency.
"""
import itertools

from entviz.colors import POSSIBLE_EDGE_COLORS

# POSSIBLE_EDGE_COLORS is [white, gold, red, blue, black] by position.
NAMES = ["white", "gold", "red", "blue", "black"]
PALETTE = dict(zip(NAMES, POSSIBLE_EDGE_COLORS))

DESIGN_FLOOR = 20.0

# Machado, Oliveira & Fernandes 2009, severity 1.0 (dichromacy).
CVD_MATRICES = {
    "protan": [[0.152286, 1.052583, -0.204868],
               [0.114503, 0.786281, 0.099216],
               [-0.003882, -0.048116, 1.051998]],
    "deutan": [[0.367322, 0.860646, -0.227968],
               [0.280085, 0.672501, 0.047413],
               [-0.011820, 0.042940, 0.968881]],
    "tritan": [[1.255528, -0.076749, -0.178779],
               [-0.078411, 0.930809, 0.147602],
               [0.004733, 0.691367, 0.303900]],
}

# Pairs permitted to fall below DESIGN_FLOOR under each CVD type, with the
# expected ΔL* (the unavoidable shortfall) and a tolerance. Documented in
# docs/spec.md's palette rationale; these rely on the retained colour axis
# plus the color-bar letters (w/g/r/b/k) for discrimination.
CVD_EXCEPTIONS = {
    "protan": {frozenset({"red", "blue"}): 7.4},   # red darkens onto blue
    "deutan": {frozenset({"gold", "red"}): 17.2},
    "tritan": {frozenset({"red", "blue"}): 15.7},
}
EXCEPTION_TOL = 1.5


def _linear(hex_color):
    def ungamma(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return [ungamma(int(hex_color[i:i + 2], 16)) for i in (1, 3, 5)]


def _lstar_from_Y(Y):
    return 116 * (Y ** (1 / 3)) - 16 if Y > 0.008856 else 903.3 * Y


def lstar(hex_color):
    r, g, b = _linear(hex_color)
    return _lstar_from_Y(0.2126 * r + 0.7152 * g + 0.0722 * b)


def lstar_cvd(hex_color, cvd):
    if cvd == "normal":
        return lstar(hex_color)
    lin = _linear(hex_color)
    m = CVD_MATRICES[cvd]
    v = [max(0.0, min(1.0, sum(m[i][j] * lin[j] for j in range(3))))
         for i in range(3)]
    return _lstar_from_Y(0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2])


def _pairs(cvd):
    L = {n: lstar_cvd(PALETTE[n], cvd) for n in NAMES}
    return {frozenset({a, b}): abs(L[a] - L[b])
            for a, b in itertools.combinations(NAMES, 2)}


def test_palette_order_is_white_gold_red_blue_black():
    """The fixed positional contract this test relies on."""
    assert PALETTE["white"] == "#ffffff" and PALETTE["black"] == "#000000"
    Ls = [lstar(PALETTE[n]) for n in NAMES]
    assert Ls == sorted(Ls, reverse=True), "palette must descend in L*"


def test_normal_vision_every_pair_at_least_20():
    """The F3 design floor: no two palette colours are closer than ΔL* 20
    under normal vision."""
    worst = min(_pairs("normal").items(), key=lambda kv: kv[1])
    assert worst[1] >= DESIGN_FLOOR, (
        f"normal-vision min pair {set(worst[0])} ΔL*={worst[1]:.1f} "
        f"< {DESIGN_FLOOR}")


def test_gold_sits_at_the_maximin():
    """Gold's lightness is the balance point between white and red:
    white/gold ≈ gold/red. A regression that un-darkens gold breaks this."""
    p = _pairs("normal")
    wg = p[frozenset({"white", "gold"})]
    gr = p[frozenset({"gold", "red"})]
    assert abs(wg - gr) <= 2.0, f"gold off maximin: white/gold={wg:.1f} gold/red={gr:.1f}"
    assert min(wg, gr) >= DESIGN_FLOOR


def test_cvd_subfloor_pairs_are_exactly_the_documented_exceptions():
    """Under each dichromacy, the ONLY pairs below the 20 floor are the
    documented, unavoidable ones, and they hold their pinned ΔL* values.
    Catches both a new CVD collapse and a regression of a known one."""
    for cvd, allowed in CVD_EXCEPTIONS.items():
        p = _pairs(cvd)
        below = {pair: d for pair, d in p.items() if d < DESIGN_FLOOR}
        assert set(below) == set(allowed), (
            f"{cvd}: sub-20 pairs {[set(x) for x in below]} != "
            f"documented {[set(x) for x in allowed]}")
        for pair, expected in allowed.items():
            assert abs(below[pair] - expected) <= EXCEPTION_TOL, (
                f"{cvd} {set(pair)} ΔL*={below[pair]:.1f}, "
                f"expected ≈{expected}")
