"""CIEDE2000 perceptual color difference (ΔE00), sRGB in.

Self-contained so the experiment has no dependency on the entviz color
module (which uses a cheap weighted-RGB stand-in). We use the full
CIEDE2000 metric here because the paper's casual-discriminability claims
need a defensible perceptual yardstick, not an approximation.

sRGB (D65) → linear → XYZ → CIELAB → ΔE00. Validated in `selftest()`
against Sharma, Wu & Dalal (2005) reference vectors.
"""

import math


def _srgb_to_linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def hex_to_lab(h):
    r, g, b = (_srgb_to_linear(v) for v in _hex_to_rgb(h))
    # linear sRGB → XYZ (D65)
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    # normalize by D65 white
    xn, yn, zn = 0.95047, 1.0, 1.08883
    x, y, z = x / xn, y / yn, z / zn

    def f(t):
        return t ** (1 / 3) if t > 216 / 24389 else (841 / 108) * t + 4 / 29

    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def ciede2000_lab(lab1, lab2):
    """ΔE00 between two CIELAB triples."""
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    kL = kC = kH = 1.0

    C1 = math.hypot(a1, b1)
    C2 = math.hypot(a2, b2)
    Cbar = (C1 + C2) / 2.0
    G = 0.5 * (1 - math.sqrt(Cbar ** 7 / (Cbar ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)

    def hp(ap, bp):
        if ap == 0 and bp == 0:
            return 0.0
        h = math.degrees(math.atan2(bp, ap))
        return h + 360 if h < 0 else h

    h1p, h2p = hp(a1p, b1), hp(a2p, b2)

    dLp = L2 - L1
    dCp = C2p - C1p
    if C1p * C2p == 0:
        dhp = 0.0
    else:
        dh = h2p - h1p
        if dh > 180:
            dh -= 360
        elif dh < -180:
            dh += 360
        dhp = dh
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp) / 2)

    Lbarp = (L1 + L2) / 2
    Cbarp = (C1p + C2p) / 2
    if C1p * C2p == 0:
        hbarp = h1p + h2p
    else:
        if abs(h1p - h2p) > 180:
            hbarp = (h1p + h2p + 360) / 2 if (h1p + h2p) < 360 else (h1p + h2p - 360) / 2
        else:
            hbarp = (h1p + h2p) / 2

    T = (1 - 0.17 * math.cos(math.radians(hbarp - 30))
         + 0.24 * math.cos(math.radians(2 * hbarp))
         + 0.32 * math.cos(math.radians(3 * hbarp + 6))
         - 0.20 * math.cos(math.radians(4 * hbarp - 63)))
    dtheta = 30 * math.exp(-(((hbarp - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cbarp ** 7 / (Cbarp ** 7 + 25 ** 7))
    Sl = 1 + (0.015 * (Lbarp - 50) ** 2) / math.sqrt(20 + (Lbarp - 50) ** 2)
    Sc = 1 + 0.045 * Cbarp
    Sh = 1 + 0.015 * Cbarp * T
    Rt = -math.sin(math.radians(2 * dtheta)) * Rc

    return math.sqrt(
        (dLp / (kL * Sl)) ** 2
        + (dCp / (kC * Sc)) ** 2
        + (dHp / (kH * Sh)) ** 2
        + Rt * (dCp / (kC * Sc)) * (dHp / (kH * Sh))
    )


def delta_e(hex1, hex2):
    """ΔE00 between two #rrggbb colors."""
    if hex1 == hex2:
        return 0.0
    return ciede2000_lab(hex_to_lab(hex1), hex_to_lab(hex2))


def selftest():
    # Sharma et al. (2005) Lab reference pairs → expected ΔE00.
    cases = [
        ((50, 2.6772, -79.7751), (50, 0, -82.7485), 2.0425),
        ((50, 3.1571, -77.2803), (50, 0, -82.7485), 2.8615),
        ((50, 2.8361, -74.0200), (50, 0, -82.7485), 3.4412),
        ((50, -1.3802, -84.2814), (50, 0, -82.7485), 1.0000),
        ((50, 2.5, 0), (73, 25, -18), 27.1492),
        ((50, 2.5, 0), (50, 3.1736, 0.5854), 1.0000),
    ]
    worst = 0.0
    for lab1, lab2, exp in cases:
        got = ciede2000_lab(lab1, lab2)
        worst = max(worst, abs(got - exp))
        assert abs(got - exp) < 1e-3, f"{lab1}->{lab2}: got {got}, want {exp}"
    # sanity: identical palette colors → 0; gold vs blue → very large
    assert delta_e("#e7be00", "#e7be00") == 0.0
    assert delta_e("#e7be00", "#2f3fbf") > 60
    return f"ciede2000 selftest OK (worst abs err {worst:.2e})"


if __name__ == "__main__":
    print(selftest())
