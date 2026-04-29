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
