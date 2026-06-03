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

        Blank Cell Clock Hands = decision:
          id: v4bptr12
          why: >
            On top of the white-disc ring (v4r1ng3v2), each blank
            cell carries two "clock hands" drawn from the ring
            center, encoding the angles to two cells of interest.
            Final shape after two iterations:

              * Long hand → maxftok direction. Length = ring
                radius + 1 (= 18 at 12pt), so the hand crosses
                the ring's black rim by exactly 1 px. Drawn as
                a white stroke with mix-blend-mode: difference.
                On the white disc interior the white stroke
                inverts to black (visible as a black hand); on
                the 1-px black rim it inverts to a single white
                pixel breaking the rim. That tiny "notch" in
                the rim is the visual cue marking the maxftok
                angle.
              * Short hand → minftok direction. Length = ring
                radius / 2 (= 8.5 at 12pt), drawn as a plain
                black stroke. Terminated by a small white-filled
                black-stroked circle (r=1.5) centered at the
                hand's end point — visually a "circle with a
                white dot inside" that makes the tip readable
                as distinct from the long hand's notch.

            Ring radius simultaneously enlarged: started at
            nucleus_width/4 = 12, grew to /4 + 3 = 15 in the
            first clock-hand redesign (to absorb the outside
            tangent marker's space), and now /4 + 5 = 17 in
            this revision (to give the long hand more length
            and the difference-blend notch more visual presence).

            minftok/maxftok are defined over the USED ftoks
            (not the full 22 ftoks of the fingerprint — for
            inputs under 512 bits some ftoks are unused).
            minftok = smallest 24-bit quant; maxftok = largest.
            Tie-break for min = highest cell index (preserving
            the earlier convention).

            Why difference blend for the long hand: it lets a
            single drawn element render as black where the
            entviz wants a black hand AND simultaneously as
            white where it wants to break the rim — without
            needing to clip or split the line into multiple
            colored segments. Modern browsers (Chrome, Brave,
            Safari, Firefox) all support mix-blend-mode on SVG
            elements; cairosvg historically does not honor it
            cleanly, which is acceptable since the gallery is
            rendered for browser viewing.

            Why the short hand carries a tip ornament: the two
            hands now share the same color (black, by the time
            the long hand's difference-blend renders), so they
            need to be distinguishable by shape, not color.
            The long hand reads as a plain line ending in a
            "notch through the rim"; the short hand reads as a
            line ending in a "circle with a white dot". That
            asymmetry (notch vs. ringed-tip) is what tells the
            viewer which direction is min vs. max.

            Purpose: every blank ring encodes two entropy-
            dependent angles, multiplying the CRC value of each
            blank cell — two entvizes that differ should differ
            in hand angles across all rings, and the angles
            also form a visual "constellation" where every
            ring's long hand points to the same maxftok cell
            and every short hand to the same minftok cell.

            Run-based decoration: only the FIRST cell of each
            run of consecutive blank cells (in reading order)
            gets the full ring + hands + tip stack. Subsequent
            cells in the same blank run are truly empty (no
            ring, no hands). The rule was added because at
            larger entropy a long trailing run of blank cells
            otherwise repeated the same decoration N times,
            which both cluttered the design and lost
            information (every ring in a run is necessarily
            identical, because they all point to the same
            min/max cells). A non-decorated trailing blank
            still carries angular information indirectly — the
            FIRST cell of the run is decorated and its position
            anchors the run's location.

        Blank Cell Ring as White-Filled Disc = decision:
          id: v4r1ng3v2
          why: >
            v4 ring style simplified from the earlier two-adjacent-
            strokes design (1-px white outer + 1-px black inner at
            radii nominal±0.5) to a single white-filled circle at
            nominal_radius with a 1-px black outline. Same color
            scheme (white + black), but the ring is now an opaque
            disc rather than a thin transparent ring. Anything
            beneath it inside the radius (grid_rect bg, overlay
            tint) is occluded. Visually more solid and easier to
            spot at a glance.

            Pointer markers (already white-filled + black-stroked)
            unchanged — already matched this new aesthetic.

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

        Type/Prefix/Suffix Label Strips = decision:
          id: v4l4bels
          why: >
            Each entviz now declares its detected type and (when
            applicable) the input's prefix and suffix in dedicated
            label strips. Top strip is always present: "<Type>:" or
            "<Type>: <prefix>..." (e.g., "Ethereum: 0x...",
            "UUID:", "base32:"). Bottom strip is present only when
            the parser identifies a suffix: "...<suffix>" (e.g.,
            "...d4af" for Bitcoin Legacy's base58 checksum).

            Strips are nucleus_height tall, separated from the grid
            and from the borders by GM on each side. Text uses the
            same monospace font family as cell text, filled in #666
            so it reads as a quiet secondary label. Rendered font
            size is always the hex-equivalent size (round(font_pt
            * 0.75) px) regardless of cell text size, so labels
            stay visually consistent across input types instead of
            jumping between big/small. Top is left-aligned to
            grid_rect.left; bottom right-aligned to grid_rect.right
            — the ellipses on each point inward toward the cell
            grid.

            For variable-length plain-alphabet types, the label
            embeds a parenthesized count of the *body* characters
            so the viewer immediately knows the input's size:
            "hex(40)", "b64(12)", "b64url(8)". For the UTF-8 →
            base64url re-encode fallback, the count is the original
            input's byte length (not the re-encoded core), so
            "hello world" → "txt(11)->b64url:". "base64" is
            displayed as "b64" and "base64url" as "b64url" to keep
            labels narrow.

            For the disproof fallback (no specific parser matched
            but the input fits some alphabet), parse() returns
            type = alphabet name ("base32", "bech32", etc.).

            When the input exceeds 512 bits and tokenize_entropy
            elides the middle, the top label is prefixed with the
            language-neutral marker "^…$ " (regex start anchor +
            ellipsis + end anchor), e.g. "^…$ hex(200):" or
            "^…$ ETH: 0x...", so the viewer knows the cells show
            only the first and last 256 bits of the original.
            The fingerprint-driven visualization channels still
            cover the entire input. Chose ^…$ over English
            ("head+tail of") so the marker reads the same in any
            locale — the regex anchors are programmer-universal
            and the ellipsis between them visually conveys
            elision.

            Bounding rect height grows by nucleus_height + GM
            always (top strip) and another nucleus_height + GM
            when suffix exists (bottom strip).

        WCAG Contrast Crossover (superseded by v4oklab) = decision:
          id: v4wcagxr
          why: >
            v3 used the naive rule `relative_luminance(bg) < 0.5 →
            white text, else black`. This mis-paired
            medium-luminance backgrounds with white text — e.g.,
            light beige #c3b2a1 (Y ≈ 0.47) was paired with white,
            giving WCAG contrast 2.0:1 (fails AA) where black would
            have given 10.4:1.

            v4 first replaced this with the true WCAG black-vs-white
            crossover at Y ≈ 0.1791 (the Y at which contrast(white,
            Y) equals contrast(Y, black)). That fixed beige and
            similar bright bgs, but exposed a second problem on
            saturated dark greens: WCAG Y heavily weights green
            (0.7152·G), so a "looks dark" green like #55841c lands
            at Y = 0.185 — just past the crossover, so paired with
            black even though the eye expects white. See [[v4oklab]]
            for the resolution.

        Oklab Perceptual Threshold = decision:
          id: v4oklab
          why: >
            Replaces the WCAG-equal-contrast crossover (v4wcagxr)
            with Oklab perceptual lightness L, threshold L > 0.6 →
            black, else white.

            Why Oklab and not WCAG Y? sRGB Y is photometric, not
            perceptual: it over-weights green so saturated dark
            greens read as "dark" to the eye but sit just past the
            WCAG crossover by number. Oklab (Björn Ottosson, 2020)
            is a modern perceptually-uniform color space whose L
            handles saturated colors — greens in particular —
            better than CIELAB L*. For #55841c: Y = 0.185 (just
            past WCAG threshold 0.179 → black), but Oklab L = 0.559.

            Why 0.6 and not the rigorous Oklab midpoint 0.5? At
            L = 0.5 the perceptual lightness gap to black equals
            the gap to white, but small dark glyphs on mid-gray
            fields read less crisply than small light glyphs of
            the same gap — the eye handles light-on-darker better
            than dark-on-mid for fine detail. A +0.1 bias past the
            midpoint flips dark-green-class colors (L ≈ 0.54–0.59)
            to white where they read more comfortably.

            Cases at the threshold (L just above/below 0.6):
              * #55841c dark green → L=0.559 → white ✓
              * rgb(125) mid-gray → L=0.590 → white
              * rgb(160) mid-gray → L=0.685 → black
              * #ff3f2f red       → L=0.657 → black
              * #c3b2a1 beige     → L=0.773 → black
              * #ffd966 gold      → L=0.896 → black

        Ethereum Detection & Full-Body Core = decision:
          id: v4eth4ddr
          why: >
            Two fixes to Ethereum address handling.

            (1) Tighten recognition. v3 used regex
              ^(0x)?[a-fA-F0-9]{40}$
            with the 0x optional, so any 40-char hex blob (regardless
            of case or context) was classified as Ethereum. But '0x'
            is a generic C-derived hex prefix and 40 hex chars alone
            is too weak a signal. v4 requires EITHER an explicit 0x
            prefix OR EIP-55-style mixed case (both upper and lower
            letters in the body). A pure single-case 40-char hex
            without prefix falls through to plain hex.

            (2) Full-body core. v3 split the 40-char body as 32 + 8,
            treating the last 8 chars as a "suffix" (like Bitcoin
            Legacy's true 4-char base58 checksum). But Ethereum has
            no separable checksum suffix — the EIP-55 checksum is
            the case pattern of the entire 40 chars. The 32/8 split
            dropped the last 8 chars from both the text channel and
            the fingerprint computation, so two addresses differing
            only in those bits produced identical entvizes. v4 puts
            the full 40-char EIP-55-cased body in `core`, leaves
            `suffix` empty.

            Plain hex is normalized to lowercase (parse_hex returns
            lower-case core) to avoid the oral-reading "cap A"
            ambiguity. Ethereum is the exception: it preserves
            EIP-55 mixed case because the case pattern is the
            checksum, not presentation.

        Alphabet Detection by Disproof = decision:
          id: v4d1sprf
          why: >
            For inputs that don't match any specific-format parser
            (UUID, Ethereum, Bitcoin*, IPFS CID*, Stellar, etc.), the
            v3 fallback always re-encoded the input as UTF-8 bytes →
            base64url. This loses information: an input like
            "ABCDEFGHIJKLMNOP" (entirely uppercase letters, no spaces
            or punctuation) is a perfectly valid base32 string but
            gets round-tripped through bytes anyway, producing a
            different fingerprint than treating it directly as
            base32 would.

            v4 adds detect_alphabet_by_disproof(): walks the known
            alphabets from most-restrictive to least
              hex → base32 → bech32 → base58 → base64 → base64url
            and returns the first whose character set contains every
            char of the input. hex/base32/bech32 are tested
            case-insensitively (they have canonical case but accept
            either); base58/base64/base64url are case-sensitive
            (their alphabets explicitly treat upper and lower as
            distinct characters).

            parse() now invokes the disproof detector when no
            specific parser matched, and returns a synthetic
            Parsed(type="auto-detected") with the detected alphabet
            if disproof succeeds. The UTF-8 → base64url re-encode
            remains as the final fallback for inputs that don't fit
            any alphabet at all (e.g. contain spaces or punctuation).

            The disproof order is intentionally most-restrictive-
            first so that ambiguous inputs (e.g., "DEADBEEF" — valid
            in all alphabets) are treated as their most-specific
            possibility. This matches the principle that we "can't
            prove a positive but can disprove" each alternative.

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

        ULID & Crockford Base32 = decision:
          id: v4cr0ckf
          why: >
            Add a ULID parser and a CROCKFORD32 alphabet entry.

            ULID format: 26 chars of Crockford base32 (5 bits/char,
            alphabet "0123456789ABCDEFGHJKMNPQRSTVWXYZ" — excludes
            I, L, O, U to reduce visual ambiguity). The ULID/Crockford
            spec also accepts I, L (-> 1) and O (-> 0) as
            case-insensitive INPUT aliases; U is not an alias. The
            parser regex matches [0-9A-TV-Z]{26} (skipping U)
            case-insensitively; on match it translates the aliases
            and upper-cases the rest to canonical Crockford form
            before declaring CROCKFORD32 as the alphabet.

            Token length is 4 chars (20 bits, extended to 24) under
            the existing bits_per_char=5 rule, identical to BASE32
            and BECH32 mechanics — the only difference is the
            character lookup table. The same 26-char text under
            CROCKFORD32 vs BASE32 vs BECH32 produces three different
            quant sequences because each alphabet maps chars to
            different bit values.

            Parser dispatch order: parse_ulid auto-registers via
            register_parse_funcs() before parse_hex is appended last.
            A 26-char string made up of only [0-9A-F] (e.g. an
            unprefixed mid-length hex blob) is therefore classified
            as a ULID rather than as plain hex — an intentional
            precedence shift since ULID is the more specific format.
            Two pre-existing test fixtures (a 26-char hex string in
            test_parsing / test_hex_normalization, and
            "bInvalidBase32Address12345" which happens to be 26
            chars of valid Crockford) were extended to 27/28-char
            lengths to remove the overlap.

            Disproof chain unchanged: CROCKFORD32 is NOT added to
            detect_alphabet_by_disproof. Reasoning — the specific
            26-char ULID parser already catches the only canonical
            shape; for arbitrary-length inputs Crockford is not
            more restrictive than RFC 4648 base32 in a useful way
            (both are 32-char alphabets and the character-set
            difference, I/L/O/U vs 0/1/8/9, is arbitrary), and
            adding it would force a precedence ranking that doesn't
            reflect any real input-source distinguishability.

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

        SSH Public-Key Type Detection = decision:
          id: v4sshkey
          why: >
            The v3 parser matched any AAAA-prefixed base64 blob with a
            generic "SSH key" type and a 4-char "AAAA" prefix. That
            under-reported structural overhead: every SSH key carries a
            fixed length-prefixed type-string at the front (and, for
            ssh-rsa, a fixed exponent field; for ecdsa-sha2-nistpXXX,
            a redundant curve-name field) that contributes no per-key
            entropy.

            v4 detects six specific key types by a base64 prefix
            (`match_str`) and consumes a possibly-longer `prefix_length`
            from the payload. The extra chars (when prefix_length >
            len(match_str)) are non-constant structural bytes — usually
            the high bytes of the next length-prefix field — that vary
            per key but carry no entropy. Pulling them into the prefix
            region keeps the cells starting on per-key entropy:
              ssh-ed25519           → match "AAAAC3NzaC1lZDI1NTE5AAAA"        (24, prefix_length=24)
              ssh-rsa               → match "AAAAB3NzaC1yc2EAAAADAQAB"        (24, prefix_length=28; extra covers 3 of 4 modulus-length bytes)
              ssh-dss               → match "AAAAB3NzaC1kc3M"                 (15, prefix_length=15)
              ecdsa-sha2-nistp256   → match "AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABB" (52, prefix_length=52; cleanly captures the always-constant key-length 0x00000041)
              ecdsa-sha2-nistp384   → match "AAAAE2VjZHNhLXNoYTItbmlzdHAzODQAAAAIbmlzdHAzODQAAABh" (52, prefix_length=52)
              ecdsa-sha2-nistp521   → match "AAAAE2VjZHNhLXNoYTItbmlzdHA1MjEAAAAIbmlzdHA1MjEAAACF" (52, prefix_length=52)

            For ssh-rsa the prefix folds in the second wire field (the
            public exponent), because real-world keys universally use
            65537 (0x010001, length 3, encoded `AAAADAQAB`). The body
            therefore starts at the modulus length-prefix.

            For ecdsa-sha2-nistpXXX the prefix folds in the curve-name
            field (`AAAAIbmlzdHAyNTY` etc.), because the curve name is
            fully redundant with the type-string — both encode "256"
            (or 384/521).

            For ed25519 the prefix extends 4 chars past the
            type-string field to sweep up the high 3 zero bytes
            (`AAAA`) of the always-constant key-length field
            (0x00000020 = 32). Without that extension the first
            cell of the core would render as `AAAA` on every
            ed25519 key — pure structural noise. The 4th byte of
            the key-length field (0x20) still leaks into the
            first character of the core (deterministically encoded
            as `I`), but the remaining 3 chars of the first cell
            encode 16 bits of the actual ed25519 public key, so
            the cell varies per-key. Trade-off: keeping the prefix
            string constant (so the `payload.startswith(prefix)`
            lookup still works) means we can't capture the full
            key-length field without leaking entropy bytes into
            the prefix; 24 chars is the cleanest cell-boundary
            stop short of that trade-off.

            For dss the prefix is just the length-prefixed type-string
            (no exponent equivalent — the four DSA parameters p,q,g,y
            are all per-key entropy).

            The parser also handles the full openssh single-line form:
                <type-string> <base64-payload> [<comment>]
            The leading "<type-string> " token is matched and consumed
            (it's redundant with the type detected from the base64
            prefix). A trailing space-separated comment (e.g.
            "user@host") is captured as `suffix`.

            Unknown type-strings (a future SSH key algorithm, or a
            non-SSH blob that happens to start with AAAA) fall back to
            the generic behavior: type "SSH key", prefix "AAAA".

        GLEIF LEI (ISO 17442) = decision:
          id: v4le1gle
          why: >
            Add `parse_lei` for GLEIF Legal Entity Identifiers (ISO
            17442). Shape: exactly 20 characters from base36
            (0-9, A-Z); structure is 4-char LOU prefix + "00" reserved +
            12-char entity body + 2-char ISO/IEC 7064 MOD 97-10
            checksum. Same checksum algorithm IBAN uses, minus the
            country-code rotation: replace each letter with its base36
            numeric value (A=10..Z=35), interpret the resulting digit
            string as a base-10 integer, and require it ≡ 1 (mod 97).
            Input is case-insensitive; the parser normalizes to upper.

            ISO 17442 split mirrors Bitcoin legacy's treatment of its
            version byte + base58 checksum:
              * prefix = 6 chars (4-char LOU issuer code + "00"
                reserved) — structural, identifies the issuer
              * core   = 12 chars (entity-specific body — the actual
                per-entity entropy that the visualization should
                emphasize)
              * suffix = 2 chars (MOD 97-10 checksum)
            Top label thus reads e.g. `LEI: 549300...`, bottom label
            reads e.g. `...12`.

            The MOD 97-10 validation matters. Without it, the LEI
            parser would claim every 20-char base36 string — a huge
            false-positive surface that would mis-label random tokens,
            short hex blobs (when interpreted upper-cased), and many
            base32/base64 fragments. The checksum reduces the false
            positive rate to ~1/97 ≈ 1% of arbitrary 20-char base36
            strings, and the additional "positions 5-6 = 00" structural
            check filters out a further ~99% of the survivors.

            BASE36 alphabet is new: 0-9 then A-Z, 36 chars. 36 isn't a
            power of 2, so true entropy is ~5.17 bits/char. For
            token-alignment purposes we declare bits_per_char=6 — the
            same trick BASE58 uses (also non-power-of-2): 4 chars per
            24-bit token. A 20-char LEI tokenizes to exactly 5 tokens.

            BASE36 is intentionally NOT added to
            detect_alphabet_by_disproof. A bare 20-char base36 string
            without a checksum carries no positive signal vs hex,
            base32 (RFC 4648), or base58 — all of which already appear
            earlier in the disproof order. The specific LEI parser
            with its checksum is the only place base36 carries
            information.

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

    V5 Migration = goal:
      id: v5m1grat
      status: drafted
      why: >
        Move the implementation from spec v4 (now archived at
        docs/v4/index.md) to spec v5 (canonical at docs/spec.md).
        v5 closes adversarial review finding F5 (head+tail-only
        text truncation collision on long inputs) and partially
        addresses F6 (CVD-accessible labeling of the gestalt color
        bar). v5 keeps all of v4's geometry, palette, surround,
        ellipse, blank-cell, and label-strip behavior intact; the
        only substantive changes are the long-input text-channel
        rule, the truncation marker style, and the addition of
        per-band letters on the color bar.

      children:

        Head + Tail + Middle Slice Text Channel = decision:
          id: v5mid1sl
          why: >
            v4 truncated >512-bit inputs to head-256 + tail-256
            and bound the omitted middle only through the
            fingerprint. The adversarial review of 2026-05-27
            (reviews/adversarial-2026-05-27.md, finding F5)
            demonstrated that this lets a T1+T5+T6 attacker (per
            docs/threat-model.md) grind a head+tail-matching
            input pair whose text channel is byte-identical and
            whose only differences live in the fingerprint-driven
            gestalt channels — a feasible attack against a
            habituated user landmark-checking on ~30 bits of
            perceptual entropy.

            v5 reserves cells for four fingerprint-selected
            middle slices in addition to head and tail. Total
            22-cell budget allocation: H=8 head tokens, 1
            separator blank, M=4 middle-slice tokens, 1
            separator blank, T=8 tail tokens (8+1+4+1+8 = 22).
            Allocation rationale:
              * 22 cells is hard-capped by the fingerprint's
                22 ftoks, so any extension to head/tail/middle
                must steal from each other.
              * 8 head + 8 tail keeps each group large enough
                to fill a typical row of the grid (8 cells wide
                in 8x3 or 11x2 layouts) so they're visually
                dominant — these are the cells the user can
                read against an external reference (e.g. an
                address shown elsewhere).
              * 4 middle slices gives meaningful coverage (96
                bits sampled across 4 disjoint body regions)
                without crowding the head/tail; smaller (1-2)
                would be near-redundant.
              * 2 separator blanks are the minimum to make the
                three groups visually distinct; a single blank
                would let the eye merge head+middle or
                middle+tail.
            Alternatives considered and rejected:
              * 6/6/8 (head/tail/middle): makes the middle
                dominate visually, but head/tail are what the
                user actually compares against external sources.
              * 10/10/2 (head/tail/middle): keeps head/tail
                strong but the 2-cell middle is too small to
                reliably catch grinding attacks against the
                body.

            Middle-slice offset derivation: for slice i in
            0..3, read digest[32+2i .. 33+2i] as big-endian
            uint16, compute offset_i = (uint16 mod
            (input_length_bytes − 3 − 32)) + 16. This keeps
            slices strictly between the head-32 and tail-32
            byte regions. Overlap rule: increment by 3 and
            retry if within ±3 bytes of a previously-selected
            offset; deterministic even-spacing fallback if the
            search wraps. Slices are presented sorted by
            ascending offset (not derivation order) so the
            user reads middle-group cells left-to-right
            through the body.

            Middle-slice cell text shows the 3 bytes at that
            offset, rendered in the input's declared alphabet
            (hex → 6 hex chars; base64/url → 4 chars via the
            standard 3-byte encoding; base32/bech32/crockford32
            → 4 chars covering 20 bits; rounding to nearest
            aligned character boundary when the alphabet's
            token alignment doesn't fall on byte boundaries).

            Used ftoks rule unchanged from v4: cell index →
            used ftok index, with separator blank cells
            consuming their cell indices but no ftoks.

            Attacker cost change: a T5 attacker who could
            previously collide only on head+tail (64 bytes)
            must now additionally match four fingerprint-
            selected 3-byte windows in the body, AND those
            windows shift as a function of the full input.
            This raises the grinding cost from a fixed
            64-byte-prefix-and-suffix search to a joint
            (full-input, offsets) search — a much larger and
            non-stationary target.

        Loud Truncation Marker = decision:
          id: v5trncma
          why: >
            v4's truncation marker was `^…$ ` — regex anchors +
            ellipsis — prepended to the top label in the same
            quiet #666 color and weight as the rest of the
            label. Adversarial review F5 noted that a reading
            user encountering `^…$ hex(200):` for the first
            time will not parse it correctly, and the marker
            disappears in peripheral vision.

            v5 replaces it with `part of ` (revised twice on
            2026-05-27: initial v5 draft used `truncated(N bytes) `
            — dropped after gallery review showed the parenthetical
            duplicated the byte count already present in the type
            label, e.g. `hex(200)`, `b64(119)`; then briefly
            `partviz` — dropped because the coined word was
            non-obvious to a first-time reader; settled on
            `part of` which reads as plain English when joined
            with the type label that follows: "part of hex(200):",
            "part of b64(1024):"). Rendered in bold with
            fill = #a00000 (dark red, Oklab L ~0.43). The marker
            communicates *what* the cells shown are: only part of
            the input, sampled at head + middle slices + tail, not
            a linear scan. The type-label parenthetical that
            immediately follows still supplies the byte count as a
            useful corroborating fact — inputs of very different
            lengths cannot be the same input regardless of cell
            similarity.

            Color choice rationale: #a00000 contrasts well
            against the white bounding-rect background,
            satisfies WCAG AA, sits at Oklab L ~0.43 (clearly
            "dark red" and distinct from both #666 label gray
            and any of the palette colors). Implementations
            MAY substitute another dark red provided Oklab L
            lies in [0.35, 0.55] and the color remains
            hue-distinct from the rest of the label under CVD
            simulation.

        Color Bar Letters = decision:
          id: v5cblet1
          why: >
            v4 communicated color-bar band identity by hue
            alone. Adversarial review F6 noted that the
            gold/red pair collapses below the severe-CVD JND
            threshold (ΔE ≈ 26.7 under deuteranopia, well
            below the 50-60 severe-CVD bar), so CVD users
            lose one of the most important gestalt
            discriminators.

            v5 adds a single letter to the center of each
            color-bar band. Letter color picked by the same
            Oklab L < 0.6 rule used for cell text against
            nucleus bg: black letter on white and gold bands;
            white letter on red, blue, and black bands. Font:
            same monospace family as cell text.

            Case and sizing revised 2026-05-27 after gallery
            review: the initial draft rendered uppercase
            (W/G/R/B/K) at font-size round(band_height × 0.6)
            with a min clamp of round(box_height × 0.5). In
            the gallery this produced letters that visually
            overpowered the narrow color bar — uppercase caps
            sit at roughly 0.7·font_size and the min clamp
            kicked in on smaller bands. The revised rule:
            lowercase glyphs (w/g/r/b/k) at font-size
            min(band_height × 0.7, bar_width × 0.85), no
            minimum floor. Lowercase glyphs sit at x-height
            so their visual mass is smaller for the same
            font-size; the explicit bar_width cap prevents
            wide bands from sprouting oversized letters; and
            dropping the floor means a tiny band gets a tiny
            (and optionally omitted) letter rather than one
            that overflows. The machine-readable
            `data-color-bar-band` attribute remains uppercase
            for stability across any future restyle of the
            rendered case.

            Why this addresses F6 only partially: it provides
            a verbal label for the gestalt channel (which
            survives complete CVD and monochrome rendering
            and CSS color filtering), but does NOT change the
            palette itself. A separate palette re-tune would
            be needed to make gold/red discriminable under
            deuteranopia/protanopia in the per-cell surround
            channel. v5 ships the letter fix only; palette
            re-tune is deferred to a future spec revision
            because it would invalidate every v4 golden test
            and a large fraction of v4's per-cell appearance.

        Spec File Rename = decision:
          id: v5spcfnm
          why: >
            v5 archives v4 at docs/v4/index.md (matching the
            existing docs/v3/index.md convention) and renames
            the working spec from docs/index.md to
            docs/spec.md. Two reasons:
              * docs/index.md was indexable as a GitHub Pages
                "site root" (entviz uses github.io for its
                gallery) which conflated "the algorithm spec"
                with "the project landing page" — the spec
                deserves a name that says what it is.
              * docs/spec.md is the conventional name in the
                wider open-source ecosystem (IETF, W3C
                proto-specs, RFC tracking) for the
                authoritative algorithm document.
            All top-level references in README.md, AGENTS.md,
            CLAUDE.md, and this.i (this file) are updated to
            point at docs/spec.md. The git mv preserves the
            file's history so blame/log over v2-v4 changes
            remains traversable.

    Adversarial Review F7 Decisions = goal:
      id: f7d3c1de
      status: drafted
      why: >
        The adversarial review of 2026-05-27 (review F7 in
        reviews/adversarial-2026-05-27.md) raised three case-
        normalization concerns. This node records the
        maintainer's resolution of each. F7a and F7c are
        intentional invariants of the algorithm; F7b is a
        behavior change to land in a follow-up implementation
        commit.

      children:

        Case Normalization Is Intentional = decision:
          id: c4s3norm
          why: >
            For every case-insensitive alphabet entviz supports
            (hex, UUID, base32, bech32, EOS-base, crockford32),
            the parser canonicalizes case before tokenization
            and fingerprinting. Most canonicalize to lower case;
            base32 canonicalizes to UPPER case (RFC 4648
            convention — Stellar and IPFS CID v1 cores are
            uppercased, see parse_stellar_address and the CID v1
            parser). The direction is irrelevant; consistency
            per alphabet is what matters. spec.md line 101 was
            corrected during the 2026-06-02 audit to stop
            claiming base32 lowercases.
            This means two inputs differing only in case for a
            case-insensitive alphabet produce identical
            entvizes. This is correct and required behavior —
            it is what the F2 fix established. Without it,
            'ABCDEF' and 'abcdef' would produce different
            entvizes despite being semantically the same hex
            value, which would let a T3 attacker (per
            docs/threat-model.md) cause a benign tooling
            difference to look like an entropy difference.

            F7's concern is that a user encountering the
            normalized cell text might not realize the
            normalization happened. The spec (docs/spec.md)
            documents the normalization explicitly so that the
            behavior is discoverable; no label-strip marker is
            added because the cell text already shows the
            normalized form, and a marker would add chrome on
            most mixed-case hex inputs without conveying
            information the cells don't already convey.

            Apply to: any case-insensitive alphabet parser.
            Not to: case-sensitive alphabets (base58,
            base64/base64url for non-Ethereum, ULID's
            crockford32 input *aliasing* is canonicalized but
            the resulting normalized alphabet remains
            distinguishable from case-sensitive base64).

        Ethereum EIP-55 Mixed-Case Validation = decision:
          id: 3ip55rj1
          why: >
            EIP-55 encodes a checksum in the *case pattern* of
            the address's hex digits. v4 silently re-derived
            the canonical EIP-55 case from the address bytes
            before rendering, which made an invalid-checksum
            mixed-case input render identically to the same
            address with a valid checksum (review F7). A T3
            attacker substituting a mixed-case address with a
            silently-corrupted checksum gets through entviz
            comparison; the wallet rejects later, after the
            user has committed time to the flow.

            v5 adopts "lenient B1": reject only mixed-case
            Ethereum inputs whose case pattern fails the
            EIP-55 checksum. All-lowercase and all-uppercase
            Ethereum inputs are accepted unchanged — per
            EIP-55 itself, these forms are conventionally
            understood as "checksum not asserted" and are
            widely used by CLI tools, JSON-RPC outputs, and
            block explorers; rejecting them would break
            legitimate paste flows. Mixed-case-but-valid is
            accepted. Mixed-case-but-invalid raises a parse
            error with a message identifying the position of
            the first mismatched-case digit.

            Strict B1 (reject all non-canonical-EIP-55 case
            including all-lower and all-upper) was rejected:
            it defends against the same attack as lenient B1
            but at the cost of breaking widely-deployed
            tooling. B2 (render with a flag in the label) was
            rejected because Ethereum users have a
            checksum-aware mental model already (their wallet
            enforces it); silently rendering and flagging
            invites the user to ignore the flag. B3 (preserve
            user case verbatim) was rejected because it would
            make two valid representations of the same address
            (lower-only and mixed-case canonical) produce
            different entvizes — an own-goal against entviz's
            core "equivalent inputs render identically" principle.

            Implementation lands in a follow-up commit; the
            spec edit accompanying this decision documents the
            behavior so spec and code stay aligned.

        UUID Dashless Input Is Permanently Accepted = decision:
          id: uu1ddash
          why: >
            Review F7 noted that entviz accepts UUIDs whose
            dashes have been stripped (32 hex characters
            instead of the canonical 8-4-4-4-12 grouping) and
            asked whether this should be flagged as non-
            standard. The decision is: this is permanently a
            non-issue, not deferred.

            Rationale: RFC 4122 defines the UUID's identity as
            its 128 bits, with dashes as a *display*
            convention, not as part of the value. Many
            real-world contexts (URLs, database keys,
            filesystem identifiers) routinely emit UUIDs
            without dashes for compactness. Treating these as
            non-standard would force users to insert
            cosmetically-required dashes before entviz
            comparison — adding friction that defends nothing,
            since the fingerprint is byte-identical whether
            the input has dashes or not.

            This decision is recorded explicitly so that
            future adversarial reviews of this codebase will
            not re-flag UUID dashless acceptance as a finding
            to consider. It is intended behavior. The spec at
            docs/spec.md documents this in the normalization
            section.

            Apply to: UUID parser only. (Other dash-bearing
            formats — Bitcoin cash bech32 with the
            `bitcoincash:` prefix, SSH key `ssh-ed25519` type
            strings — have different semantics and are not
            governed by this decision.)

    Additional-Patterns Triage = goal:
      id: fa1tr14g
      status: drafted
      why: >
        Adversarial review of 2026-05-27 listed twelve
        "Additional Patterns Noted" below the top-7 finding
        threshold (F-A1 through F-A12). This node records the
        maintainer's disposition of each: which were fixed in
        code, which were accepted as documented limitations,
        which were classified as permanent non-issues, and
        which were deferred for later revisit.

      children:

        FA1 Thread Safety Of Disproof Order = decision:
          id: fa1thrd1
          why: >
            `entviz/entropy.py` previously rebuilt the
            `_DISPROOF_ORDER` cache lazily by mutating a
            module-level global. Safe in the CLI's single-
            threaded use; a race in any multi-threaded server
            context (the planned cross-repo React component
            will likely call `parse()` from a backend pool).
            Fixed in code: the order is computed eagerly at
            module import or guarded by a lock — see the
            implementation. Cheap insurance.

        FA2 Ethereum Prefix Case Normalization = decision:
          id: fa2pf1xc
          status: nonissue
          why: >
            The adversarial review predicted that `0xDEAD…`
            and `0XDEAD…` would follow different parser paths
            and produce different `type_name` labels (`ETH`
            vs `hex(N)`). On investigation this prediction
            did NOT match the current code: `ETHEREUM_REGEX`
            already uses `re.I`, and `parse_ethereum_address`
            already runs before `parse_hex` in dispatch
            order, so both prefix cases route through the
            Ethereum parser and produce identical labels.
            The review's F-A2 was a speculative finding the
            author did not verify by running. No code change
            needed; pinned via regression tests in
            test_adversarial_additional.py so the property
            remains stable against future parser-order
            refactors.

        FA3 Wider ClipPath Salt = decision:
          id: fa3cl1p1
          why: >
            v4's `grid-clip-{first_8_hex}-{cols}x{rows}` id
            had a 32-bit salt — birthday-bound collision
            around ~65k entvizes on one HTML page. v5 widens
            to `first_16_hex` (64-bit salt → ~4B headroom).
            Future-proof for galleries, demo pages, and the
            planned spot-check React component. Spec updated
            (docs/spec.md SVG implementation notes); code
            change lands alongside.

        FA4 ViewBox For Responsive Embedding = decision:
          id: fa4v1wbx
          why: >
            v4 root `<svg>` had only `width`/`height` and no
            `viewBox`. Consumers setting `width="100%"` got
            fixed-pixel sizing instead of proportional
            scaling. v5 mandates
            `viewBox="0 0 {bounding_width} {bounding_height}"`
            on the root SVG so the entviz scales cleanly when
            embedded responsively (relevant for the React
            component and for any HTML embedding generally).

        FA5 Font Fallback Chain = decision:
          id: fa5f0nt1
          why: >
            v4 used a bare `style="font-family: monospace"`,
            letting each viewer's OS pick its own monospace
            with materially different glyph metrics and
            homoglyph behavior (Menlo on macOS, Consolas on
            Windows, DejaVu/Liberation/Ubuntu on Linux). This
            is security-relevant: an entviz's text channel
            depends on the user reliably distinguishing
            characters like 0/O, 1/l/I, 5/S, -/_, and font
            substitution can flip distinguishability.
            v5 pins the fallback chain to
            `"DejaVu Sans Mono", "Consolas", "Menlo",
            "Liberation Mono", monospace` — explicit named
            fonts on Linux/Windows/macOS with `monospace` as
            the final safety net. Not bundling a webfont
            (avoids licensing complications). The spec's
            font-choice section now documents the homoglyph
            risk for implementations that deviate from the
            chain.

        FA6 Mix-Blend-Mode Render-Environment Dependence = decision:
          id: fa6m1xbl
          why: >
            The long hand on the blank-cell marker uses
            `mix-blend-mode: difference` to invert against
            the white disc and black rim. Well-supported in
            all major browsers but silently ignored by
            `cairosvg` (the common server-side PNG renderer),
            making the maxftok direction indicator invisible
            in cairosvg PNG output. This is a real but
            bounded limitation: the maxftok direction is
            still conveyed via the short hand's terminator
            circle (the maxftok orientation, not the minftok,
            is the encoded direction — short hand is the
            one that doesn't depend on mix-blend-mode).
            Decision: document the dependence in
            docs/spec.md (cell-rendering section) and offer
            two consumer-side workarounds (use a browser-
            based renderer like Playwright/Puppeteer, or
            post-process the SVG to substitute a directly-
            stroked dark hand before rasterizing). No code
            change; no fallback path in the renderer itself
            because the browser path is the canonical
            rendering surface.

        FA7 CLI Output File Validation = decision:
          id: fa7c11ut
          status: nonissue
          why: >
            `app.py --output` accepts an arbitrary user-
            supplied path and overwrites without prompting.
            Standard CLI behavior; the user invokes the tool,
            names the file, owns the consequence. Recorded
            as a permanent non-issue so future reviews don't
            re-flag it. (If a `--force`/`-f` confirmation
            gate is ever wanted, it would be additive, not a
            change of contract.)

        FA8 sys.path.insert In Bin Script = decision:
          id: fa8sysp1
          status: nonissue
          why: >
            `bin/entviz.py` does `sys.path.insert(0, …)` to
            find the local `entviz` package. In an
            adversarial multi-user setup where another user
            can write to the script's directory, this would
            allow shadow-importing a malicious `entviz`
            package. Bounded by filesystem permissions; it is
            the standard Python script idiom for in-tree
            development. Permanent non-issue. If entviz ever
            ships as an installed wheel via `pip install`,
            the script-installer path replaces this entirely.

        FA9 Background Color Is 2 Bits = decision:
          id: fa9bg2b1
          status: accepted
          why: >
            The entviz background color is chosen from 4
            candidates by the 2 low-order bits of the median
            ftok's quant. A T1 grinder matches the
            background in an expected 4 trials. This is
            acknowledged in the spec as a *hint* channel —
            its job is to make two unrelated entvizes look
            unrelated at a glance, not to provide
            independent collision resistance. Serious
            collision resistance lives in the surround
            pattern, the color bar histogram, the ellipse
            overlay, the blank-cell positions, and the
            quartile marks. v5 spec now quantifies the bg's
            attacker cost explicitly so an implementer
            doesn't mis-rely on it. No widening of the
            bg-bit budget: that would invalidate every v4
            golden render for a hint-only channel.

        FA10 Bech32 Separator Disproof Limitation = decision:
          id: f4d1sp10
          status: deferred
          why: >
            Bech32's alphabet excludes `1` (it's the separator
            character), so a bare bech32 fragment containing
            `1` fails bech32 disproof and resolves to a
            different alphabet (base58/base64/base64url/UTF-8
            fallback). Real bech32 addresses with their
            `bc1`/`tb1`/`ltc1`/`addr1`/`bitcoincash:` prefixes
            are handled correctly by the specific-format
            parsers ahead of disproof; this caveat applies
            only to bare fragments pasted without their
            prefix — an unusual case. v5 spec documents the
            caveat in the alphabet-detection step. Deferred
            rather than fixed because the fix (recognize
            unprefixed bech32-with-separator via a smarter
            disproof) would add complexity for a narrow win;
            revisit if a real user reports confusion.

        FA11 SVG Injection Regression Test = decision:
          id: fa11svxi
          status: done
          why: >
            Implementation is safe because the SVG emission
            uses `lxml.etree`'s `.text =` assignment, which
            escapes `<`, `>`, `&`, and quotes. v4 had no
            test exercising this path. Resolved in commit
            d5144fc as part of the F1–F4 fix batch: a
            regression test now asserts hostile cell-text
            input is HTML-escaped in the output SVG.

        FA12 BCH Unprefixed Acceptance = decision:
          id: fa12bchu
          status: nonissue
          why: >
            `parse_bitcoin_cash_address` accepts strings
            matching `[pq]<41 bech32 chars>` even without the
            `bitcoincash:` or `bchtest:` prefix. After the
            F4 fix (regex now `$`-anchored), trailing junk
            is rejected. The unprefixed form IS legitimate
            per the Bitcoin Cash spec — many tools emit it
            that way for compactness. Classifying it as BCH
            is correct, not a misclassification. Permanent
            non-issue.

        EOS Regex Char-Class Residual = decision:
          id: 3osr3sd1
          status: deferred
          why: >
            After F1 (parse_eos_address moved to run AFTER
            parse_hex in the dispatch order), lowercase pure-
            hex inputs are correctly classified as hex
            instead of EOS. But the EOS regex's character
            class `[a-z1-5.]` still overlaps with lowercase
            hex letters `[a-f]`, so a 12-char input that
            happens to be all-hex would parse as EOS only if
            parse_hex somehow failed first (it doesn't,
            because hex always wins now). The residual is
            "narrow heuristic over a too-permissive char
            class" — not exploitable today, but it would
            re-surface if the dispatch order is ever
            reshuffled. Recorded here so a future review
            doesn't re-flag the same overlap and the
            reshuffle-resistance is understood: anyone
            considering changing parser dispatch order must
            verify the EOS regex doesn't regain priority
            over parse_hex. The proper long-term fix is to
            tighten EOS_REGEX to require >=12 chars or at
            least one non-hex character, but that is a
            separate decision with its own legitimate-input
            test surface; deferred.

    Snowflake Support = decision:
      id: sn0wfl4k
      status: drafted
      why: >
        Add support for Twitter/Discord/Mastodon "snowflake"
        IDs — 64-bit integers serialized as 17-20 decimal
        digits. Snowflakes carry a known bit layout (42-bit
        timestamp || 10-bit machine || 12-bit sequence) but
        are exchanged as opaque decimals; users comparing
        them today fall back to character-by-character which
        is exactly the failure mode entviz exists to solve.

        Three design choices recorded here so they survive a
        future re-read of the parser code:

        (1) DECIMAL alphabet, verbatim rendering. The cell
            text shows the original decimal digits, not a
            hex re-encoding of the underlying 64-bit value.
            Token alignment uses 4 bits/char (token_len = 6,
            matching HEX) even though decimal's true entropy
            density is ~3.32 bits/char. This is the same
            modeling shortcut already used for BASE36 and
            BASE58 (whose true densities are ~5.17 and ~5.86
            respectively): the bits_per_char field controls
            token packing, not quant accuracy, and a slight
            overshoot just means a few low-order bits of the
            quant are zero-padding instead of entropy. The
            tradeoff was considered against re-encoding to
            hex (cleaner bit alignment, but the user pasted
            decimal and would see hex in the cells — a
            surprise that defeats the verbatim-text guarantee
            in the spec's Guarantees section).

        (2) Plausible-timestamp range check. A bare 17-20
            digit decimal is ambiguous (bank account, phone,
            tracking number, random integer). Detection
            requires that the top 42 bits, interpreted as a
            Discord-epoch timestamp (2015-01-01 UTC), decode
            to a date in [2015-01-01, today + 5 years]. The
            5-year future window absorbs clock skew, fake
            future IDs, and the slow drift of "today" as the
            codebase ages without weakening the filter
            meaningfully. Twitter snowflakes from 2010-2014
            (Twitter epoch is earlier) are rejected; a
            future broadening to Twitter's epoch is possible
            but no current entropy-comparison use case
            warrants the wider false-positive surface.

        (3) Parser ordering: parse_snowflake must precede
            parse_hex in the dispatch chain because every
            decimal string is also a valid hex string. The
            parse_funcs list registration loop walks
            globals() in definition order and parse_hex is
            explicitly appended at the end (see the comment
            block above `parse_funcs.append(parse_hex)`), so
            any parser defined in the module body wins. This
            decision documents the dependency for any future
            refactor that changes parser registration.

        DECIMAL is intentionally NOT added to the disproof-
        fallback order: pure-digit strings outside the
        snowflake length/timestamp window correctly fall
        through to HEX (which contains all decimal digits)
        and are visualized as hex. Adding DECIMAL to the
        disproof set would steal those inputs from HEX with
        no benefit — the resulting entviz would be identical
        in the text channel and would differ only in the
        type label, which is not a user-visible improvement
        for arbitrary decimal blobs.

    Spec-Implementation Audit Triage 2026-06-02 = goal:
      id: aud0602t
      status: done
      why: >
        A full spec-vs-implementation audit on 2026-06-02 found
        two real implementation bugs and two spec-internal
        inconsistencies. All four were fixed. This node records
        the dispositions.

      children:

        AUDIT1 Quant Bit-Extension Pad Source = decision:
          id: qb1tpad1
          why: >
            tokenize() in entviz/entropy.py extended a partial
            token's value to 24 bits by repeatedly appending the
            low-order bits of the ORIGINAL value (`val & mask`).
            spec.md lines 155-174 require appending the low-order
            bits of the CURRENT (already-extended) quant
            (`quant & mask`). The two coincide for 8/12/16/20-bit
            partials (one doubling, or val==quant at the divergent
            step) but diverge for 4-bit partials, which need three
            doublings: the spec's own worked example 0x5 ->
            0x555555 was computed by the code as 0x550505.

            Blast radius: the nucleus background color of any cell
            holding a 4-bit partial token (hex/decimal inputs whose
            final chunk is a single character — char count
            ≡ 1 mod 6). ftoks are unaffected (the partial ftok is
            always 8 bits). Fixed by changing `val & mask` to
            `quant & mask`; regressions pinned by
            test_tokenize_4bit_extension_repeats_current_quant.

        AUDIT2 Ellipse Overlay r_min = decision:
          id: 3llrmin1
          why: >
            _draw_ellipse_overlay in entviz/pipeline.py set
            r_min = cell_h, but spec.md line 274 specifies
            r_min = nucleus_height (= cell_h/2). The function's own
            docstring already said cell_h/2, so the code contradicted
            both the spec and its own comment. Effect: every overlay
            was sized off an inflated floor (2x at the minimum), and
            the r_max <= r_min guard tripped more often on small
            grids, occasionally suppressing the overlay entirely.
            Fixed to r_min = cell_h / 2; the stale v3_ellipse_params
            docstring (which also said cell_h) was corrected.
            Regression pinned by test_v5_ellipse_rmin.

        AUDIT3 Spec Line 149 Ftok-Cell Mapping = decision:
          id: sp149fx1
          why: >
            spec.md line 149 claimed large-input middle cells use
            ftoks 9..12 and tail cells use ftoks 14..21 ("cell index
            -> used ftok index"), contradicting line 188 ("used ftok
            at index i drives the token with token_index i"). The
            implementation follows line 188 (the 20 tokens carry
            contiguous token indices 0..19, so middle uses ftoks
            8..11 and tail uses 12..19; ftoks 20-21 unused). Line 149
            was the wrong statement; corrected to the token-index
            mapping. No code change — flagged to prevent a future
            "fix" toward the erroneous line. See also [[c4s3norm]].

        AUDIT4 Spec Line 101 Base32 Case Direction = decision:
          id: sp101fx1
          why: >
            spec.md line 101 listed base32 among alphabets that
            "lowercase" before fingerprinting, but the parsers
            uppercase base32 cores (RFC 4648 canonical; Stellar and
            IPFS CID v1). Not a behavioral bug — case-insensitivity
            holds because the regexes accept either case and
            normalize consistently — but the spec text was wrong and
            contradicted its own base32 alphabet note (line 116).
            Corrected line 101 and the [[c4s3norm]] this.i entry to
            state base32 canonicalizes to upper case.

    V6 Migration = goal:
      id: v6m1grat
      status: implemented
      why: >
        Move from spec v5 to v6 (canonical at docs/spec.md; v5 archived in
        git history). v6 is a rendering-only revision — tokenization,
        fingerprint, and the text channel are unchanged from v5. Four
        changes, all motivated by legibility / robustness rather than the
        threat model. Driven in the 2026-06-02 working session; see
        reviews/ellipse-audit-2026-06-02.md.

      children:

        Color Bar Width Doubled = decision:
          id: v6barwid
          why: >
            v5 reused box_height (10px at 12pt) as the color-bar width, so
            the per-band letters (w/g/r/b/k, added in v5 for CVD/monochrome
            legibility) were capped at bar_width x 0.85 ~ 8.5px and read as
            tiny. v6 introduces bar_width = 2 x box_height = 1.25 x
            font_size_px (20px at 12pt) as a named geometry term, doubling
            the letter cap to ~17px. Ripple: bounding_width, the interior
            separator x (1 + bar_width + 0.5), the grid_rect origin x, and
            every geometry golden shift by +10px. The letter-size formula
            already read bar_rect.width, so it picked up the wider bar with
            no formula change. See [[v5cblet1]].

        Blank-Cell Map Replaces Clock Hands = decision:
          id: v6blnkmp
          why: >
            v5's blank-cell marker was a white disc with two clock hands
            pointing at the maxftok/minftok cell *directions* (angles). The
            long hand relied on mix-blend-mode:difference, which cairosvg
            and other non-browser renderers silently drop (adversarial
            finding F-A6), so the maxftok indicator vanished outside
            browsers. It was also ambiguous: an angle names a ray, not a
            cell.

            v6: every blank cell gets a black-outlined rounded rect
            (corner radius font_size_px/8) coincident with the nucleus
            rect. The FIRST blank (lowest cell index) becomes a "map": the
            rect is filled (white normally, gold #ffd966 when the entviz
            background is white, so it always contrasts) and subdivided
            into a cols x rows logical grid mirroring the entviz; a red dot
            (#d62828) marks the maxftok cell's (row,col) and a blue dot
            (#1d4ed8) the minftok cell's. Degenerate min==max (single used
            ftok) draws a blue ring with a concentric red dot. This is
            position-based (names the exact cell), renderer-independent (no
            mix-blend-mode, closing F-A6 for this channel), and one map per
            entviz (the rest of the blanks are bare outlines). Decisions
            confirmed with the maintainer: red=max/blue=min; first blank
            only; rect = nucleus rect (sub-cells stretched, not letterboxed
            to grid AR); gold (not an arbitrary yellow) for the white-bg
            fill. Tests in tests/test_v6_blank_map.py.

        Ellipse Coverage Clamp = decision:
          id: v6elclmp
          why: >
            The 2026-06-02 ellipse audit (reviews/ellipse-audit-2026-06-02.md)
            found the v5 radius bounds [nucleus_height, d_far - cell_width]
            sound on every grid (no degenerate math) but mis-sized at the
            tails: 3-11% of draws covered <8% of the grid (invisible
            slivers) and up to 7-10% on large/near-square grids covered
            >80% (swamping the entviz, killing the dark/light gestalt that
            is the overlay's whole purpose). Diversity was fine under the
            correct OR discrimination model (coverage OR location OR aspect
            differs => distinguishable; collision ~0.5-2.2%).

            Fix: clamp both semi-axes to [0.22 x d_far, 0.58 x d_far]. Both
            bounds scale with grid size (via d_far), so coverage lands in
            ~8-70% (median ~32%) on every grid, and the bound also fixes the
            small-grid radius-discretization (step now scales with d_far).
            A grid-relative clamp (rx <= k x grid_width) was tried first and
            rejected: corner anchors clip small ellipses to near-nothing, so
            it tanked the floor. Constants chosen by sweeping + eyeballing
            rasterized candidates (scripts/ellipse_prototype.py, candidate
            A) with the maintainer. 0.58 > 0.22 always, so the range is
            never degenerate. Replaces the v5 r_min=nucleus_height rule
            pinned by [[v5m1grat]]'s test_v5_ellipse_rmin (reworked).

        Font Fallback Chain Refresh = decision:
          id: v6fontch
          why: >
            v5's F-A5 chain ("DejaVu Sans Mono", "Consolas", "Menlo",
            "Liberation Mono", monospace) covered Linux/Windows/macOS but
            left Android/iOS to the bare-monospace fallback and led with a
            Linux-only face. The maintainer asked for solid coverage on
            Windows/macOS/Linux/iOS/Android. Embedding a pinned font (the
            only way to get *identical* glyphs cross-platform, and the only
            way to defeat cross-implementation divergence) was considered
            and declined: it would force every conformant implementation to
            ship and embed the same licensed font, and the font-independent
            gestalt channels already carry visual comparison while the text
            channel only needs to be individually readable. v6 instead
            refreshes the named chain to "JetBrains Mono", "Menlo",
            "Consolas", "DejaVu Sans Mono", "Liberation Mono", "Roboto
            Mono", "Noto Sans Mono", monospace: JetBrains Mono leads (best
            homoglyph disambiguation; used by those who have it), then each
            platform's native preinstalled mono (Menlo=macOS/iOS,
            Consolas=Windows, DejaVu/Liberation=Linux, Roboto/Noto=
            Android/ChromeOS), then the generic. See [[v5m1grat]] F-A5 note.

        Dev-Only SVG Rasterizer (render group) = decision:
          id: v6rendgp
          why: >
            cairosvg was dropped in 0.5.0 (only one skipped pixel-diff test
            used it). The v6 work needed to *see* rendered output to tune
            the ellipse clamp and verify the blank-cell map. Re-added
            cairosvg + numpy as an opt-in PEP 735 dependency GROUP
            ("render"), mirroring the existing "docs" group, so it is a
            dev/authoring tool only — never a runtime dependency of the
            shipped library (which emits SVG). Used via
            `uv run --group render ...`. CI goldens stay dependency-free
            (structural assertions, not pixel diffs); the rasterizer is a
            bench tool for visual confirmation and gallery PNG/PDF artifacts.

        Long-Input Middle = Fingerprint, Not Body Slices = decision:
          id: v6fpmid1
          why: >
            v5 closed adversarial finding F5 by filling the 4 middle cells
            of a >512-bit input with entropy BODY slices sampled at
            fingerprint-derived offsets (see [[v5mid1sl]]). Empirically
            (tests/test_v6_fingerprint_middle.py), that made the middle
            TEXT differ between two inputs only probabilistically: a
            low-entropy or structured body could render identical middle
            cells for different inputs, so a screen-reader / read-aloud
            comparison (no access to the gestalt channels) could miss a
            real difference. The maintainer's requirement: the middle text
            must be GUARANTEED to differ on any input change.

            v6 fills the middle from the MIDDLE OF THE FINGERPRINT — digest
            bytes 24-35 (the 3-byte groups behind ftoks 8-11) — rendered in
            the INPUT'S alphabet via a bit-chunk encoder
            (_fingerprint_token_text), so token length / charset / font size
            match head/tail exactly (no base64url-vs-input mismatch). The
            fingerprint avalanches by construction, so the middle text is
            guaranteed to change on any 1-bit input change. Head/tail stay
            real entropy (recognition + verification).

            NOT a weakening (maintainer's hard constraint): gestalt is
            untouched; F5 resistance is comparable — matching the 4 shown
            fingerprint tokens is a ~2^96 partial preimage of SHA-512, vs
            v5's ~2^96 body-window match at moving offsets — and arguably
            stronger (exact hash bits, not a lossy gestalt projection).
            Losslessness promise is unaffected: it only ever applied to
            <=512-bit inputs, which don't use this path.

            Rendering: the 4 middle nuclei are painted with the entviz
            background color (neutral/hollow) since they carry no entropy in
            their bg — visually distinct from the entropy-colored head/tail,
            and already bracketed by the two separator blanks. Their surround
            stays ftok-driven (still avalanches). Dropped the v5 body-slice
            offset/guard math (derive_middle_slice_offsets et al.). The
            `fingerprint of` truncation marker (renamed from `part of`) now
            literally describes the middle cells. Format question raised by
            the maintainer (base64url ftoks would mismatch a hex input's
            head/tail) resolved by rendering in the input alphabet. AGREED
            follow-up: re-run the adversarial lens on the new text channel.

        Middle = Domain-Separated Second Hash, Rendered Hex = decision:
          id: v6fpmid2
          why: >
            The agreed follow-up adversarial pass (adversarial-2026-06-02)
            found two real defects in v6fpmid1's "primary-digest bytes 24-35,
            rendered in the input's alphabet" scheme:

            F1 (avalanche not actually guaranteed). Rendering 24 bits in the
            input's alphabet via _fingerprint_token_text drops bits on
            non-hex alphabets: 5-bit alphabets (bech32/base32/crockford32)
            show only the top 20 of each cell's 24 bits (token_len=4), so the
            low nibble of every 3rd middle byte is NEVER shown — two inputs
            whose digests differ only there render IDENTICAL middle text
            (measured). And the spec falsely claimed non-power-of-2 alphabets
            "never reach the path" — a 200-char base58/base36 paste DOES
            truncate, and the mod-fallback aliases group values badly. So the
            "guaranteed avalanche for read-aloud" promise was false for those
            alphabets; real displayed entropy was 80 bits (5-bit) or less.

            F2 (middle not independent of gestalt). Bytes 24-35 of the PRIMARY
            digest also feed the color bar and the middle cells' own surround,
            so matching the displayed middle matched those gestalt channels for
            free; the spec's "match the middle AND independently match the
            gestalt" overstated a barrier that was actually correlated.

            Fix (maintainer agreed both): (1) render the middle as HEX, 6
            lowercase chars = a full 24 injective bits per cell, regardless of
            input alphabet — the cells are already marked as a hash readout
            (neutral bg + frame + `fingerprint of`), so hex is appropriate and
            signals "digest, not your data". (2) derive the middle from a
            SECOND, domain-separated digest second = SHA-512(DOMAIN_TAG||core),
            DOMAIN_TAG = b"entviz/fingerprint-middle/v6\0", uncorrelated with
            the primary fingerprint. Now the 96-bit (4×24) partial-preimage
            claim is EXACT and uniform across alphabets, and is independent of
            matching the gestalt. _fingerprint_token_text and _match_core_case
            deleted (dead). Spec lines (summary, goals, middle group, "why",
            "rendering", threat para) rewritten; the false "never reach the
            path" claim removed. Tests rewritten to prove hex-regardless-of-
            alphabet, 5-bit injectivity, exact second-digest value, and
            primary-digest independence. See [[v6fpmid1]].

        Unify Large-Input Blank Placement = decision:
          id: v6blnkun
          why: >
            v5 (and v6.0) gave every >512-bit entviz an IDENTICAL blank
            layout: the large-input path bypassed the median/quartile
            blank-shift and hard-coded two "separator" blanks at cell
            indices 8 and 13 to visually delimit head|middle|tail. The
            maintainer (author) flagged that two very different large inputs
            looked structurally identical, and correctly noted head/middle/
            tail are a LOGICAL token ordering, not fixed cell positions —
            there was no real reason to bypass the shift.

            v6 removes the bypass: large inputs now call the same
            assign_cell_indices(median, ASCII-endpoints) shift as short
            inputs. Token order (head→middle→tail, indices 0..19) is
            preserved, so reading order is unchanged, but blanks are now
            placed by the fingerprint and VARY per input — restoring the
            CRC-like blank-position channel for large inputs. The grid stays
            choose_grid(22) (4x6 = 24 cells → 4 blanks) so the shift has
            slack. No fixed separators remain.

            The explicit head|middle|tail delimiter is dropped, but it's
            redundant now: the 4 fingerprint cells are individually marked
            (neutral bg + gold/white frame, and a new data-cell-fingerprint
            attribute so overlays/tests can find them by position), and the
            `fingerprint of` marker already signals a non-linear read.
            Closes the "all large entvizes share one layout" complaint.
            See [[v6fpmid1]].

        Darken Gold to Maximin Lightness = decision:
          id: v6goldlt
          why: >
            Adversarial finding F3 claimed the palette collapses under CVD.
            Investigation (the maintainer hand-tuned the original palette by
            luminance) showed F3's specific diagnosis (gold/red collapse) was
            WRONG — gold/red is lightness-saved AND hue-backed. The real weak
            pair was white/gold: at v5's gold `#ffd966` (CIELAB L*≈88) the
            white→gold gap was only ΔL*≈12, the smallest in the palette, and
            white/gold blurred together on a grayscale / achromat rendering.

            Lightness is the only channel that survives CVD, monochrome, and
            color-filtering, so the fix is to space the colors on L*. Holding
            white(100)/red(57)/blue(34)/black(0) fixed and moving ONLY gold's
            lightness, the maximin (white/gold gap == gold/red gap) is at
            L*78.5: both gaps ≈21. Adopted gold `#e7be00` — L*78.4, max chroma
            at that lightness (C*80, up from #ffd966's 60). Chroma maxed on the
            maintainer's call: gold/red leans on the yellow-vs-red HUE cue, so
            a stronger gold hue reinforces the pair that took the smaller
            lightness gap. White/gold has no hue backup, which is why the
            lightness budget is spent equalizing it, not gold/red.

            Rejected alternatives: (a) L*80 #ecc300 — I initially recommended
            it for a marginally better deuteranopia gold/red (ΔL* 18.3 vs 17.2),
            but the maintainer correctly noted gold/red's hue cue makes that 1.1
            difference perceptually irrelevant, so the true maximin (78.5) wins.
            (b) the ΔE76-optimized palette (gold L*75/red L*50/blue L*25) —
            ΔE76 over-credits chroma (the fragile channel) and regressed
            perceptual quality; ΔE76 is NOT a safe optimization metric here.

            HONEST LIMIT: protanopia red/blue stays pinned at ΔL*≈7 for ANY
            gold (red darkens under protan; no lightness assignment fixes it).
            Those two rely on the retained blue-yellow axis + color-bar letters
            (`r`/`b`). Palette is robust, not CVD-proof. Spec palette-rationale
            paragraph + CVD honesty caveat updated to say so. Validated by
            per-CVD ΔL* sweep and by-eye (.cache/palette_gold_chroma.html);
            do NOT trust ΔE76. See [[v6fpmid1]].
