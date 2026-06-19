"""Build an entviz *casual model* for an input, using the reference
implementation's own internals (no algorithm reimplementation here, so the
experiment can never silently diverge from the shipped renderer).

A "casual model" is the subset of an entviz that a glancing human actually
perceives: the entviz background, and per grid-position the cell's nucleus
colour + surround (edge) colour, or — for a blank — its pill fill. We
deliberately DROP the per-box surround *pattern*: the empirical result that
motivated this experiment is that the 24-bit pattern is casually
imperceptible (half its boxes can toggle and a glance reads "same"), so it
must not count toward casual discriminability. We also carry two audit
channels (ellipse params, colour-bar ordering) so we can attribute residual
discriminability to them rather than over-claiming for the colour levers.

Everything fingerprint-derived that a lever might consume (per-cell ftok
quants, the digest, quartile ftoks, blank positions) is exposed on the model
so levers.py can transform colours without recomputing the algorithm.
"""

from dataclasses import dataclass, field

from entviz.entropy import parse, tokenize_entropy, BASE64URL
from entviz.fingerprint import (
    compute_fingerprint, tokenize_fingerprint,
    get_median_ftok, get_quartile_ftoks,
)
from entviz.layout import choose_grid, assign_cell_indices
from entviz.colors import (
    select_visual_style, get_nucleus_colors, closest_palette_color,
)
from entviz.pipeline import (
    v3_ellipse_params_from_digest, _two_bit_first_appearance,
)
import base64


@dataclass
class CellSlot:
    pos: int                 # grid cell index (0 = top-left, row-major)
    row: int
    col: int
    is_blank: bool
    token_index: int = -1    # -1 for blank
    nucleus: str = ""        # entropy-derived RGB (filled cells only)
    edge: str = ""           # baseline surround colour (filled cells only)
    blank_fill: str = ""     # baseline blank = "" (empty pill)
    ftok_quant: int = 0      # fingerprint bits available to a lever
    is_map_blank: bool = False


@dataclass
class CasualModel:
    input_text: str
    grid_cols: int
    grid_rows: int
    cell_count: int
    bg_color: str
    edge_palette: tuple            # the 4 non-bg palette colours
    digest: bytes
    slots: list = field(default_factory=list)   # indexed by grid position
    ellipse: dict = field(default_factory=dict)
    colorbar_order: tuple = ()     # band colours top→bottom (audit channel)
    quartiles: list = field(default_factory=list)  # [{rank,pos,quant}] in rank order
    is_truncated: bool = False


def _parse_front_end(text):
    """Mirror pipeline.render's parse/normalize so core + fingerprint_core
    match the shipped renderer exactly (incl. the unparseable→b64url
    fallback and the semantic-prefix fold)."""
    raw = text.strip()
    parsed = parse(raw)
    if parsed is None:
        core = base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")
        return core, BASE64URL, None, False
    fp_core_prefix = parsed.prefix if (parsed.prefix and parsed.prefix_semantic) else None
    return parsed.core, parsed.alphabet, fp_core_prefix, parsed.prefix_semantic


def build_model(text):
    core, alphabet, sem_prefix, _ = _parse_front_end(text)
    tokens, is_truncated = tokenize_entropy(core, alphabet)
    if not tokens:
        raise ValueError(f"no tokens for input {text!r}")
    token_count = len(tokens)

    fingerprint_core = (sem_prefix + core) if sem_prefix else core
    digest = compute_fingerprint(fingerprint_core)
    used_ftoks = tokenize_fingerprint(digest)[:token_count]

    grid = choose_grid(22 if is_truncated else token_count)
    cell_count = grid.cols * grid.rows
    median_ftok = get_median_ftok(used_ftoks)
    quartile_ftoks = get_quartile_ftoks(used_ftoks)
    style = select_visual_style(median_ftok)

    cell_of_token = assign_cell_indices(
        tokens, grid, median_token=median_ftok, sort_keys=used_ftoks)
    token_of_cell = {c: t for t, c in cell_of_token.items()}

    slots = []
    blank_positions = []
    for pos in range(cell_count):
        row, col = divmod(pos, grid.cols)
        t_idx = token_of_cell.get(pos)
        if t_idx is None:
            slots.append(CellSlot(pos, row, col, is_blank=True))
            blank_positions.append(pos)
            continue
        tok = tokens[t_idx]
        nucleus, _fg = get_nucleus_colors(tok.quant)
        edge = closest_palette_color(nucleus, style.edge_colors)
        slots.append(CellSlot(
            pos, row, col, is_blank=False, token_index=t_idx,
            nucleus=nucleus, edge=edge, ftok_quant=used_ftoks[t_idx].quant))
    # lowest-indexed blank carries the min/max map (spec): mark it so levers
    # can leave it alone (it already shows dots) if desired.
    if blank_positions:
        slots[min(blank_positions)].is_map_blank = True

    # quartile cell positions (rank order); a quartile ftok maps to its token
    # by shared index, then to that token's cell.
    quartiles = []
    for rank, qf in enumerate(quartile_ftoks):
        if qf is None:               # quartile fell in sort padding (small inputs)
            continue
        pos = cell_of_token.get(qf.index)
        if pos is not None:
            quartiles.append({"rank": rank, "pos": pos, "quant": qf.quant})

    # --- audit channels (already-avalanching; not the levers' target) ---
    ell = v3_ellipse_params_from_digest(digest)
    colorbar_order = tuple(_two_bit_first_appearance(digest, style.edge_colors))

    return CasualModel(
        input_text=text, grid_cols=grid.cols, grid_rows=grid.rows,
        cell_count=cell_count, bg_color=style.bg_color,
        edge_palette=tuple(style.edge_colors), digest=digest, slots=slots,
        ellipse=ell, colorbar_order=colorbar_order, quartiles=quartiles,
        is_truncated=is_truncated)
