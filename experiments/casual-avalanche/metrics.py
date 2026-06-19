"""Casual-discriminability metric for a pair of entvizes.

Operationalizes "would a glancing human see a difference?" conservatively
and transparently, from the casual colour field (model.py) under a given
lever (levers.py):

  colour-distinguishable  := the background changed, OR some grid position's
                             casually-salient colour/structure changed by more
                             than a ΔE00 glance threshold T. (Surround PATTERN
                             is excluded by construction — see model.py.)
  whole-distinguishable    := colour-distinguishable OR an audit channel moved
                             (ellipse params, or colour-bar band order).

We report the *miss* rates (= not distinguishable): the fraction of
one-character neighbours that slip past a glance. T is swept so no conclusion
rests on a single cutoff. Palette colours are tens of ΔE apart, so any
discrete palette change clears every threshold; T essentially governs only
the continuous nucleus channel.
"""

from ciede2000 import delta_e
from levers import LEVERS, color_field

THRESHOLDS = (5.0, 10.0, 20.0)   # ΔE00: "visible", "clear at a glance", "obvious"


def _pos_changed(pa, pb, T):
    # structure change (cell<->blank, or filled<->empty) is always salient
    if len(pa) != len(pb):
        return True
    return any(delta_e(ca, cb) > T for ca, cb in zip(pa, pb))


def _ellipse_moved(ea, eb):
    if ea.get("anchor_index") != eb.get("anchor_index"):
        return True
    # a >=2/15 step change (~13% of the parameter range) reads as a visibly
    # different ellipse; smaller jitter may not.
    for k in ("rx_step", "ry_step", "rotation_step"):
        if abs(ea.get(k, 0) - eb.get(k, 0)) >= 2:
            return True
    return False


def evaluate_pair(ma, mb):
    """Return {lever: {T: {color_miss, whole_miss, singletons}}} plus the
    two audit-channel booleans. Assumes ma, mb share grid dimensions
    (true for a same-length one-character neighbour)."""
    assert ma.cell_count == mb.cell_count, "pair must share grid size"
    ellipse_moved = _ellipse_moved(ma.ellipse, mb.ellipse)
    colorbar_changed = ma.colorbar_order != mb.colorbar_order
    audit_moved = ellipse_moved or colorbar_changed

    out = {"ellipse_moved": ellipse_moved, "colorbar_changed": colorbar_changed}
    for lever in LEVERS:
        bga, pa = color_field(ma, lever)
        bgb, pb = color_field(mb, lever)
        per_T = {}
        for T in THRESHOLDS:
            bg_changed = delta_e(bga, bgb) > T
            singletons = sum(
                _pos_changed(pa[p], pb[p], T) for p in range(ma.cell_count))
            color_distinguishable = bg_changed or singletons > 0
            per_T[T] = {
                "color_miss": not color_distinguishable,
                "whole_miss": not (color_distinguishable or audit_moved),
                "singletons": singletons,
                "bg_changed": bg_changed,
            }
        out[lever] = per_T
    return out
