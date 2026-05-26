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
      status: in-progress
      why: >
        Move the implementation from spec v2 (docs/index.md) to spec v3
        (docs/index_v3_draft.md, to become docs/index.md when promoted).
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
