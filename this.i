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

    Casual Avalanche Levers = decision:
      id: c4sav1nc
      why: >
        v10 (DRAFT, docs/spec-v10-draft.md). Comparison has two modes —
        casual (a glance, reading the colour gestalt) and careful (cell by
        cell). Bandwidth is mode-dependent: the surround PATTERN avalanches
        for careful comparison but is casually invisible (Fig 4b), and the
        colour gestalt — the channel a glance actually uses — barely moves on
        a one-char change (nucleus = entropy, surround echoes it, background
        is only 2 bits). Measured: 27.1% of background-unchanged neighbours
        are casually colour-identical (n=100k; experiments/casual-avalanche).
        Fix: put fingerprint signal into colour, as a few discordant colour
        SINGLETONS that pop out pre-attentively. Top-left cell (first
        fixation) + 1st/2nd quartile cells (already fingerprint-positioned,
        and they move) take their surround edge colour from 2 ftok bits
        instead of nearest-to-nucleus; blanks fill from the fingerprint with
        a HYBRID map-blank rule (colour the map blank iff it is the sole
        blank — markers stay legible by shape, not hue — else keep it a white
        anchor and colour its siblings). Partiality is REQUIRED: singletons
        must stay rare to pop, which also scales down to small inputs.
        Locked result: hard-quarter colour-miss 27.1% -> ~0.5%, every type
        <= ~2%. Adds casual salience only, NOT collision resistance. The four
        >512-bit fingerprint cells are deliberately left neutral: they
        avalanche in their text, large inputs already discriminate casually,
        and they anchor the coherent field the singletons pop against.

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

            v8 (SPEC-F3): the disproof-fallback path
            (detect_alphabet_by_disproof in parse_entropy) was
            the lone violator of this rule — it lowercased EVERY
            case-insensitive alphabet it detected, including
            base32. So a bare base32 fragment that missed the
            specific parsers (Stellar/CIDv1) fingerprinted under
            a LOWER core while the same value via a specific
            parser fingerprinted under an UPPER core — a per-
            alphabet inconsistency that changed the SHA-512 and
            every channel. Fixed by uppercasing base32 (and only
            base32) on the disproof path, matching the specific
            parsers. This did NOT change base32's normalization
            rule (it was always UPPER); it brought the outlier
            path into line. spec.md's disproof step said "treats
            the input itself as the normalized core ... no
            re-encoding", which read as exempting the path from
            case canonicalization; clarified in v8 that "no
            re-encoding" means no alphabet re-serialization and
            does not waive per-alphabet case normalization.
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

        (2) Deterministic structural validity check (v8,
            SPEC-F1). A bare 17-20 digit decimal is ambiguous
            (bank account, phone, tracking number, random
            integer), so detection needs a second filter beyond
            length. Through v7 that filter was a PLAUSIBLE-
            TIMESTAMP WINDOW: the top 42 bits, read as a
            Discord-epoch (2015-01-01 UTC) timestamp, had to
            fall in [2015-01-01, today + 5 years]. The upper
            bound consulted the WALL CLOCK (time.time() via
            _now_ms), which made the SAME input render
            DIFFERENTLY over time: a boundary decimal whose
            implied date sits just past "now + 5y" parsed as
            hex today and as snowflake a few years later —
            different type label, different alphabet, different
            SVG. That is a direct violation of the spec's
            determinism MUST (spec.md "An implementation MUST be
            deterministic ... No part of the output may depend
            on wall-clock time"), and the frozen golden corpus
            could never catch it because it was generated at one
            instant.

            v8 replaces the wall-clock window with a CLOCK-FREE
            STRUCTURAL test: a canonical 64-bit snowflake is a
            non-negative signed integer, i.e. bit 63 (the sign
            bit) is clear, so n < 2**63. Reject when bit 63 is
            set. This is not an arbitrary cutoff — it is exactly
            the well-formedness of the layout: with the sign bit
            clear the 41-bit timestamp field (bits 22..62)
            decodes, by construction, to a date in
            [2015-01-01, ~2084], so "the implied date is
            plausible" becomes a structural property of the bit
            pattern rather than a comparison against the moving
            present. A truly absurd future decimal still fails,
            because its timestamp overflows the 41-bit field and
            sets bit 63. No clock, no pinned date, identical
            across implementations and across time. (The old
            n.bit_length() > 64 overflow guard is subsumed:
            n >= 2**63 already rejects everything from 2**63 up,
            including the >=2**64 overflow case.)

            Tradeoff, recorded honestly: dropping the future
            window WIDENS acceptance. The window admitted random
            18-digit decimals ~3.6% of the time; the structural
            rule admits ESSENTIALLY ALL 17-20 digit decimals
            below 2**63. So more non-snowflake decimals now
            classify as "snowflake". This is acceptable because
            the consequence is confined to the TYPE LABEL and
            tokenization (snowflake: + DECIMAL alphabet vs
            hex(N): + HEX) — both render the verbatim digits and
            both are deterministic, so comparison correctness is
            unaffected in either classification. Determinism (a
            spec MUST) outranks label precision (a cosmetic
            nicety). A future revision MAY add a clock-free
            tightening (e.g. rejecting all-zero machine/sequence
            bits) if the false-positive label rate proves
            annoying, but MUST NOT reintroduce any wall-clock
            dependence.

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

    Git Hash Schemes (SWHID / gitoid) = decision:
      id: g1tha5h0
      status: drafted
      why: >
        A git commit hash is a SHA-1 (40 hex) or, in sha256
        repos, a SHA-256 (64 hex), always lowercase hex with
        no affix, no checksum, no case information. It is
        therefore ALREADY handled correctly by the HEX
        alphabet today — entviz tokenizes and fingerprints it
        identically whether or not it is "recognized" as git.

        Decision (1): do NOT add a separate primitive for git
        hashes. Not a separate ALPHABET — an alphabet exists
        only to drive tokenization (bits/char -> token length),
        and a git hash is hex (4 bits/char, 6-char tokens); a
        "git" alphabet would be a byte-for-byte clone of HEX.
        Not a content-sniffing TYPE either — a 40-char lower
        hex string is indistinguishable from any other 160-bit
        value (a different SHA-1, RIPEMD-160, an HMAC, a random
        key), and a 64-char string from any other 256-bit
        value. Asserting type=git from length alone would be a
        confident guess that is wrong a large fraction of the
        time, violating the spec's "content inspection is
        unsound; each parser must DECLARE its alphabet"
        principle (spec.md tokenization step). It would also
        change zero pixels: fingerprint and every channel are
        byte-identical to plain hex. See also [[c4s3norm]].

        Decision (2): a bespoke `git:<hex>` prefix to make
        detection deterministic was considered and REJECTED.
        It is emitted by no tool and typed by no user, and it
        collides with the existing `git://` transport URL
        scheme; it would only ever fire for someone who already
        knew it was a git hash, so the label carries no
        information. Inventing a notation breaks the pattern
        every other prefix in the parser follows: each one
        (`0x`, `did:`, `bc1`, `ssh-...`, the multihash bytes)
        is a REAL format some tool actually produces.

        Decision (3): instead recognize the two REAL,
        standardized prefix schemes that namespace a git hash:
          * SWHID (Software Heritage IDentifier, ISO/IEC track):
            `swh:1:<type>:<40-hex-sha1>`, <type> in
            snp/rel/rev/dir/cnt. A git commit is `rev`.
          * gitoid (OmniBOR): `gitoid:<obj>:<algo>:<hex>`, obj
            in blob/tree/commit/tag, algo in sha1(40)/sha256(64).
        These satisfy the soundness bar a bespoke prefix could
        not: the prefix is an explicit, self-describing
        assertion present in the input (detection is
        deterministic, not a content guess), the prefix is real
        structure tools emit, and the label is INFORMATIVE — it
        distinguishes a commit (`rev`) from a file blob (`cnt`),
        an object type bare hex can never convey.

        Implementation choices that mirror the existing prefix
        parsers (parse_did / parse_hex's `0x` branch):
          (a) The scheme+type is the `prefix`; the hex is the
              `core` declared HEX; both are lowercased. Because
              compute_fingerprint hashes the CORE only, the
              prefix is excluded from the fingerprint, so
              `swh:1:rev:<h>`, `gitoid:commit:sha1:<h>`, and
              bare `<h>` visualize the SAME entropy and differ
              only in the label. This is the explicit guarantee
              the proposal was after ("fundamentals unchanged").
          (b) SWHID v1 is sha1-only (40 hex); a 64-hex body does
              not match. gitoid validates hex length against the
              declared algo (sha1->40, sha256->64) and rejects a
              mismatch rather than re-tokenizing a malformed id.
          (c) SWHID qualifiers (`;origin=...;lines=...`) are
              addressing context, not entropy. They are matched
              so a qualified SWHID is still recognized (instead
              of falling to the UTF-8 base64url garbage path),
              but they are a FREE annotation and are DROPPED, not
              surfaced — see [[sufxbind]]. (The first draft put
              them in `suffix`; that was a looser use of `suffix`
              than its checksum/derivation definition, corrected
              by the suffix-binding rule.)
          (d) Parser ordering is not sensitive: the `swh:` and
              `gitoid:` prefixes contain colons and match no
              earlier parser (DID requires a literal `did:`),
              and both are defined before parse_hex in the
              auto-registration walk.

    Multicodec CID Labelling = decision:
      id: mult1c0d
      status: drafted
      why: >
        The multiformats family (multihash, multibase,
        multicodec, CID, multiaddr) is mostly already handled:
        parse_multihash / parse_hex_multihash recognize raw and
        hex multihashes (MULTIHASH_HASH_FUNCS table), and
        parse_ipfs_cid recognizes CIDv0 (Qm.. base58) and CIDv1
        (b.. base32). The gap was the multicodec *content-type*
        layer — the registry that names what a CID wraps.

        Decision: decode a CIDv1's self-describing interior
        (the leading version / content-codec / hash-fn varints)
        to ENRICH THE LABEL only. A CIDv1's bytes are
        `<version><content-codec><multihash>`; reading those
        varints is deterministic (the bytes are physically
        present and self-describing) and therefore sound — the
        same justification that makes the existing multihash
        hash-fn table sound, and the opposite of a content
        guess. The label goes from a static "IPFS CID v1 256"
        to a decoded codec label (decoded via the new
        MULTICODEC_CONTENT table + the existing multihash table).
        The exact label form was later refined for brevity — see
        [[lbldedup]] (codec always shown, hash elided unless it
        departs from sha2-256; "IPFS " and the inter-token space
        dropped), giving e.g. "CIDv1 dag-pb". CIDv0 is
        dag-pb/sha2-256 by definition, so it is just "CIDv0".

        Label-ONLY, deliberately (see [[g1tha5h0]] for the same
        stance applied to git hashes):
          (a) The core stays the full base32 body and the
              fingerprint is unchanged, so existing CID entvizes
              do not shift. decode_multicodec_label is purely a
              naming step.
          (b) The version/codec/hash-fn bytes are structural
              framing and one COULD split them into the prefix
              (as parse_hex_multihash splits its 2-byte prefix).
              We do NOT, because those bytes are buried inside a
              base32 string whose 5-bit char boundaries do not
              align to the byte-varint boundaries; splitting
              cleanly would require base32-decoding the digest
              and re-encoding it, changing the cell text. That
              is a larger, breaking decision; deferred. The
              multihash parsers can split because their input is
              already raw bytes / hex (byte-aligned).
          (c) decode_multicodec_label is defensive: any
              malformed buffer, unknown codec, or unknown
              hash-fn returns None and the caller falls back to
              the plain "IPFS CID v1" label. binascii.Error from
              a bad base32 body subclasses ValueError and is
              caught.

        REJECTED (same soundness bar as [[g1tha5h0]]): a generic
        standalone multibase parser (f<hex>/z<base58>/m<base64>/
        u<base64url>/b<base32>). Outside a structurally-gated
        container like CID, the single-char multibase selector is
        indistinguishable from ordinary data — `f9fce0..` is
        equally base16-multibase or plain hex starting with f —
        so matching it by inspection would hijack and mislabel
        ordinary hex/base58/base64 inputs. Multibase is only sound
        when the input is DECLARED multibase by its container,
        which entviz already honors via the CID parsers. There is
        no `multibase:` wrapper to gate a generic parser on.
        multiaddr (/ip4/.. /tcp/..) is network addressing, not
        entropy, and is out of scope.

        Note on CESR AIDs/SAIDs (asked during this work): they
        are ALREADY handled. A KERI AID is a CESR primitive — a
        key (`D` Ed25519 transferable, `B` non-transferable) or a
        self-addressing digest; a SAID is a CESR digest primitive
        (`E` Blake3-256, `F`/`G`/`H`/`I` other 256-bit hashes,
        `0D`.. for 512-bit). parse_cesr recognizes all of these
        by derivation code + length. The label reports the
        cryptographic primitive ("CESR Blake3-256"), not the role
        word "AID"/"SAID", because AID-vs-SAID is a CONTEXTUAL
        role (the same Blake3-256 digest is a SAID when it
        self-addresses a document; a `D` key is an AID when it is
        an identifier prefix) and is not recoverable from the
        primitive alone — labelling it would be the same
        content-role guess that [[g1tha5h0]] rejects.

        SUPERSEDED in part by [[s3mpr3fx]]: the claim above that the
        CESR code is label-only (clause (a)'s "fingerprint unchanged")
        was WRONG. The CESR derivation code is identity-bearing: the
        same body under a different code is a different object, so it
        MUST bind the fingerprint. The fix keeps the code IN the core
        (it is base64url and contiguous), so it now drives both the
        cells and the fingerprint; the clause-(a) "fingerprint
        unchanged" symmetry no longer holds for CESR. NB the CID
        interior codec IS also identity (a dag-pb vs raw CID over the
        same hash is a different object) — but it is already bound,
        because in a CIDv1 it sits inside the base32 body that IS the
        core, so no change was needed there (see [[s3mpr3fx]]'s
        sweep). The gallery taxonomy was also corrected (`D` is a
        verification key, not "the transferable AID"; the usual
        transferable AID is the self-addressing `E`).

    Semantic Prefixes Bind the Fingerprint = decision:
      id: s3mpr3fx
      status: drafted
      why: >
        Reported as two CESR bugs (2026-06-06). Root cause is one
        gap: the parser splits a derivation code off as a `prefix`
        and the pipeline fingerprints `core` ALONE
        (compute_fingerprint(core)), so the code reached NEITHER
        channel — not the head/tail text cells and not the
        SHA-512-driven gestalt. It survived only as label text.

        Why that is wrong for CESR (and not for hex's `0x`): a
        CESR derivation code is IDENTITY-BEARING, not a signal.
        `B`, `C`, `D`, `E` may each precede the same 43 base64url
        chars to mean a non-transferable key / encryption key /
        transferable key / Blake3-256 digest — four different
        objects, and `B` vs `D` is the security-critical
        non-transferable/transferable split. With the code outside
        the fingerprint, those four rendered IDENTICALLY except for
        a label a user may not read — exactly the confusion entviz
        exists to prevent. `0x` is the opposite: it is constant for
        the format; no other prefix could precede the same 20 bytes
        to mean a different address, so it carries no identity bits.

        THE RULE — three categories (refined through discussion
        2026-06-06; full text in docs/spec.md). Classify every part
        of the input by whether it carries IDENTITY BITS:
          * PRESENTATION — how the value is written, not what it is
            (0x, multibase base selector, SSH/PEM framing, case).
            Normalized away: neither cells nor fingerprint; shown in
            the label as the encoding/type. Same principle as
            case-normalization, generalized to radix/serialization.
          * IDENTITY — a type/role discriminator that changes the
            denoted object (CESR code, LEI LOU, SWHID/gitoid
            object-type, CID multicodec). MUST bind the fingerprint.
          * ANNOTATION — freely attached (SSH comment, SWHID
            ;origin=…). Dropped. See [[sufxbind]] (suffix analogue).

        THE SWAP TEST distinguishes presentation from identity. Hold
        the body fixed and swap the prefix:
          * No legal alternative, OR the body must RE-ENCODE to stay
            legal → PRESENTATION. The body-must-re-encode case is the
            tell of an encoding selector (multibase f↔b forces
            hex↔base32). This sub-clause — added when the user probed
            why multibase is presentation — is what cleanly separates
            multibase (encoding) from multicodec (identity), which the
            bare swap test handled awkwardly.
          * Body byte-for-byte unchanged, meaning changes → IDENTITY
            (CESR B↔D↔E; SWHID cnt↔rev).

        MECHANISM — two ways to bind identity, by alphabet. Parsed
        has a `prefix_semantic` flag (default False). render()
        computes fingerprint_core = (prefix+core) if (prefix and
        prefix_semantic) else core, used by all three
        compute_fingerprint sites (used_ftoks, clip-id, ellipse).
          (1) IN THE CORE (preferred; same alphabet + contiguous):
              the discriminator is NOT split off — it stays in `core`,
              so it is rendered in the CELLS *and* hashed (we hash
              core TEXT, so this Just Works). Used by the CESR code
              (parse_cesr: prefix=None, core=whole primitive) and the
              LEI LOU (parse_lei: prefix=None, core=LOU+"00"+entity).
          (2) PREFIX-FOLD (different alphabet / not cell-stream-able):
              kept as `prefix` (label, not cells), prefix_semantic=
              True, hash input = prefix+core. Used by SWHID/gitoid
              (letters ahead of a hex body; parse_swhid/parse_gitoid).

        WHY CODE-IN-CELLS, not fingerprint-only (the user's Question
        A, 2026-06-06). The first v7 cut folded the CESR code into the
        fingerprint but left the cells as the body alone. That misses
        the TEXT channel for SHORT inputs: a 44-char CESR primitive
        has no fingerprint-middle cells (those exist only >512 bits),
        so the code reached the gestalt but no cell — a read-aloud of
        the cells could not tell B from D. v6's whole philosophy is
        "the text channel independently catches what the gestalt
        catches," so the code belongs in the cells. Keeping it in the
        core (mechanism 1) achieves cells+fingerprint with no split
        and is the most faithful (cells show the literal identifier).
        The fingerprint VALUE is unchanged from the fold cut (hashing
        core=prefix+core ≡ hashing prefix+core); only the cells gained
        the code.

        NO DELIMITER. The first proposal hashed `code + "\x1f" +
        core` out of generic anti-concatenation habit (boundary-
        shift collisions when joining two variable-length fields).
        The user pushed back; correctly. A CESR code is fixed-length
        and self-framing, so `prefix + core` is exactly the original
        primitive string and the (code, core) split is recoverable
        and injective — a sentinel adds nothing. Revisit only for a
        future VARIABLE-length semantic prefix, and even then prefer
        a length prefix over a sentinel.

        TABLE-CORRECTNESS FIXES (same report). (a) Blinding factor
        is lowercase `a` (44 chars); the code had it as capital `Z`,
        which is actually Tag11 (12 chars) — so real `a…` blinding
        factors failed to parse and bogus 44-char `Z…` strings would
        have been accepted. (b) Added the FN-DSA (FIPS 206)
        post-quantum codes `b`/`c`/`d`/`e` and `1AAQ`/`1AAR`, and
        relabeled `1AAB`/`1AAJ` to "pub/enc key" per the spec table.
        (c) Gallery taxonomy: `B` is correctly a non-transferable
        AID, but `D` is a bare verification key (the spec names it
        "Ed25519 public verification key", no "prefix"/AID
        qualifier), and the USUAL transferable AID is the
        self-addressing `E` (Blake3-256 of the inception event) —
        previously mis-filed only as "SAID". The B/D gallery pair
        now shares one body deliberately, to demonstrate that the
        code binds the fingerprint. Authoritative source:
        ../kswg-cesr-specification/spec/spec-body.md master code
        table. Supersedes the label-only CESR note in [[mult1c0d]].

        OTHER IDENTITY PREFIXES (swept 2026-06-06, same change).
          * LEI LOU — DONE (mechanism 1, in-core). Same 12-char body
            under a different LOU = a different registration. core is
            now LOU+"00"+entity; previously the LOU was split off
            structurally and left out of the fingerprint — the same
            bug as CESR.
          * SWHID / gitoid object-type+algo — DONE (mechanism 2,
            fold). Without it a SWHID content and a gitoid blob over
            the same git hash collide in every fingerprint channel.
          * multibase (CID leading b/f/z/m/u) — NO CHANGE NEEDED: it
            is PRESENTATION (the base selector), already stripped.
          * multicodec / CID content codec — NO CHANGE NEEDED: it is
            identity, but in a CIDv1 it lives INSIDE the base32 body,
            so it is already part of `core` text and already bound.
            (This corrects the earlier note that listed it as a
            pending fix; it was already covered.)
        Built on [[h4shtext]] (the fingerprint hashes core TEXT,
        which is exactly what makes mechanism 1 bind the in-core
        discriminator without any decode step).

    Fingerprint Hashes Text, Not Decoded Bytes = decision:
      id: h4shtext
      status: drafted
      why: >
        Surfaced 2026-06-06 while pinning the [[s3mpr3fx]] rule: the
        user assumed the fingerprint hashes the value's DECODED RAW
        BYTES; the implementation has always hashed the UTF-8 bytes
        of the normalized core TEXT (fingerprint.py:
        sha512(normalized_core.encode('utf-8'))). The spec said
        "SHA-512 of the normalized entropy bytes" — ambiguous, never
        ratified, and silently resolved to text by accreted code.
        Sober lesson on stating intentions precisely; the spec is now
        explicit (RFC 2119 MUST) either way.

        DECISION: keep hashing canonical normalized TEXT. Cross-
        encoding invariance is an explicit NON-GOAL (hex vs base64 of
        the same 32 bytes, or one CID in two multibases, render
        differently). Reasoning, after steelmanning both (the user
        asked for a red-team, not a rubber stamp):

          (1) FAIL-SAFE vs FAIL-UNSAFE. The text channel is verbatim
              by design (it shows the chars the user holds), so it can
              NEVER be made encoding-invariant without destroying
              fidelity. If the fingerprint hashed bytes, two encodings
              of one value would share a gestalt but show different
              cell text — the channels would DISAGREE about identity,
              the exact ambiguous signal entviz exists to kill.
              Text-hashing keeps all channels in agreement; its worst
              case is a FALSE NEGATIVE (fail to notice two encodings
              match → investigate further), never a false "same".
          (2) COLLISION SURFACE. Byte-hashing inserts a decoder before
              the hash, and base64/base58/bech32/base32 are MALLEABLE
              (distinct text → same bytes). That yields attacker-
              manufacturable "different text, identical gestalt"
              collisions — a primary win. Text-hashing denies the
              lever. (See threat-model.md, T3.)
          (3) CONFORMANCE. The 3-impl certification goal needs
              byte-identical output. Hashing UTF-8 text needs only
              case/punct normalization; byte-decoding every alphabet
              identically (base58 leading zeros, bech32 5-bit unpack,
              base64 trailing bits, decimal width) is a large,
              divergence-prone surface. The arbitrary-text fallback
              has no "raw bytes" but its UTF-8 anyway.

        NOTE the user's intent was principled — in a single-impl world
        optimizing for "true byte identity" it is defensible. The
        cost/benefit flipped once "verbatim text channel" and "3
        certified impls" became hard constraints.

        NOT a contradiction: decoding still happens to compute a
        token's 24-bit quant from its chars, and to measure core byte
        length for the >512-bit truncation threshold — but NEVER as
        the hash input. Identity discriminators are bound by living in
        the hashed TEXT (in core, or folded as prefix+core per
        [[s3mpr3fx]]), not by decoding. This is also exactly why
        mechanism (1) of [[s3mpr3fx]] works: an in-core code is part
        of the text, so it is hashed with no decode step.

    Additional Alphabets / Address Formats = decision:
      id: xtra4lph
      status: drafted
      why: >
        A batch of seven candidate formats was evaluated against
        the soundness bar from [[g1tha5h0]] (deterministic
        detection, no content-sniffing). Two were ADDED; five
        were DEFERRED as ambiguous or needing a larger design
        decision. The user explicitly asked to defer the hard
        ones rather than force them. (base62 was briefly added to
        the disproof ladder, then reverted — see below.)

        ADDED:
          (1) Stellar muxed accounts (strkey `M…`). Distinct
              prefix `M` and length 69 (vs a `G` account's 56),
              same RFC-4648 base32 alphabet. Deterministic;
              parse_stellar_address gained a second branch
              labelled "XLM muxed".
          (2) Generic checksum-validated bech32 (Cosmos-SDK
              chains: cosmos1/osmo1/juno1/…). The KEY point is
              that detection is made sound by VALIDATING the
              BIP-173/BIP-350 checksum (polymod), not by matching
              an arbitrary hard-coded HRP list — a random
              <letters>1<chars> string passes with ~2⁻³⁰
              probability. The HRP names the chain straight from
              the input (shown in the displayed prefix, e.g.
              "bech32: cosmos1..." — see [[lbldedup]]), so no
              chain registry is hard-coded. Runs AFTER the
              specific bech32 parsers (bc1/ltc1/addr1/CashAddr),
              which still win for their formats. `<hrp>1` is the
              prefix, the 6-char checksum is the suffix (as for
              LEI / Bitcoin-legacy), the rest is the BECH32 core.
        DEFERRED (each fails the soundness bar; revisit only with
        an explicit declaration mechanism):
          * Solana — a bare base58-encoded 32-byte ed25519
            pubkey with NO prefix and NO checksum. Indistinguishable
            from any other 32-byte base58 blob; labelling it
            "Solana" would be exactly the content-sniffing guess
            [[g1tha5h0]] rejects. (Contrast Bitcoin/Ripple, which
            carry base58check version+checksum and ARE detectable.)
          * JWK — a structured multi-field JSON document, not a
            single token. Visualizing it needs design decisions
            entviz does not currently make: WHICH field is the
            entropy (x/y for EC/OKP, n for RSA, k for oct, and
            keypairs add d), plus JSON canonicalization so key
            order / formatting don't change the fingerprint. Real
            work, deferred — not a parser one-liner.
          * NanoID — 21 chars from the URL-safe alphabet
            [A-Za-z0-9_-], i.e. identical to a 21-char base64url
            string. No prefix, no checksum, configurable length;
            no deterministic marker. Already handled as base64url.
          * z-base-32 — a human-oriented base32 variant
            (alphabet ybndrfg8ejkmcpqxot1uwisza345h769). Two
            problems: (a) no marker — its char set is a subset of
            base58 and base64url, so a disproof entry would have to
            sit BEFORE base58 ("most restrictive first") and would
            then STEAL ordinary base58 inputs; and (b) it uses a
            DIFFERENT char→value mapping than base32/bech32, so a
            mis-detection produces wrong quants (silent corruption),
            not just a wrong label. Strictly worse than leaving
            such inputs as base58/base64url. Deferred.
          * base62 (0-9A-Za-z) — ADDED to the disproof ladder,
            then REVERTED after review. The rationale for adding
            was "most-restrictive-that-fits": base62 is a strict
            subset of base64 (differs only by +/), so it seemed a
            tighter description. The flaw: tightness is not
            correctness. A random base64 string omits both + and /
            with probability (62/64)^N — ~25% at 44 chars
            (256-bit), ~50% at 22 chars (128-bit) — so a base62
            disproof entry would STEAL a quarter-to-half of all
            genuine base64 inputs and relabel them "base62." And
            base62 is rare in the wild while base64 is ubiquitous,
            so for a punctuation-free alphanumeric blob "base64
            that omitted +/" is far likelier than "true base62":
            the label would be wrong more often than right. This is
            the SAME content-sniffing unsoundness that disqualified
            Solana/NanoID — the disproof ladder is sound only where
            fitting alphabet X makes BEING X the likely explanation
            (true for hex/base32/bech32/base58, which are
            distinctive or restrictive enough that an accidental
            fit is unlikely; false for base62). The visualization
            is unaffected (base62 and base64 tokenize identically),
            so it was "safe" only in the narrow sense of never
            corrupting the picture — but a label that is usually
            wrong is not worth adding. Reverted; left to base64.

    User Note Caption = decision:
      id: usrn0te1
      status: drafted
      why: >
        Hex (and a few other broadly-used encodings) carry no
        semantics, and a user often knows something about an
        input that entviz cannot detect ("this is a git commit",
        "prod DB key"). The user wanted a way to caption an
        entviz WITHOUT changing the trust placed in the input.
        This adds an out-of-band, aggressively-sanitized,
        visually-quiet caption — the `--note` flag.

        Rejected first: an IN-BAND prefix syntax (`X?<input>` or
        `(git)<input>` -> label "git? hex(40)" / "(git)hex(40)").
        Two fatal problems:
          * Separator ambiguity / input hijacking. The
            arbitrary-text fallback path accepts EVERY byte, so
            no character (`?`, `(`, `)`) is safe to reserve as a
            delimiter. Real inputs contain them (a passphrase
            `what?up`, a URL query `path?q=1`, `(555)1234567`),
            and reserving them silently fingerprints DIFFERENT
            bytes than the user pasted — a correctness bug and a
            threat-model secondary-win ("render differs by
            encoding form"). Same family as the bech32 `1`
            separator caveat, but worse: the fallback has no
            alphabet to bound what is data vs. delimiter.
          * Overloading the trusted channel. The top type-label
            is a relied-upon output (threat model: "entviz trusts
            the user to read both label strips"); putting
            arbitrary free text there, guarded only by `?`/`()`,
            is a social-engineering surface. The parenthetical
            form is WORSE because entviz's real labels already use
            parens (`hex(40)`, `b64(200)`), so user text would be
            typographically indistinguishable from derived text.

        Why out-of-band defuses the threat (the reframe that makes
        a quiet treatment acceptable): a `--note` is set by
        WHOEVER RUNS entviz, never by the input. In the
        security-relevant flow (Alice receives a value from Bob
        and renders it HERSELF) Bob cannot inject a note — he
        controls the bytes, Alice controls the flag. The only way
        an attacker sets the note is by handing over a
        pre-rendered SVG, but an attacker who controls rendering
        can already draw anything (tier T2); `--note` grants no
        new capability. So a note can only "mislead" the person
        who typed it — annotating one's own artifact, not an
        attack. It also cannot forge a false MATCH: the gestalt
        channels are untouched and a mismatched caption only makes
        two things look MORE different (the safe direction). The
        residual risk is mild false-REASSURANCE, bounded hard by
        sanitization.

        Locked design:
          (a) Out-of-band only. A `--note` CLI flag / `render(...,
              note=)` arg. NEVER part of the input string; NEVER
              enters the core or the fingerprint; OUTSIDE the
              comparison surface — two renders of the same value
              differing only in `--note` are "the same" for
              comparison. (A clean comparison just omits the
              flag.)
          (b) Aggressive sanitization. ASCII alphanumeric only
              (`[A-Za-z0-9]`), a single token (the charset forbids
              spaces), MAX 8 chars. Case is PRESERVED (it is a
              human caption, not entropy, so no normalization).
              Validation is STRICT: an invalid note is an ERROR,
              never silently truncated/mangled (silent mangling of
              a trust-adjacent field is worse than a clear error).
              8 over 10: tighter fit and modestly narrows the
              space of reassuring words.
          (c) Render location: the BOTTOM (suffix) strip — never
              next to the top type-label, keeping untrusted text
              off the channel users rely on. The note is appended
              after any real suffix, separated by a space, wrapped
              in parens: `...<suffix> (<note>)`, or just
              `(<note>)` when there is no suffix. The bottom strip
              now appears when there is a suffix OR a note (it was
              suffix-only before). The suffix strip is already a
              lower-trust, source-controlled context band (it
              carries SSH comments / SWHID qualifiers), so it is a
              natural home for an ancillary caption.
          (d) Visual treatment: the note text is GRAY (#808080) —
              quieter than the #666666 suffix/label text — with NO
              italics and NO new font size (same monospace family
              and label size). The gray is the same value as the
              bounding-rect border, reading as "chrome, not data."
              The user chose gray over a `note:` lead-in or italics.
          (e) Structural marker: the note `<text>` element carries
              a `data-user-note="<note>"` attribute, so downstream
              tooling distinguishes the caption from
              algorithm-derived suffix content regardless of
              styling. The gray fill + this attribute together
              carry the (verified vs. asserted) distinction; the
              residual ambiguity with a real suffix that itself
              ends in parens is accepted as minor given the
              out-of-band reframe.

    Label De-duplication and Default Elision = decision:
      id: lbldedup
      status: drafted
      why: >
        The top label is "<Type>: <prefix>...". Two distinct
        kinds of waste were found and removed; both are
        label-only (no detection / fingerprint / geometry
        change), and shorter labels also help the top strip fit
        on narrow grids.

        (A) Redundancy with the prefix. For most types the prefix
        is OPAQUE (0x, AAAA, E, 1220, Qm) and the Type decodes it
        — complementary, not redundant. But where the stripped
        prefix is itself human-readable and self-describing, a
        Type that re-spells it is pure duplication. Two tiers of
        fix, by how much the Type would echo the prefix:

          Tier 1 — prefix IS the identifier -> NO type at all.
          When the prefix begins with the scheme's own name, even
          a slimmed Type still echoes it, so the Type is dropped
          entirely (parser returns type="") and the label renders
          the self-describing prefix ALONE:
            * gitoid -> "gitoid:blob:sha256:..." (a slimmed "git
              object" was tried first and rejected — still an echo
              of "gitoid").
            * SWHID  -> "swh:1:rev:..." ("SWHID" tried first and
              rejected for the same reason).
          The obj/algo/version stay fully visible in the prefix.
          Rendering: _draw_label_strips, given an empty type_name,
          emits "<prefix>..." with no "<Type>: " segment. This is
          a reusable rule for any future self-describing-prefix
          scheme.

          Tier 2 — Type adds info the prefix lacks -> keep a slim,
          non-redundant Type:
            * Cosmos: "bech32 cosmos" -> "bech32" (the encoding
              family is NOT in the prefix; the chain IS, via
              cosmos1).
            * SSH: "SSH ed25519 pubkey" -> "SSH ed25519" (the
              prefix is OPAQUE base64, so "SSH ed25519" is not an
              echo; only the constant "pubkey" — the degenerate
              certain-default case of (B) — is dropped).
        DID ("DID: did:key:...") was left: the echo is a single
        friendly-acronym, and the method (key) is only in the
        prefix, so the prefix adds information.

        (B) "Silent default, loud departure." A token that is an
        overwhelmingly-assumable default is omitted; only a
        departure from it is shown. Applied where one token is
        near-constant AND the others stay distinct:
          * CID content codec ALWAYS shows (it varies: dag-pb /
            raw / dag-cbor) but the hash shows ONLY when it is
            not sha2-256: "CIDv1 dag-pb", but "CIDv1 dag-pb/
            sha3-256" on departure. CIDv0 is dag-pb/sha2-256 by
            definition, so both elide -> "CIDv0". Also dropped
            "IPFS " and the CID/version space per user preference
            (CIDv0 / CIDv1). The gallery SECTION title keeps
            "IPFS CID" for discoverability; only the entviz
            labels shortened.
          * multihash hash: sha2-256 elided -> "hex multihash";
            shown on departure -> "hex multihash sha3-384".
        decode_multicodec (renamed from decode_multicodec_label)
        now returns a (codec, hash) pair so the caller can apply
        the elision.

        Where (B) must NOT be applied: "decode-the-opaque-code"
        types with no single dominant default — above all CESR.
        Ed25519 keys, secp256k1, Blake3-256 digests, etc. all
        coexist; eliding a "default" would collapse genuinely
        different primitives to a bare "CESR" — the same trap as
        labelling a CID by its (constant) hash instead of its
        (varying) codec, where a dag-pb and a raw CID would read
        identically. The variety IS the information there, so the
        full decode stays. Same protects the blockchain tickers
        and the disproof alphabets. Cardano era (Shelley default
        vs Byron) is a borderline (B) candidate left UN-elided:
        the era is genuinely useful and addr1-vs-Ae2/DdzFF
        already signals it.

    Suffix Binding Rule (bound vs free) = decision:
      id: sufxbind
      status: drafted
      why: >
        The bottom-strip `suffix` is reserved for material that is
        BOUND to the entropy. The test is: can the suffix vary
        while the entropy stays fixed?
          * BOUND (no — locked to the value): a checksum or
            derivation. A different value of it does not parse
            (it would be an invalid checksum), so it is always
            consistent with the entropy, it is short, and it is a
            verifying property of the value. Examples: LEI MOD
            97-10 check digits, Bitcoin/Litecoin/Cardano
            base58check checksums. These are SHOWN.
          * FREE (yes — varies independently): an annotation
            attached to the value but not derived from it. The
            same value carries any such annotation, and it is
            often unbounded. Examples: an SSH public-key comment
            (`alice@host`), SWHID qualifiers
            (`;origin=...;lines=...`). These are DROPPED — matched
            so the input is still recognized via its core, but not
            entered into the core and not surfaced as a suffix.

        This is not a new invention: spec.md step 1 already
        defines suffix as "checksums or derivations of the true
        entropy," so a free annotation never qualified — surfacing
        the SWHID qualifier / SSH comment was an over-broad use of
        the field. Three reasons to DROP free annotations rather
        than truncate them:
          (1) Not part of the value. entviz visualizes the
              entropy; rendering an annotation implies it is part
              of what is being compared, which it is not — two
              identical values with different annotations would
              look "different" in the strip.
          (2) Unbounded -> layout breakage (the SWHID qualifier
              scrolling off the viewport is what surfaced this).
          (3) It is the in-band attacker-text problem that
              [[usrn0te1]] deliberately kept out-of-band: a free
              suffix is exactly un-fingerprinted, attacker-mutable,
              in-band text drawn into the picture. Dropping it also
              CLOSES an SVG-injection vector at the source (the
              hostile text never reaches the renderer) on top of
              the existing lxml escaping.

        Verified: a free suffix never touches the fingerprint
        (core only is hashed), so dropping it changes nothing in
        the comparison surface; two inputs differing only in a
        free annotation render identical visuals (the only delta
        is the informational `data-input-bytes` attribute, which
        reflects the literal raw-input length).

        Scope applied now: SWHID qualifiers and the SSH comment.
        Bound checksums (LEI/Bitcoin/etc.) are unaffected.
        DEFERRED candidate: the DID URL path/query is also a free
        annotation by this test (the same DID identifier carries
        many URLs) and is currently still surfaced as a suffix;
        dropping it is a reasonable extension but was left out of
        scope, and it is the live vector the SVG-injection
        regression now exercises. See also [[lbldedup]].

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

        Blank-Cell Map: Shape Cue + Position Attributes = decision:
          id: v8blnkmp
          why: >
            Two v8 changes to the blank-cell map, from the 2026-06-08 review
            (PSY-F1 + SPEC-F2). Both are comparison-breaking (they change the
            rendered marker and an emitted attribute), so they land together
            under the v7 -> v8 SPEC_VERSION bump.

            (PSY-F1) SHAPE, not just colour, now carries the max/min semantic.
            Through v7 both markers were dots distinguished only by hue
            (red=max #d62828, blue=min #1d4ed8). The blank-cell map is the
            channel a habituated reader checks first, but under achromatopsia
            the two dots collapse to near-equal grays (ΔL* ~ 8), so a reader
            could see THAT two cells are marked but not WHICH is max and which
            is min — a silent loss of the map's meaning for that population.
            v8 keeps the minftok marker a blue DOT (filled circle) and makes
            the maxftok marker a red PLUS (a crossed stroked path: arms
            +/-1.2*marker_radius, stroke-width max(1, 0.55*marker_radius),
            fill none, butt caps). The colours are retained as a redundant
            cue; the shape is the primary discriminator and survives total
            colour blindness. The maintainer chose the plus (over a "v" or
            other glyph) and chose dot=min / plus=max. Because the shapes
            differ, the v6 degenerate-case special marker (blue ring +
            concentric half-size red dot, for min==max on a single used ftok)
            is no longer needed: both markers are drawn at the one centre and
            the red plus over the blue dot stays legible.

            (SPEC-F2) The markers now expose their POSITION directly. v6
            emitted data-blank-map-min/max = "true" (a boolean flag) and the
            reference checker reverse-engineered the (row,col) from the dot's
            cx/cy pixel geometry — fragile, and a checker written faithfully to
            the SVG profile (which names "dot positions") would have found no
            position to read. v8 emits the literal "row,col" of the cell as the
            attribute value (data-blank-map-min on the blue dot,
            data-blank-map-max on the red plus), so a Tier-A checker recovers
            the position from the named attribute without any geometry. This
            also decouples recovery from the marker's element type, which now
            differs (circle vs path) between the two markers. compliance/model.py
            _dot_rowcol was simplified to parse the attribute string. The
            abstract render model is UNCHANGED (still records map_min/map_max as
            [row,col]), so Tier-A goldens did not move; only the SVG/raster
            (Tier B), figures, and gallery regenerated. Tests in
            tests/test_v6_blank_map.py. See also [[v6blnkmp]].

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

        Head/Tail Are Anchors, Not A Representative Sample = decision:
          id: v6htscal
          why: >
            The maintainer questioned whether the >512-bit allocation
            (H=8 head, M=4 fingerprint-middle, T=8 tail) under-serves the
            MIDDLE of a truly massive input (e.g. a 40GB genome): showing
            the first/last 192 bits literally while giving the hash only 4
            cells "feels like it over-emphasizes the input and under-
            emphasizes the hash."

            Analysis (no behavior change warranted): the worry conflates
            two separable things — BINDING vs text-channel REAL ESTATE —
            which have opposite answers.

            BINDING: the input's middle is the BEST-protected part, not the
            worst. The primary fingerprint is SHA-512 over the WHOLE input
            and drives the surround on all 20 cells, the color bar, the
            ellipse, the blanks, the quartiles, and the bg color. The 4
            middle text cells are a 96-bit injective readout of a SECOND,
            domain-separated digest ([[v6fpmid2]]) that avalanches on any
            input change even in a TEXT-ONLY / read-aloud comparison (the
            one scenario gestalt can't help). So the bulk is bound into
            every high-bandwidth channel; head/tail get exactly ONE channel
            (literal text) to themselves. 4 cells is plenty for binding —
            more middle cells would only raise the read-aloud preimage bound
            above 96 bits, which is already far past any human-effort
            threshold, and would NOT improve gestalt binding at all.

            REAL ESTATE (the legitimate part of the worry): the 80/20
            literal:hash split in the TEXT channel is tuned for inputs
            barely over 512 bits, where head/tail recognition is plausible.
            It scales poorly to truly massive inputs: recognition value of
            384 literal bits -> ~0 (nobody eyeballs 192 bits of genome; file
            ends are often headers/padding), and the represented fraction ->
            ~0 (48 bytes of 40GB), yet the literal cells keep 80% of the text
            real estate.

            Decision: do NOT make the H/T/M split size-adaptive. A sliding
            allocation trades away "trivial to implement correctly"
            ([[z3rodeps]]) and the fixed 20-token / 4x6-grid invariant for no
            security gain. Fix the optics in PROSE instead: state plainly in
            the spec that head/tail are a VERIFICATION CONVENIENCE (spot-check
            the ends vs a known-good copy), NOT a representative sample, and
            that the larger the input the more the fingerprint-driven
            channels carry essentially all the comparison signal. Added a
            "Head/tail are anchors, not a representative sample" scale-caveat
            paragraph to the large-input handling subsection, and a clause to
            the `fingerprint of` reading-user guidance (point 2). A threshold
            rebalance (e.g. H=6/T=6/M=8 above some large size) was considered
            and deferred as cosmetic-only — record here in case a future
            revision wants it. See [[v6fpmid1]], [[v6fpmid2]], [[v6blnkun]].

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

    Supply-Chain Hardening = decision:
      id: s3cch41n
      why: >
        Defend the project's build/CI integrity against the dominant 2026
        supply-chain attack classes, without adding runtime dependencies (so
        [[z3rodeps]] still holds — the shipped library is untouched).

        (1) Invisible-Unicode / Trojan-Source gate: scripts/check_unicode.py
        rejects only the dangerous code-point categories (bidi controls,
        directional marks, zero-width/invisible, variation selectors, tag
        chars, Private Use Areas) while allowing legitimate non-ASCII the
        project uses on purpose (Greek Δ in formulae, em-dashes, box-drawing,
        CJK, emoji). A naive ASCII-only rule would have failed honest prose.
        Wired as its own CI job (unicode-guard) and covered by
        tests/test_check_unicode.py. The pre-flight scan caught two accidental
        characters in authored prose — a stray U+200B in the paper's Weber's-Law
        formula and a U+FE0F emoji presentation selector in a review doc — both
        removed (they rendered identically without them), so the gate is clean
        on the tree with no exclusion holes.

        (2) GitHub Actions pinned to full commit SHAs (was mutable @vN tags),
        with least-privilege top-level permissions and persist-credentials:false
        on checkout, so a retargeted tag (tj-actions class) can't inject code.
        Dependabot keeps the SHAs current and grouped.

        (3) PATH/binary-hijack (Task 3) does NOT apply: the shipped library
        spawns no external binaries. The only subprocess use is the dev-only
        scripts/release.py (git/uv), run interactively by the maintainer on a
        trusted machine — out of the runtime threat model.

    Bounded Input / Anti-DoS = decision:
      id: 1nputcap
      why: >
        Close the threat-model "super-linear resource consumption" secondary
        win (docs/threat-model.md). Two independent costs scaled with raw input
        size, both unnecessary:

        (1) Wasted full tokenize. tokenize_entropy() materialized EVERY token
        of the whole core (a 10 MB hex input → ~1.7M Token objects, ~14.5s;
        50 MB → ~48s) only to read len(all_tokens) for a branch decision and
        then discard all but the head/tail on the large-input path. But
        tokenize() emits exactly ceil(len(core)/token_len) tokens, so the
        count — and the byte length ([[_core_byte_length]]) — are both O(1)
        from len(core). Fix: derive the >512-bit / >22-token branch
        arithmetically and only call the full tokenize() on the short path
        (which is ≤22 tokens by definition); the large path tokenizes just the
        head and tail windows it actually renders. Output is byte-identical —
        test_large_input.py is the regression guard, and an explicit
        equivalence test pins it.

        (2) Unbounded input. Even with (1) fixed, render() still hashes and
        allocates O(n) over attacker-controlled bulk (the full-core SHA-512
        that binds the fingerprint, the .strip()/.encode() copies, the
        txt->b64url fallback's base64 of the whole input). entviz visualizes
        IDENTIFIERS; the largest plausible one (a long cert chain or JWT) is a
        few KB. MAX_INPUT_CHARS = 65536 (64 KiB) is ~16× headroom over that yet
        bounds the residual work to a few milliseconds even worst-case (a 64 KiB
        input of 4-byte codepoints expands ~4× through the txt->b64url fallback
        before the full-core SHA-512; measured ~14 ms). Past the cap the input is
        not an identifier, so render() raises ValueError outright rather than spend
        unbounded CPU/memory — same "reject, don't silently mangle" stance as
        [[usrn0te1]]'s note validation. The cap is checked at the render()
        boundary before parse()/tokenize so no O(n) work precedes it.

        Relation to [[s3cch41n]]: that node hardens the BUILD/CI surface; this
        hardens the RUNTIME render() surface. Both serve the same threat model.

    Algorithm Bug-Hunt Review = decision:
      id: alg0rvw1
      why: >
        Record (2026-06-05): the algorithm changes from the adversarial-review
        batch (commit a3a0a3a — the [[1nputcap]] tokenize optimization + input
        cap, the parser-dispatch globals()->explicit-list refactor, and the
        render() nested-helper extraction) were put through a dedicated
        bug-hunting code review at high effort, scoped to the diff
        `git diff 0b873e5..a3a0a3a -- src/entviz/entropy.py src/entviz/pipeline.py`.
        Method: a multi-angle pass (line-by-line, removed-behavior-auditor,
        cross-file tracer) plus two independent reviewers.

        Result: CLEAN — no correctness bugs. The verdict is evidence-backed,
        not asserted: the O(1) token-count substitution
        (token_count = -(-len(core)//token_len)) was brute-forced equal to the
        old len(tokenize(core)) across every alphabet × lengths 0–199 plus the
        bech32 92-char/23-token corner case (0 mismatches); the lifted helpers
        pass every formerly-captured variable; the explicit parse_funcs list is
        complete and order-preserving (now pinned by a test); and the
        output-preserving claims are corroborated by the byte-identical gallery
        regeneration. The only follow-up was correcting this batch's
        residual-cost wording in [[1nputcap]] ("microseconds" -> a few ms).

    Conformance Formalization = decision:
      id: c0nf0rm1
      why: >
        Record (2026-06-06): the v6 spec was given a rigorous, RFC-2119
        conformance pass so that independent implementers (a Rust and a
        TypeScript port are planned) can produce provably compliant renderers.
        The pass is EDITORIAL and output-neutral: no algorithm, constant, or
        rendered pixel changed, SPEC_VERSION stays v6, and the gallery + figure
        SVGs remain byte-identical (verified by the figure drift guard + gallery
        regen).

        Two substantive additions to docs/spec.md: (1) a "Notation and
        requirements language" section adopting RFC 2119/8174, with load-bearing
        instructions re-voiced to MUST/SHOULD and rationale explicitly marked
        non-normative (readability retained, normative core now extractable);
        and (2) a normative "Conformance" section defining the abstract RENDER
        MODEL an implementation must compute, a three-tier conformance model,
        the EQUIVALENCE RELATION a checker uses, the SVG profile (required
        data-* attributes + normative paint order), and the error-condition
        catalog.

        Key design choice — three conformance tiers, because the semantic model
        alone is insufficient. Tier A (render model from the emitted data-*
        attributes) proves the algorithm COMPUTED the right values and localizes
        failures, but cannot prove what a human SEES: two SVGs with identical
        render models can still paint in the wrong z-order or place. Tier B
        rasterizes via one fixed reference rasterizer and pixel-compares — the
        visual authority for layering/color/position/size/occlusion — excluding
        text-glyph regions, since cross-platform glyph equality is explicitly a
        non-goal (the font-fallback clause) and text is instead proven through
        Tier A. Tier C is an optional non-blocking headless-browser smoke. This
        decision drives the compliance suite (Phase 2) and the corpus published
        as a release asset that each implementation certifies against. Tracked
        in the tick ledger (Phase tickets); relates to [[s3cch41n]] (build
        surface) and the threat-model channels [[usrn0te1]]/[[3ip55rj1]] whose
        rejects are now in the normative error catalog.

    Compliance Suite = decision:
      id: c0mpsu1t
      why: >
        Record (2026-06-06): Phase 2 landed the conformance suite under
        compliance/ (Tier A render-model extractor from data-* attrs +
        normative geometry; Tier B canonical raster via cairosvg with text
        stripped; corpus generator + language-agnostic runner; 44 render + 6
        error + 3 invariant vectors). The reference self-certifies 53/53. Wired
        into pytest with a corpus drift guard mirroring the figure guard
        (tests/test_compliance.py). Implements the [[c0nf0rm1]] design.

        Two follow-ons the suite forced out (both correct, both small):
        (1) render() now validates font_size_pt in [6,30] and target_ar in
        [0.01,100] at the LIBRARY boundary, not only in the CLI (app.py), so the
        spec's error catalog is true of the importable API and a Rust/TS port
        has a self-validating render() contract. Output-neutral: only
        already-invalid params are rejected; no valid SVG changes.
        (2) Fixed a spec self-contradiction the corpus surfaced (a 128-bit UUID
        has an ellipse): the Guarantees section claimed inputs <256 bits omit
        the ellipse, but the algorithm step + impl always draw it. The
        Guarantees prose was corrected to match (resolves tick 5s5a). The
        canonical reference rasterizer is pinned per-corpus in manifest.json
        (cairosvg now; resvg is the intended longer-term authority for closer
        browser fidelity — the rasterizer is pluggable).

    Multi-Language Implementations = decision:
      id: mult1mpl
      why: >
        Record (2026-06-06): Phases 3-5 of the [[entviz-multiimpl-plan]] — the
        Rust + TypeScript + React implementations — live in SEPARATE repos
        (~/code/entviz-rs, ~/code/entviz-js), not this one, for idiomatic
        cargo/npm publishing; they certify against the corpus this repo
        publishes (consumed locally for now).

        entviz-js (TypeScript, Node native type-stripping, zero deps beyond
        node:crypto) ports the full SHORT-INPUT shared algorithm and is
        CERTIFIED 24/24 supported corpus vectors at Tier A (render model) AND
        Tier B (canonical raster) via the real compliance runner. This proves
        the cross-language pipeline end to end: an independent impl yields
        identical render models and pixel-identical (non-text) rasters. Parsers
        ported: hex, UUID, utf8->base64url fallback (+ note/font-size error
        handling); the blockchain/CESR/SSH/etc parsers and the >512-bit branch
        are mechanical follow-ons. A thin @entviz/react <Entviz/> wraps the
        certified core. Two cross-language gotchas the corpus caught and pinned:
        Python round() is banker's rounding (round-half-EVEN) — JS Math.round
        and naive ports round half UP, which broke the 6pt cell-text size until
        a roundHalfEven() was added; and the white bounding-rect fill is a real
        painted element (not a cairosvg default), so omitting it failed Tier B
        across the margins.

        entviz-rs (Rust) is BLOCKED: this host has no rustc/cargo. It is
        scaffolded with the deterministic shared core ported (mirroring the
        certified TS) + cargo unit tests, but UNVERIFIED (uncompiled). Needs
        rustup to build/test and to port the renderer + certify. Tracked by
        tick 77ua / 3t6v.

    Discrete-vs-Analog Verification Bits = decision:
      id: d1scr3t3
      why: >
        Record (2026-06-17): the load-bearing principle behind the v9
        comparison-channel work, surfaced while brainstorming a recommended
        comparison algorithm (the Comparison Procedures spec section is the
        next design target; not yet locked). PRINCIPLE: reliable,
        attacker-resistant human verification bits come only from DISCRETE-
        symbol decoding (reading a character, naming a color letter, checking
        whether a marker sits in the same slot/cell). ANALOG visual variables —
        colour shade, size, aspect ratio, position-on-a-continuum, organic
        shape — contribute RECOGNITION and DIFFERENCE-DETECTION but not hard
        bits: they are read with perceptual tolerance, which both caps reliable
        bits at the JND and hands a near-collision attacker (T1+T6) a tolerance
        band to hide in.

        Consequences that decided several design questions: (1) text "dominates"
        the adversarial bit budget not because it is text but because it is the
        most familiar zero-tolerance discrete channel — so the way to make
        comparison LESS text-centric is to enrich the OTHER discrete channels
        (blank-map cell positions, colour-bar letter order, quartile positions,
        the new bar markers), NOT to add analog flourish. (2) A drunken-bishop
        walk was REJECTED: it is a holistic/analog generator, and entviz is
        already a saturated holistic-gestalt object, so it would add a
        correlated impression + visual mess, not the scarce discrete bits.
        (3) A "fat vs thin" colour-bar encoding was REJECTED: aspect ratio is
        among the least reliably-read visual variables and is continuous
        (gameable). (4) The blank map is the best non-text channel precisely
        because it is DISCRETE (positions), not analog. Two comparison MODES
        follow: a casual mode (gestalt-first; avalanche lights up every channel
        on any honest single-char error, so a glance suffices) and an
        adversarial mode (discrete-symbol-backed; the randomized/seeded walk
        forces unpredictable coverage so a T1+T6 attacker cannot pre-match the
        check-set). Drives [[cr0ckmid]] and [[b4rm4rks]].

    Crockford Middle Cells = decision:
      id: cr0ckmid
      why: >
        Record (2026-06-17): v9 (pending implementation). For >512-bit inputs
        the 4 middle ("fingerprint") cells render the second, domain-separated
        digest as 5 LOWERCASE CROCKFORD base32 characters per cell, replacing
        v6's 6 lowercase hex. Motivation: reading effort scales with character
        count AND syllables, and the middle cells are the read-aloud bottleneck
        on a base64-alphabet input (4-char head/tail tokens flanking 6-char hex
        middles). Breaking change accepted — nobody is using entviz yet.

        Crockford-5 is the PROVABLE OPTIMUM of {fewest chars that is injective
        on 24 bits, single-case, homoglyph-clean}: 4 chars would need a >=64-
        symbol (6-bit) alphabet, forcing mixed case or -/_ (which re-imports the
        "cap" read-aloud syllable AND homoglyph cost — so base64url is a wash on
        syllables and worse on safety/signal); no single-case homoglyph-clean
        alphabet reaches 64 symbols (digits + one letter case = 36 max). 5 chars
        over a 32-symbol disambiguated alphabet is therefore the floor.
        32^5 = 2^25 >= 2^24, so the encoding is injective (24-bit big-endian
        value, high-order zero-padded; the leading char never exceeds symbol
        value 15 — harmless). Crockford excludes i/l/o/u, so it kills the 0/o,
        1/l, 1/i confusions — strictly safer than hex. base58 was REJECTED
        outright: 58^4 = 11,316,496 < 2^24, so 4 base58 chars cannot injectively
        carry 24 bits and a 4-char rendering re-opens exactly the F1 mod-fallback
        aliasing this construction was created to kill.

        Font: NO rule change needed. The existing per-cell size rule
        round(ref x max(0.75, min(1.0, 4/token_chars))) yields 5-char -> 0.80x
        (10pt at the 12pt reference) automatically, vs hex's clamped-to-floor
        0.75x (9pt) — bigger and roomier (~9.6px horizontal slack vs ~4.8px).
        Full size is impossible: 5 glyphs overflow the ~4-glyph nucleus, which
        is the same wall that forced hex to 0.75x.

        Signal preserved and improved: the "this is a digest, not your data" cue
        rested partly on hex looking unlike the input alphabet. On a HEX input
        that cue was weakest (all-hex; only the neutral bg + gold/white frame
        distinguished the middle). With crockford the head/tail (6-char hex) and
        middle (5-char crockford) now differ by alphabet AND size even on a hex
        input — the F1 "hex signals digest" rationale is reworded, not lost.
        Reuses the existing second digest + DOMAIN_TAG (no new hash). Relates to
        the Large-input handling subsection, the cell-text rendered-size rule,
        and [[d1scr3t3]].

    Color-Bar Decouple + Discrete Markers = decision:
      id: b4rm4rks
      why: >
        Record (2026-06-17): v9 (pending implementation). Three coordinated
        colour-bar changes that add DISCRETE (hard) bits to a non-text channel
        per [[d1scr3t3]].

        (a) ORDER-DECOUPLE. The bands' vertical order is now set by each 2-bit
        pattern's FIRST-APPEARANCE order while scanning the primary SHA-512
        digest's 256 disjoint 2-bit slices (tie-break by pattern value,
        00<01<10<11), INDEPENDENT of band heights (still count^4 of the primary
        histogram). Today order == argsort(heights), so it carries ~0 extra
        bits; decoupling adds ~3 reliable discrete bits (read the letters top to
        bottom) at zero extra glance and zero CVD cost. It does not hurt the
        COMPARISON task — sorted-vs-unsorted only matters for reading a trend in
        isolation, not for "do these two bars match". data-color-bar-rank now
        reflects the independent order.

        (b) TWO FIXED-SLOT MARKERS. The bar's drawing height is divided into
        K = clamp(floor(bar_height / 12px), 4, 16) EQUAL FIXED slots, independent
        of band sizes/order. A small FILLED CIRCLE rides each gutter: LEFT at slot
        second[12] mod K, RIGHT at second[13] mod K. Source = the second,
        domain-separated digest (reused DOMAIN_TAG), bytes disjoint from the
        middle cells' second[0..11]. `second` is now computed for EVERY input
        (one extra SHA-512), so SHORT inputs gain this channel too. bar_width is
        UNCHANGED (markers live in ~4px gutters inside the existing 20px bar — no
        geometry blast radius). Left/right placement means the two markers can
        NEVER overlap regardless of slot, and SIDE alone tells them apart — so
        there is no coincident-slot rule.

        CIRCLES, not distinct shapes (revised after gallery review): the first
        cut used a SQUARE (left) + EQUILATERAL TRIANGLE (right), but shape
        discrimination proved untenable at the bar's scale — on a dark band
        (blue/red/black) the black halo vanishes and only a too-small inner
        glyph reads, so the shape was not perceived consistently. Since the
        left/right gutters already distinguish the two markers, the shape
        distinction was redundant as well as fragile; both are now circles.

        Markers are drawn as OPAQUE TWO-TONE: white fill + ~0.75px black
        outline — NOT mix-blend-mode / difference compositing. This delivers the
        "visible against anything, including a marker that straddles a band
        boundary" goal PORTABLY: pure lightness contrast (CVD/grayscale-safe),
        bit-identical across rasterizers. mix-blend-mode or an invert filter
        would re-open adversarial finding F-A6 (the v5 marker was invisible
        outside browsers; the blank map deliberately avoids blend modes for
        exactly this) and break Tier-B (the non-browser reference rasterizer).
        A statically-computed colour inverse does NOT solve the band-spanning
        case (two backdrops, one inverse); the halo does — the white core shows
        on the dark side of the cut, the black halo on the light side.

        (c) WHY IT MATTERS. The markers are discrete (slot positions),
        INDEPENDENT (second digest is domain-separated from the primary, so the
        bits add cleanly to the joint near-collision grind cost — the F2 logic),
        CVD-safe (side + lightness halo), and — decisively — ALWAYS
        PRESENT. This closes the coverage hole where the blank map (our other
        best discrete channel) vanishes ENTIRELY on an exactly-filled grid
        (token_count == cell_count -> no blank cell -> no map). Honest framing:
        still a tripwire-tier contributor (2 markers x ~3 bits ~= 6 independent
        hard bits), NOT the security backbone (cell-text reads are).

        (d) CONFORMANCE. The render model's `color bar` field gains the two
        marker slots; the SVG carries data-bar-marker-left /
        data-bar-marker-right (slot index) and data-bar-slots (K) so a Tier-A
        checker recovers them without pixel geometry, and data-color-bar-rank
        reflects the decoupled order. Relates to [[cr0ckmid]], [[d1scr3t3]], the
        colour-bar + blank-cell-map steps, and the multi-impl corpus/ports
        ([[entviz-multiimpl-plan]] — Rust/TS/React + golden corpus regen).

    DID method handling (v11) = decision:
      id: d1dm3th0
      status: drafted
      why: >
        2026-06-23. Added broad W3C DID support. The pre-v11 parse_did was
        wrong four ways: (1) its regex forbade `:` in the body, so
        multi-segment DIDs (did:web:a:b, did:webvh:<scid>:domain,
        did:ethr:0x89:0x…) and any `#fragment` fell through to the UTF-8
        fallback; (2) it stripped the method as a NON-semantic prefix, so the
        method never bound the fingerprint and did:web:X == did:key:X in every
        channel; (3) it surfaced the DID URL as a `suffix` (displayed) instead
        of dropping it; (4) it forced base64url on every body regardless.

        The fix is ONE generic path, justified by [[h4shtext]] (hash TEXT, not
        bytes) + [[s3mpr3fx]] (prefix-fold for identity material in a different
        alphabet from the body):
          * Body ends at the first /,?,# (W3C DID Core ABNF allows `:` inside
            method-specific-id). The DID URL tail is a FREE annotation -> DROP
            (same as [[sufxbind]] SWHID `;…` qualifiers). This also disposes of
            ION's `?-ion-initial-state=` long-form for free.
          * Method name is IDENTITY (swap test: same body, different method =
            different DID). Bind by PREFIX-FOLD: prefix=`did:<method>:`,
            hash input = prefix ‖ core. Exactly the SWHID/gitoid mechanism.
          * Core = method-specific-id VERBATIM (multibase selector, network id,
            separators, self-cert hash all kept) — bound because we hash text.
            NOT percent-decoded (no parser ahead of the hash).
          * Case PRESERVED (DIDs are case-sensitive per DID Core; most bodies
            are case-sensitive base58btc/base64url). Diverges from the
            per-alphabet [[c4s3norm]] rule ON PURPOSE; fail-safe (case diff ->
            false negative only).
          * Label: no-type, prefix self-describing -> `did:<method>:...`
            (the SWHID/gitoid no-type rule).

        KEY INSIGHT that collapsed the planned "hybrid w/ big special-case
        table" down to generic-only: in this spec EVERY non-hex alphabet
        tokenizes at the SAME 4-char/24-bit boundary (base58/base64url/bech32/
        base32/crockford32/base36 all = 4; only hex & decimal = 6). So
        declaring base58 vs base64url for a DID body changes ONLY the
        nucleus-COLOUR hint channel — never token boundaries, the fingerprint,
        or read-aloud text. Combined with verbatim-core binding, the generic
        path is already fully identity-correct for did:key/peer/webvh/keri/
        btcr/etc. base64url is chosen as the uniform DID alphabet (superset of
        the base58/base64url bodies; out-of-alphabet chars like . : % -> zero
        quant, cosmetic only); it also dodges the disproof case-folding hazard
        (disproof tries case-insensitive hex/base32/bech32 first and would
        UPPER-case a case-sensitive base58 body, corrupting the fingerprint).

        DELIBERATELY DEFERRED (additive, non-breaking, each touches one named
        method — NOT in v11):
          (a) EIP-55 reject for did:ethr/did:erc725. Declined: conflicts with
              the clean case-preservation rule, and is fail-safe without it (a
              corrupted mixed-case address just renders differently). Reuses
              [[3ip55rj1]] if added.
          (b) Drop the long-form initial-state of did:ion/did:prism as a free
              annotation. Declined: the `?-ion-initial-state=` form is already
              dropped by the DID-URL rule; the `:`-suffix form needs per-method
              structure NOT yet validated — naive "keep first `:`-segment"
              BREAKS on `did:ion:test:Ei…` (the network `test` precedes the
              SAID, so first-segment would keep `test` and drop the SAID).
              Until validated, ion/prism long-forms ride generic: the
              `:`-suffix stays in the core verbatim and, if >512 bits, the
              existing head/middle/tail large-input path handles it (correct,
              just visualizes more). Held-back examples flagged for checksum/
              structure validation before they enter the corpus.

        Did NOT special-case did:peer (Daniel co-authored it): generic base58
        path is already identity-LOSSLESS — the `.` separators + V/E/S purpose
        codes + base64url service blocks all stay verbatim in the cells (read-
        aloud faithful) and bind the fingerprint. Special-casing would add only
        a richer label + `.`-segment cell alignment (cosmetic), not worth the
        per-method tokenizer cost across 5 impls.

        URNs (RFC 8141) folded into v11 too — they are the same shape as DIDs
        (urn:<NID>:<NSS> ~ did:<method>:<msid>; DIDs were designed in the URN
        tradition), so they ride the SAME generic path: NID is identity ->
        prefix-fold `urn:<nid>:`, NSS is the verbatim base64url core, and the
        r-/q-/f-components (?+ / ?= / #) are a free annotation -> DROP (RFC 8141
        states outright they are NOT part of URN equivalence). Two differences
        from DID: (1) `/` is a legal NSS char and part of identity, and the
        components start only at `?` or `#`, so the NSS terminates at the first
        ? or # (NOT /). (2) Per RFC 8141 the urn scheme + NID are
        case-INSENSITIVE while the NSS is case-sensitive, so we LOWERCASE the
        `urn:<nid>:` prefix (URN:ISBN: == urn:isbn:) but PRESERVE NSS case — the
        one place URN diverges from DID's preserve-all-case rule. Not
        per-namespace special-cased (urn:uuid/oid/isbn all ride generic). Daniel
        asked for this and chose the RFC-correct prefix-lowercasing.

        Blast radius: docs/spec.md (v10->v11, new *Decentralized Identifiers* +
        *Uniform Resource Names* subsections, tokenization-list pointer),
        spec-change-log.md (v11 entry),
        the python reference parse_did rewrite + tests, NEW DID corpus vectors +
        golden regen, then the 4 sister-repo ports (js/rs/java/go) reproduce
        Tier A — tracked as tick 5yau. Relates to [[s3mpr3fx]], [[h4shtext]],
        [[sufxbind]], [[c4s3norm]], [[3ip55rj1]], [[lbldedup]],
        [[entviz-multiimpl-plan]].
