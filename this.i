# Entviz Intent File
# Component: entviz
# Format: intent code

Entviz = goal:
  id: e1ntv1z0
  why: >
    Provide a human-friendly way to visually compare high-entropy strings.
    The goal is to allow untrained humans to reliably distinguish between
    two similar-looking but different entropy values (keys, hashes, etc.).

  children:

    Visual Channels = goal:
      id: v1schann
      why: >
        Use three independent visual channels to convey entropy, providing
        redundancy and cross-checking capabilities.

      children:
        Text Channel = decision:
          id: t3xtchan
          why: >
            Render entropy as text tokens within cells for easy reading and
            oral communication.

        Edge Channel = decision:
          id: 3dg3chan
          why: >
            Use shapes and colors in the cell edges to provide a fast, gestalt-based
            comparison that doesn't require reading.

        Nucleus Channel = decision:
          id: nuclchan
          why: >
            Use cell background colors (nucleus) as a redundant hint for
            comparison, acknowledging that fine gradations might be lost
            in lower color-depth environments.

    Visual CRC = goal:
      id: v1sucrc1
      why: >
        Surface differences in the middle of long strings or at token ends
        via blank cells and quartile marks, acting as a visual checksum.

    Accessibility = constraint:
      id: acc3ssib
      why: >
        Must be usable by people with various forms of color blindness.
        Must remain effective when printed in grayscale (256 shades).

    Zero Dependency = constraint:
      id: z3rodeps
      why: >
        Must be trivial to implement correctly with no significant dependencies,
        allowing it to be ported to various environments (SVG, Canvas, etc.).

    Algorithm Implementation = decision:
      id: alg0impl
      why: >
        The implementation follows the step-by-step algorithm defined in
        docs/index.md, ensuring consistency across different language ports.

    Tokenization = decision:
      id: t0k3n1z3
      why: >
        Split normalized entropy into tokens on even character boundaries.
        Each token is mapped to a 24-bit 'quant'. If a token represents
        fewer than 24 bits, low-order bits are repeated to fill the space.

    CRC Token Detection = decision:
      id: c7ct0k4n
      why: >
        Identify median and quartile tokens to drive visual CRC features.
        Median uses standard ASCII sort. Quartiles use mirrored (reversed)
        ASCII sort with specific padding logic for non-multiples of 4.

    Blank Cell Shifting = decision:
      id: b1ankshf
      why: >
        Strategically insert up to 3 blank cells to create visual gaps
        for balance and improved comparison. Shifts are triggered by
        the median token and the extrema of the sorted token list.

    Visual Style Selection = decision:
      id: v1su5ty1
      why: >
        Determine the global color palette and shape set for an entviz 
        based on the median and second quartile tokens. This ensures that 
        different entropy values result in distinct visual "themes."

    Cell Rendering = decision:
      id: c3llrend
      why: >
        Translate a token's quant and cell position into SVG elements.
        Includes nucleus background, text contrast, and the 6-edge
        visual system with XOR-based shifting to ensure local variety.
        All 8 shapes (triangle, hook, rect, box, slant, hammer, pyramid,
        double bars) implemented in cell_shapes.py with correct geometry
        for all 6 edge orientations.

    Quartile Marks = decision:
      id: q4rtmark
      why: >
        Small filled circles (diameter = edge_size/2) drawn in the corners
        of quartile token cells act as a visual CRC. Corner placement and
        fill color are indexed by quartile order (1st=top-left, 2nd=top-right,
        3rd=bottom-right, 4th=bottom-left), using the edge_colors array.

    Full Pipeline = decision:
      id: f4llpipe
      why: >
        pipeline.py wires all steps (parse → tokenize → grid → cell assignment
        → visual style → render) into a single render() function returning
        an SVG string. app.py wraps it as a CLI accepting entropy text with
        optional --ar (aspect ratio) and --fs (font size) flags.

    Grid Selection = decision:
      id: g7id5elc
      why: >
        Select grid dimensions (NxM) that result in an overall aspect ratio
        closest to the target, without being less than the target.
        Calculations must account for the 2:1 aspect ratio of individual cells.

    V2 Migration = goal:
      id: v2m1grat
      status: complete
      why: >
        Move the implementation from spec v1 (docs/v1/index.md) to spec v2
        (now canonical at docs/index.md). v2 closes a security hole in v1: when the input
        entropy lacks an avalanche effect (UUIDs, chosen hex, base64 blobs),
        single-bit changes produce nearly identical v1 renderings. v2 fixes
        this by deriving most channels from a SHA-512 fingerprint of the
        input. v2 also supports inputs of arbitrary size and adds three
        gestalt channels (color bar, shape count summary, ellipse overlay)
        for rapid comparison without cell-by-cell inspection.

      children:

        Fingerprint as Second Data Source = decision:
          id: fpr1ntds
          why: >
            v1 had one data source (entropy → tokens) driving every channel.
            v2 splits responsibilities: tokens drive only text and nucleus
            background color (preserving losslessness ≤ 512 bits); a SHA-512
            fingerprint of the normalized input is tokenized into 22 "ftoks"
            that drive everything else (edge colors, edge shapes, median /
            quartile calculations, blank placement, entviz background color,
            color bar, shape count summary, ellipse overlay). Used ftoks are
            the first token_count ftoks, mapped 1:1 to tokens by index.

        Large Input Handling = decision:
          id: l4rg3inp
          why: >
            v1 implicitly assumed the input fits the grid. v2 caps tokens at
            22 regardless of input size: for inputs > 512 bits, only the
            first 256 bits and last 256 bits are tokenized into the text
            channel (separated by a blank cell). The fingerprint is computed
            over the entire input so the whole value still binds into all
            fingerprint-driven channels even when text is lossy.

        Grid Minimum 2x2 = decision:
          id: gr1dm1n2
          why: >
            v1 allowed 1xN and Nx1 grids. v2 forbids them; minimum grid is
            2 columns × 2 rows. Single-row/column layouts collapse the
            visual structure that makes comparison work.

        Bounding Rect Reframed = decision:
          id: gr1drect
          why: >
            In v1, "bounding rect" was the rectangle containing the cells.
            In v2 that rectangle is the "grid rect" and "bounding rect"
            names the larger outer canvas that holds the color bar, grid,
            and shape count summary. The bounding rect adds a grid margin
            (GM = edge_size/2) of white space on three sides, a 1-pixel
            black border on top/right/bottom only, and a color-bar-wide
            strip on the left. It is also the clipping region for all
            drawn content (notably the ellipse overlay).

        Layered Rendering = decision:
          id: l4y3rrnd
          why: >
            v1 rendered each cell completely in one pass (edges + nucleus
            + text together). v2 requires distinct layers with a global
            draw order: white fill → all edge rects of all cells → ellipse
            overlay → all nuclei + text → quartile marks → color bar + SCS
            → black border lines. The overlay must sit between edges and
            nuclei across the whole grid, so per-cell rendering no longer
            works. The pipeline gains a build-defs pass before the layered
            draw loop.

        Gestalt Color Bar = decision:
          id: c0lorb4r
          why: >
            Tally edge-color usage (excluding blank cells), sort bands
            descending by count with edge_colors-order tiebreak, render
            as the leftmost GM-wide strip filling the bounding rect height.
            Provides a redundant rapid-comparison channel: two entvizes
            with different color distributions differ visibly here before
            any cell-by-cell inspection begins.

        Gestalt Shape Count Summary = decision:
          id: shp3cnts
          why: >
            Tally shape usage (excluding blank cells), format each as X##
            (shape letter + zero-padded count), sort descending by count
            with alphabetical tiebreak, render right-justified to the grid
            rect's right edge in the cell text font on a line below the
            grid. Interactive renderings add a tooltip with the shape's
            full name when hovering an edge shape.

        Gestalt Ellipse Overlay = decision:
          id: 3llpsovr
          why: >
            A large, partially transparent ellipse derived from raw SHA-512
            digest bytes (60-63: anchor, axis ratio, rotation, opacity).
            Sized so its smaller semi-axis ≥ half the diagonal of the
            bounding rect, guaranteeing it overflows and clips to an arc.
            Fill is black (if entviz background luminosity > 0.5) or white,
            at the derived opacity. Drawn above edges and below nuclei so
            nucleus colors and text are never affected.

        Ellipse Anchor Enumeration = decision:
          id: 3llpsanc
          why: >
            The spec's original "outer corners of perimeter edge rects"
            phrasing was tightened. Anchor candidates are enumerated by
            walking perimeter cells in cell-index order, visiting each
            cell's corners in top-left, top-right, bottom-left, bottom-right
            order, and emitting each unique point the first time it is
            seen. This deduplicates shared corners and includes interior
            grid intersections that are corners of perimeter cells (but
            no corners of purely interior cells). Selection uses
            digest[60] mod (point count). docs/index.md line 156 carries
            the canonical wording.

        Shape Decoupling via defs+use = decision:
          id: shp3dcpl
          why: >
            A separate effort will redesign the edge shapes. To avoid
            churn at that boundary, v2 shapes are defined once as SVG
            <symbol> elements in <defs> and instantiated via <use> with
            per-edge transforms (translate + rotate, and scale for
            edges 2/5 compression). Each shape object owns its canonical
            symbol, name, and identifying letter; the per-edge transform
            lives on the renderer (uniform across shapes). Replacing a
            shape touches one file; the renderer is unaffected. This also
            cuts SVG size and parse cost dramatically (8 symbol defs +
            ~6N use elements instead of 6N inline shape primitives).

        Per-Cell Gradient via currentColor = decision:
          id: gr4dcurc
          why: >
            Each edge shape is filled with a linear gradient from nucleus
            background color (inner) to edge color (outer). Edge color
            varies per edge; nucleus bg varies per cell. Naively that is
            one gradient per cell × edge. Instead we define one gradient
            per cell in <defs> with stops (nucleus_bg, currentColor) and
            set color="<edge_color>" on each <use>. SVG resolves
            currentColor per instance, so 6 edges share one gradient def
            but render with their own edge colors. Cuts gradient defs
            from up to 132 to at most 22.

        Color Shift Once Per Cell = decision:
          id: shftxc3l
          why: >
            v1's spec wording placed "if last column, add shape_shift to
            color_shift" inside the per-edge loop (would fire 6 times for
            a last-column cell). v1 code does it once after the loop.
            v2 spec (docs/index.md) was updated to match the code: the
            adjustment is a separate step that runs once after all 6 edges
            of the cell have been processed. Per-edge logic stays per-edge;
            per-cell logic is its own step.

        Red Color Correction = decision:
          id: r3df1xup
          why: >
            v1 used #ffdf2f for "red" in possible_edge_colors, but that
            value is actually yellow nearly identical to gold (#ffd966),
            which collapses the palette in practice. v2 uses #ff3f2f.
            Caught in v1 but only fixed in v2 to keep the migration
            self-contained.

    V3 Migration = goal:
      id: v3m1grat
      status: complete
      why: >
        Move the implementation from spec v2 (now archived at
        docs/v2/index.md) to spec v3 (canonical at docs/index.md).
        v3 refines the gestalt channels (color bar skew, frame, SCS
        styling, ellipse overlay rework, hex font fitting) and replaces
        the v2 procedural edge shapes with new path-based cubist and
        polygon shape sets authored in 24x8 canonical edge space with
        fill-rule:evenodd. The full design rationale and locked decisions
        live in docs/spec-improvement-notes.md; the deferred polish items
        live in that same file under "Deferred items (next v3 polish
        pass)". The new shape geometry handoff is in new-shapes/.

      children:

        Spec Improvement Notes = decision:
          id: sp3cnote
          why: >
            Canonical record of the v3 design decisions and deferred polish
            items lives at docs/spec-improvement-notes.md. Six items are
            locked (color bar skew, color bar frame, SCS styling, ellipse
            rework, hex font fitting, clip-path bug fix) and eleven are
            deferred (D1-D11) for a later polish pass. When picking up v3
            work after a pause, read that doc first.

        New Shapes Handoff = decision:
          id: n3wshape
          why: >
            The v3 edge shapes are a designed set of 6 base shapes
            (cubist C1-C3 + polygon P1-P3) plus an empty member at slot
            4 of each set. Authored in 24x8 canonical edge space, single
            SVG path per shape with fill-rule:evenodd. Rotation uses a
            "tab" mechanic: shapes with mass outside their 16-wide window
            use a separate truncated path at 90/270 degrees, with hinge
            at the tab outer-left corner. Reference materials are in
            new-shapes/. The color model is UNCHANGED from v2 (per-cell
            nucleus_bg to per-edge edge_color gradient); the encoding doc
            in new-shapes/ shows a single-ink fade-to-transparent example
            that is for academic-paper diagrams only and is NOT the spec
            color model.

    V4 Exploration = goal:
      id: v4expl0r
      status: prototype
      why: >
        Experiment with replacing the v3 shape-based edge channel with a
        much simpler 24-box surround per cell. Goal: evaluate whether a
        pure bitmap-of-boxes can carry the same per-cell entropy more
        legibly than the cubist/polygon shape sets, while removing the
        per-edge shape menu, the shape-shift/color-shift state, and the
        per-cell color rotation. Spec docs/index.md is unchanged; this
        is an isolated implementation prototype.

      children:

        Blank Cell Min/Max Pointers = decision:
          id: v4bptr12
          why: >
            On top of the bicolor ring (v4bl4nkc), each blank cell
            also carries two small "pointer" markers: one tangent
            outside the ring pointing toward the maxftok cell, one
            tangent inside the ring pointing toward the minftok cell.

            minftok/maxftok are defined over the USED ftoks (not the
            full 22 ftoks of the fingerprint — for inputs under 512
            bits some ftoks are unused). minftok = smallest 24-bit
            quant; maxftok = largest. Tie-break = highest cell index
            (visual reading order — last cell containing the tied
            value).

            These cells are independent of the quartile cells
            (which sort the same used ftoks by mirrored ASCII text
            rather than by 24-bit value). The two sortings rarely
            coincide, so the pointers tend to flag two more
            ftok-derived cells than the four already flagged by
            quartile triangles.

            Geometry: ring nominal_radius reduced from
            (nucleus_height + box_height) / 2 to nucleus_width / 4
            (12 at 12pt, was 15) so the outside marker has 3 px of
            margin to the cell edge instead of touching it. Each
            marker is a r=1.5 white-filled black-1-px-stroked disc
            (4 px visible diameter). Outside marker center at
            r = nominal_radius + 3; inside at nominal_radius − 3
            (tangent to ring outer/inner extents).

            The markers are identical in design — position alone
            (inside vs outside the ring) tells the viewer which is
            min and which is max. Memorable rule: "max bursts
            outward".

            Purpose: (a) every blank ring now encodes two
            entropy-dependent angles, multiplying the CRC value of
            each blank cell — two entvizes that differ should differ
            in pointer angles across all rings; (b) creates a
            visual "constellation" — all the rings' max markers
            point at the same target, forming a geometric pattern
            that varies with the fingerprint.

        Blank Cell Bicolor Ring = decision:
          id: v4bl4nkc
          why: >
            v3 left blank cells visually empty — just the grid_rect bg
            color showing through. v4 adds a small ring centered in
            each blank cell. Nominal radius = (nucleus_height +
            box_height) / 2 (15 px at 12pt). Built as two adjacent
            1-px stroked circles at radii nominal±0.5: outer white,
            inner black. The result is a 2-px-wide bicolor ring —
            1 px of white on the outside immediately adjacent to 1 px
            of black on the inside. Whichever bg the cell sits on,
            one of the two strokes contrasts and the other gives a
            hard edge.

            Dead ends along the way (preserved for institutional
            memory):
              1. Single 1-px white stroke under mix-blend-mode=
                 difference. In theory inverts the bg pixel-by-pixel;
                 in practice fails for mid-luminosity bgs (e.g. blue
                 lightened by the 30% white overlay becomes ~#6e79d2,
                 luminance ~0.22, whose difference-inverse #91862d
                 is luminance ~0.23 — virtually identical luminance,
                 invisible to human contrast perception).
              2. Concentric outlined ring (3-px white outer + 1-px
                 black inner at same radius). Visible but visually
                 chunky and the black hairline ended up centered in
                 a white halo rather than on an edge.
            The adjacent-radii approach is the cleanest of the three:
            no blend mode, no luminance calculation, no per-cell
            logic, and the bicolor edge is naturally crisp.

            Purpose: (a) make blank cells findable at a glance — they
            were previously easy to miss against the surround-box
            noise on either side; (b) serve as a redundant visual CRC
            channel — the position and count of rings derives from
            the median / ASCII-first / ASCII-last anchors plus the
            large-input separator, so two entvizes that differ should
            differ in ring layout. Applies to all blank cells
            including algorithm-inserted blanks and any trailing
            unfilled cells.

        Quartile Marks as Corner Triangles = decision:
          id: v4qtri4ng
          why: >
            v3 used small filled circles in the corner of each quartile
            ftok's cell, color-coded by quartile (1st = edge_colors[0]
            in the top-left corner, etc.). v4 replaces the circle with
            a small right triangle in the nucleus corner: both legs =
            nucleus_height / 2, right-angle vertex at the nucleus
            corner, legs along the two nucleus edges. Fill = the cell
            text foreground color (white on dark nuclei, black on
            light). Quartile identity is encoded by triangle
            orientation alone — the per-quartile palette is retired.

            Earlier prototype (briefly): triangles with full
            nucleus_height legs filled white under mix-blend-mode=
            difference for pixel inversion. That worked visually but
            interfered with cell text legibility (half the glyphs got
            inverted). Smaller fg-colored triangles preserve text and
            keep quartile marks unambiguous.

        Taller Nucleus for Descenders = decision:
          id: v4nuc1ht
          why: >
            v3 set nucleus_height = font_size_px (16 at 12pt), assuming
            the em-box equals the glyph bounding box. It does not:
            typical monospace fonts (Consolas, Courier, etc.) have
            glyph bboxes that extend ~20-25% below the em-box for
            descender depth, plus line-gap. In v3 the descenders
            protruded into the bottom edge_rects, but those edges held
            sparsely-filled shape paths with lots of bg color showing
            through, so descenders blended in visually. In v4 the
            surround is densely solid-filled palette color, and
            protruding descenders became obvious — visible in every
            base64 cell containing g/j/p/q/y.

            Fix: nucleus_height = 1.25·font_size_px (was 1.0). Width
            stays at 3·font_size_px. Surround box dimensions follow
            from tiling: box_width = nucleus_width/8 (unchanged),
            box_height = nucleus_height/2 (was 0.75·box_width; the 0.75
            ratio is retired — box dimensions are now derived
            independently). cell_width = 3.75·font_size_px (unchanged),
            cell_height = 2.5·font_size_px (was 2.0). Cell aspect
            changes from 15:8 to 3:2.

        24-Box Surround = decision:
          id: v4b0xsur
          why: >
            Each cell's nucleus is surrounded by exactly 24 boxes — 10
            top, 10 bottom, 2 left, 2 right — numbered 0..23 clockwise
            from the top-left of the top row. Every box has the same
            dimensions: box_height = nucleus_height/2 = cell_height/4
            and box_width = 0.75·box_height. cell_width = nucleus_width
            + 2·box_width = 3.75·nucleus_height (15:8 aspect ratio,
            not v3's 2:1); cell_height = 2·nucleus_height. The surround
            tiles flush with the cell border, so adjacent cells touch
            with no inter-cell gap. Bit i of the ftok's 24-bit quant
            (LSB=bit 0) controls box i: 1 emits a filled rect, 0 emits
            nothing.

        Per-Cell Edge Color = decision:
          id: v4edg3c2
          why: >
            Filled surround boxes are painted in the cell's edge color,
            chosen per cell as the palette entry (one of the 4 non-bg
            colors) that is perceptually closest to that cell's
            nucleus_bg, using the weighted-RGB distance
            sqrt(2(Δr)² + 4(Δg)² + 3(Δb)²) as a cheap stand-in for
            CIELAB ΔE. This replaces an earlier prototype decision to
            fill the surround with the nucleus color directly: that
            looked clean but collapsed all contrast between the
            nucleus and its surround, which in turn made the ellipse
            overlay invisible (the overlay darkens nucleus-and-surround
            uniformly, so without contrast there's no visible arc). The
            palette-closest rule keeps each cell visually anchored to
            its nucleus while restoring the contrast the overlay needs.

        SCS Removed = decision:
          id: v4n0sc1m
          why: >
            v3's shape count summary (SCS) tallied per-edge shape usage
            and rendered an `X## X## …` line below the grid. v4 has no
            shapes to count, so the SCS is removed entirely. The
            bounding rect height drops by (nucleus_height + GM) — at
            12pt that's 20 px — and the row of white below the grid
            collapses to just the bottom GM margin and 1-px gray
            border.

        Base32 Alphabet = decision:
          id: v4base32
          why: >
            Add a BASE32 alphabet entry (5 bits/char, RFC 4648 alphabet
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"). Same 4-chars-per-token
            rule as bech32 (= 20 bits, extended to 24).

            Used by Stellar (G prefix) and IPFS CID v1 (b prefix).
            Bitcoin Cash CashAddr is commonly described as "base32"
            but actually uses the bech32 alphabet (BIP-173 char set,
            with 0,8,9 and minus 1,b,i,o); we declare BECH32 for it,
            not BASE32. Fixed the BITCOIN_CASH_REGEX char class
            accordingly — it had been using the RFC 4648 base32 char
            class which rejects 0/1/8/9, so real CashAddr addresses
            containing '9' fell through to the unknown-input
            fallback.

            BASE32 and BECH32 are now two distinct alphabet entries
            sharing bits_per_char=5 but with different character
            lookup tables. The same input string will produce
            different quant values depending on which alphabet is
            declared.

        Bech32 Alphabet = decision:
          id: v4bch320
          why: >
            Add a BECH32 alphabet entry (5 bits/char, alphabet
            "qpzry9x8gf2tvdw0s3jn54khce6mua7l" per BIP-173). Token
            length chosen as 4 chars (= 20 bits) rather than 5 chars
            (= 25 bits) because the quant is defined as a 24-bit
            value and the existing extension rule handles
            under-24-bit tokens cleanly; over-24-bit tokens would
            require a new collapse rule.

            Bitcoin SegWit (bc1.../tb1...), Litecoin modern
            (ltc1...), and Cardano Shelley (addr1.../stake1...)
            parsers updated to declare BECH32 instead of the BASE64
            placeholder. The Bitcoin SegWit regex previously used the
            BASE32 character class (a-zA-Z2-7) which is missing 0,
            1, 8, 9 — valid bech32 chars except for 1 (the
            separator) — so real bech32 addresses were falling
            through to the base64 fallback path. The regexes now
            use a proper bech32 character class.

            BASE32 alphabet (5 bits/char, alphabet A-Z2-7) is still
            deferred: Bitcoin Cash CashAddr, Stellar, IPFS CID v1
            continue to use the BASE64 placeholder until a separate
            commit adds BASE32.

            Default token_len rule simplified from
              "24 // bits_per_char if 24 % bits_per_char == 0 else 5"
            to
              "24 // bits_per_char"
            which gives 6 / 4 / 4 chars for hex / base58/64 / bech32
            respectively — all under or equal to the 24-bit budget.

        Hybrid Ellipse Anchoring = decision:
          id: v4hybell
          why: >
            v3 skipped the ellipse overlay entirely for grids with
            fewer than 6 interior corners (smaller than 3x4 / 4x3,
            corresponding to roughly <256 bits of input). v4 extends
            coverage to all valid grids (2x2 and larger) by falling
            back to EXTERNAL corners — the cell-corner points on
            grid_rect's outer boundary, of which a 2x2 has 8, a 2x3
            has 10, etc. The math (r_min ≤ r_max) holds even for
            the tightest 2x2 edge-midpoint anchor because external
            anchors have much larger d_far than interior corners
            give for the same grid.

            Visual character differs between the two anchor types:
            interior anchors produce a centered curve mostly visible
            inside the grid; external anchors produce a
            quarter-ellipse-in-a-corner (for vertex anchors) or
            half-ellipse-along-an-edge (for midpoint anchors)
            silhouette because most of the ellipse is clipped
            outside the grid_rect. Two visual "species" of overlay,
            but no entviz shows both — the species is determined by
            grid size, which is a deterministic function of input
            length.

            Threshold = 6 (unchanged from v3 for the
            interior-corner-eligible case). Implementation: new
            enumerate_external_corners() helper alongside the
            existing enumerate_interior_corners(); _draw_ellipse_overlay
            chooses between them based on interior_count.

        Clip-Path Id Uniqueness = decision:
          id: v4ovr1d1
          why: >
            v3's overlay structure (<g clip-path><ellipse transform>)
            works correctly when each SVG stands alone. It breaks when
            multiple entvizes are embedded in a single HTML document
            (e.g., the gallery): every clipPath uses id="grid-clip", and
            browsers resolve url(#…) to the *first* matching id in the
            entire HTML document, so every entviz after the first gets
            silently clipped to the first one's grid_rect. Symptom:
            overlays look "clipped wrong" in non-leading positions —
            spurious axis-aligned cut-offs at the wrong column/row.

            Fix: salt the clipPath id with the first 8 hex chars of the
            fingerprint AND the grid dimensions (cols x rows). The
            grid dimensions component handles same-input/different-AR
            cases (e.g., the gallery's "same input, different aspect
            ratios" set). For multi-entviz HTML embeds beyond the
            gallery generator, callers should additionally per-instance
            namespace ids if they expect the same input rendered
            twice; the gallery generator rewrites every id and
            url(#…) reference per entry as a belt-and-suspenders.

            Dead end on the way: emitted the rotated ellipse as a
            pre-rotated <path> (two A arcs, rotation baked in), under
            the misdiagnosis that the issue was clip-vs-transform
            interaction. The path approach also failed to fix the bug
            in the browser — confirming the actual cause was id
            collision, not the transform. Reverted to v3's
            <ellipse transform=rotate> structure once the id salt was
            in place.

        V4 Color Bar from Digest Histogram = decision:
          id: v4c1rbar
          why: >
            v3 sourced the color bar from per-edge color-usage tallies.
            v4 has no per-edge color choices, so the bar is repurposed
            as a fingerprint summary: tally each of the 4 two-bit
            patterns (00, 01, 10, 11) across the 256 disjoint 2-bit
            slices of the 64-byte SHA-512 digest, map binary value i to
            the i-th non-bg color (the existing quartile palette), then
            reuse the v3 rendering — descending sort, count^4 skew,
            edge_colors-order tiebreak. Total count is always 256
            regardless of grid size, so band proportions stay
            comparable across small and large inputs. A white band stays
            distinguishable from the surrounding white canvas because
            the existing 1-px gray frame (top/bottom borders + left
            border + interior separator at x = 1 + box_height + 0.5)
            encloses the bar on all four sides.

    Reference and Rendered Font Sizes = decision:
          id: r3fr3nfn
          why: >
            v3 introduces a distinction: "reference font size" is the
            configurable input (nominally 12pt) that drives all geometry
            (nucleus_height, cell dims, GM, bounding rect, color bar
            width). "Rendered font size" is the actual size applied to a
            specific text element. They may differ: hex cell text renders
            at 75% of reference; SCS renders at min(round(0.9 x reference),
            cell text rendered size). The rendered size never affects
            geometry.
