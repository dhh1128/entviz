"""Candidate casual-avalanche levers, applied as colour-field transforms on
a CasualModel. None of these touch the shipped renderer — they let us
*measure* each lever's effect before committing any of it to the spec.

A "colour field" is what the metric consumes: per grid position, the set of
casually-salient colour patches. We model each filled cell as two patches
(nucleus, surround) and each blank as one (pill fill, or None when empty).
The entviz background is a separate global patch.

Levers (all FINGERPRINT-driven, so they avalanche on any input change):

  baseline   : shipped behaviour — surround = nearest palette to nucleus
               (entropy echo); blanks are empty pills.
  topleft    : the top-left cell's surround colour is taken from the
               fingerprint (2 ftok bits → 4-colour edge palette). Targets the
               first-fixation point.
  quartile   : the 1st & 2nd quartile cells' surround colours are taken from
               the fingerprint (2 quartile-ftok bits each). A few discordant
               colour singletons that move with the fingerprint.
  blanks     : every non-map blank's pill is filled from the fingerprint
               (2 digest bits → 4-colour edge palette, never the bg so it is
               always visible). Pill outline retained (preserves "gap"
               semantics); we model the fill as the salient patch.
  combined   : topleft + quartile + blanks together.

Bit selection: a lever reads 2 bits and indexes the 4-entry edge palette.
We use bits (q & 3). The background uses the *median* ftok's low 2 bits, so a
per-cell ftok's low 2 bits are an independent draw under avalanche.
"""

LEVERS = ["baseline", "topleft", "quartile", "blanks", "blanks_all",
          "combined", "combined_all", "hybrid"]

# `hybrid` is the LOCKED design: topleft + quartile(1st,2nd) + hybrid blanks
# (colour the map blank only when it is the SOLE blank — so single-blank small
# inputs like LEI/small-hex get the avalanche — otherwise keep the map blank
# white as a findable anchor and colour its siblings).


def _palette_pick(palette4, bits):
    return palette4[bits & 3]


def color_field(model, lever):
    """Return (bg, patches) where patches maps grid-position -> list[hex].

    Only casually-salient colour is included; the surround *pattern* (which
    boxes are filled) is intentionally excluded — it is casually
    imperceptible and must not inflate discriminability.
    """
    pal = model.edge_palette
    # start from baseline patches
    patches = {}
    for s in model.slots:
        if s.is_blank:
            patches[s.pos] = []  # empty pill: no salient colour
        else:
            patches[s.pos] = [s.nucleus, s.edge]

    if lever == "baseline":
        return model.bg_color, patches

    apply_topleft = lever in ("topleft", "combined", "combined_all", "hybrid")
    apply_quart = lever in ("quartile", "combined", "combined_all", "hybrid")
    # blank mode: None | "skip_map" | "all" | "hybrid"
    blank_mode = ({"blanks": "skip_map", "combined": "skip_map",
                   "blanks_all": "all", "combined_all": "all",
                   "hybrid": "hybrid"}).get(lever)
    n_blank = sum(1 for s in model.slots if s.is_blank)

    if apply_topleft:
        s0 = model.slots[0]
        if not s0.is_blank:
            patches[0] = [s0.nucleus, _palette_pick(pal, s0.ftok_quant)]

    if apply_quart:
        for q in model.quartiles:
            if q["rank"] in (0, 1):
                pos = q["pos"]
                s = model.slots[pos]
                if not s.is_blank:
                    patches[pos] = [s.nucleus, _palette_pick(pal, q["quant"])]

    if blank_mode:
        ordinal = 0
        for s in model.slots:
            if not s.is_blank:
                continue
            if s.is_map_blank:
                # skip_map: never colour. all: always colour. hybrid: colour
                # only when it is the sole blank (else keep it the white anchor).
                if blank_mode == "skip_map":
                    continue
                if blank_mode == "hybrid" and n_blank > 1:
                    continue
            byte = model.digest[40 + (ordinal % 20)]
            patches[s.pos] = [_palette_pick(pal, byte)]
            ordinal += 1

    return model.bg_color, patches
