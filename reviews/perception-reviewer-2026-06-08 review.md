# Perception & Psychophysics Review: entviz

**Date:** 2026-06-08
**Effort level:** deep
**Output examined:** CVD simulations run programmatically (Machado 2009 matrices) on all palette colors, blank-cell map dots, and the fingerprint-of marker; entropy-budget analysis across all channels; palette lightness test suite run; two near-identical input pairs rendered and ellipse parameters compared; color-bar letter legibility analysis; font-chain homoglyph analysis.
**Implementation commit:** 4c36b8878f4063eccd76c9ccb0e7678546f53292

---

## Evidence Inventory

**Read:** `docs/spec.md` (full v7); `this.i`; `src/entviz/colors.py`; `src/entviz/renderer.py`; `src/entviz/pipeline.py`; `reviews/palette-optimization-findings.md`; `reviews/ellipse-audit-2026-06-02.md`; prior adversarial reviews (2026-05-27 and 2026-06-02); `tests/test_v6_palette_lightness.py`.

**Simulations run:**
- Full palette CVD simulation via Machado 2009 severity-1.0 matrices (protanopia, deuteranopia, tritanopia) and luminance-only achromatopsia; CIELAB ΔE76 and ΔL* for all 10 pairwise combinations under each condition.
- Blank-cell map dot colors (#d62828 red, #1d4ed8 blue) under all four CVD conditions.
- Fingerprint-of marker (#a00000) vs. label gray (#666666) under protanopia and deuteranopia.
- Color-bar letter legibility: minimum band height analysis for 12pt reference font.
- Ellipse parameter rendering: two inputs (64 hex As vs. 63 As + B) compared on rx, ry, rotation.
- Color-bar band order distribution over 1000 randomly-drawn hex inputs.
- Oral readout font-chain homoglyph analysis.
- Surround-box merge analysis at 6pt, 8pt, 10pt, 12pt, 16pt.
- Blank-cell map dot angular size and JND analysis.

**New renderings:** Two SVGs rendered to confirm avalanche behavior on single-character change (large Δrx=14.2, Δrot=48° — avalanche confirmed working well).

**Skipped:** Gallery HTML visual inspection (gallery.html lives in repo but was not rendered to browser); paper figures in `docs/assets/paper/` were not individually viewed, as the simulation data above provides equivalent evidence. No browser screenshots were taken.

**Prior finding status checked:** adversarial-2026-06-02 F3 (per-cell edge-color CVD) → partially addressed by `test_v6_palette_lightness.py` (added after that review); the test now pins known sub-floor pairs including deutan gold/red ΔL*≈17.2.

---

## Perceptual Entropy Budget

All estimates are for a typical 3×4 entviz at 12pt/96dpi. "Gestalt" = fast comparison without reading; "Deliberate" = full careful comparison.

| Channel | Nominal bits | Normal/16M (gestalt) | CVD (protan/deutan) | CVD (achromat/grayscale) | Small display / low-vision |
|---|---|---|---|---|---|
| Text (≤512-bit) | Up to 512 | 6–8 gestalt; full deliberate | ≈ same (no color) | ≈ same | Degrades when font falls below ~6pt |
| Surround (24 boxes/cell, 12 cells) | 288 | 5–8/cell × 12 ≈ 60–96 | ~40–60 (edge-color palette collapses to 2–3 perceived colors) | ~30–40 (lightness-only, 5 levels) | Boxes merge at <3px width; drops to ~4 bits/cell density |
| Color bar (histogram, count^4) | ~8–10 | 5–7 (band order + relative heights) | 4–6 (letters compensate for color loss) | 4–5 (lightness bands + letters) | Legible to ~6pt; letters always fit at typical band heights |
| Ellipse (anchor × rx × ry × rot) | ~15 (16^3 × anchors) | 8–10 (each step above JND for side-by-side) | ≈ same (shape-based) | ≈ same | Rx steps 3.5–8px depending on grid; marginal at extreme small sizes |
| Blank-cell map (dot positions) | ~7 (2 × log2(12)) | 5–7 | 5–7 (hue survives protan/deutan) | 2–3 (gray dots, positional only; semantic distinction lost) | Dots are 10.6 arcmin — visible but small |
| Quartile marks (4 corners) | ~13 | 4–6 | ≈ same (B&W marks) | ≈ same | Orientation marginal at 6pt |
| Entviz background (2 bits) | 2 | 2 | 1–2 (some pairs collapse) | 1–2 | 2 |
| Nucleus color (RGB from quant) | 24/cell | 5–8 total (rough hue regions) | ~1–3 (hue-axis collapse) | 0–1 (sub-JND hint) | 0 (all merge) |
| **SUM (gestalt, channels union)** | — | ~35–48 | ~20–30 | ~15–20 | ~10–15 (small) |

The multi-channel union exceeds the randomart ~20–24 bit benchmark comfortably under normal vision. Under protanopia/deuteranopia the estimated gestalt budget (~20–30 bits) still clears the benchmark given that the color-bar letters and shape-based channels survive. Under achromatopsia the budget (~15–20 bits) is at or near the benchmark, with the critical channels being the ellipse shape, surround density patterns, blank-cell positions, and quartile-mark orientations. Under achromatopsia the design is functioning at the edge of the benchmark claim.

---

## Executive Summary

entviz's multi-channel design delivers strong perceptual discrimination under normal vision and degrades gracefully through most color-vision-deficiency conditions. The fingerprint-driven avalanche (Δrx=14.2, Δrot=48° on a single-character change) works as intended. The seven findings below are not implementation bugs but design gaps at the boundary of what the spec promises and what the design delivers under extreme conditions. The most important issue is that the blank-cell map dots are **semantically indistinguishable under achromatopsia** (both become gray; the user cannot tell which dot is max vs. min without color), and this affects the channel a habituated user is most likely to check first. The second priority is that the **spec's palette honesty caveat names only the protanopia red/blue collapse**, leaving the deuteranopia gold/red collapse (ΔL*≈17, confirmed by the test suite) and the tritanopia red/blue collapse (ΔL*≈15.7) undocumented in the authoritative text — an implementor doing their own CVD analysis will not learn these from the spec. Both issues are fixable with small effort and no algorithm changes.

---

## Top Findings

Ordered by bang-for-buck: (realistic collision risk under supported populations) × (how silent the failure) / (fix effort).

---

### F1: Blank-cell map dots are semantically indistinguishable under achromatopsia; marginal under tritanopia

- **Population:** GRAYSCALE/LOW-COLOR; tritanopia (CVD)
- **Severity:** HIGH
- **Confidence:** CONFIRMED (computational CVD simulation, Machado 2009)
- **Location:** `src/entviz/pipeline.py:535–542`; `docs/spec.md §blank-cell map` (red #d62828, blue #1d4ed8)
- **Finding:** Under achromatopsia, red dot #d62828 becomes mid-gray L*=46.9 and blue dot #1d4ed8 becomes slightly darker gray L*=39.1. ΔL*=7.8 means both dots are individually *visible* (10.6 arcmin angular size at 60cm — well above detection threshold), but neither color survives: the user sees two gray dots and cannot determine which is maxftok (red=max) and which is minftok (blue=min) without knowing the convention by memory. The semantic layer of the map — "the redder dot marks the brightest cell; the bluer dot marks the darkest cell" — is entirely carried by hue, and hue vanishes under achromatopsia. A user doing a map-first comparison can confirm *positions* but not *identities*, reducing the check from a two-dimensional CRC to a one-dimensional "are both gray dots in the same spots?" Under tritanopia, ΔL*=4.3 with a pinkish-red vs. teal hue distinction — still distinguishable but the pair is the weakest CVD scenario for the dots.
- **Evidence:** Machado 2009 simulation: red → (111,111,111) L*=46.9, blue → (92,92,92) L*=39.1 under achromatopsia. For comparison: normal-vision ΔL*=7.9, which is itself relatively low for a 10.6arcmin target (JND for small stimuli is elevated vs. large patches). The spec claims protan/deutan coverage for the map dots and does not claim achromat/tritan coverage; still, achromatopsia is a "256-gray" rendering condition which falls under the spec's CVD requirement.
- **Recommended action:** Add a shape distinction between the two dot types so orientation, not just color, carries the semantic. Simplest fix: render the maxftok dot as a filled circle (current behavior) and the minftok dot as a hollow ring of the same radius (stroke only, no fill). This mirrors the current degenerate-case rendering (ring + concentric dot, `pipeline.py:523–532`) and would survive achromatopsia with lightness + shape carrying the distinction. Alternatively, spec documents the achromat limitation explicitly as an accepted risk and adds a note that the CRC is positional-only under achromatopsia.
- **Fix effort:** small (ring vs. filled is a one-line change to the render call; spec update is a paragraph)

---

### F2: Spec palette honesty caveat names only protanopia red/blue; the deuteranopia gold/red and tritanopia red/blue sub-floor pairs are pinned in the test suite but absent from the spec

- **Population:** CVD (deuteranopia, tritanopia)
- **Severity:** HIGH
- **Confidence:** CONFIRMED (Machado 2009 simulation; also confirmed by `tests/test_v6_palette_lightness.py:CVD_EXCEPTIONS`)
- **Location:** `docs/spec.md §palette-rationale` ("Honesty caveat:" paragraph); `tests/test_v6_palette_lightness.py:CVD_EXCEPTIONS`
- **Finding:** The spec's honesty caveat reads: "under *protanopia* the red and blue swatches collapse to ΔL\* ≈ 7 regardless of palette choice." This is accurate as far as it goes, but the test file pins two more exceptions that the spec does not mention: (a) **deuteranopia gold/red ΔL*≈17.2** — both palette entries shift into similar yellow-olive tones under the Machado deutan simulation (#caca4a for gold, #9a9715 for red); ΔE76 drops to 18.6. (b) **tritanopia red/blue ΔL*≈15.7** — the blue-yellow axis, which the spec relies upon for gold/red discrimination, is precisely the axis that tritanopia degrades. The spec says "those two [red and blue] remain separable only via the retained blue-yellow axis" — but for tritanopia users the blue-yellow axis is absent. An implementor reading only the spec's CVD section would conclude that the design holds everywhere except protanopia red/blue; in practice two more sub-floor pairs exist in the documented design. The color-bar letters (g/r, r/b) are the intended fallback for these cases, and they do work — but the spec does not say so for these additional cases.
- **Evidence:** `test_v6_palette_lightness.py`: `CVD_EXCEPTIONS = { "protan": {frozenset({"red","blue"}): 7.4}, "deutan": {frozenset({"gold","red"}): 17.2}, "tritan": {frozenset({"red","blue"}): 15.7} }`. Test passes on current code, confirming these values are accurate and intentionally accepted. Machado simulation corroborates: deuteranopia red → L*=60.8, gold → L*=79.2, ΔL*=18.4 (slight discrepancy from test value due to matrix precision; both are in the sub-20 zone).
- **Recommended action:** Extend the honesty caveat in `docs/spec.md §palette-rationale` to name all three pinned sub-floor pairs and explicitly state that the color-bar letters (g/r, r/b) are the fallback for each. The sentence should read something like: "Under **deuteranopia** gold and red collapse to ΔL\* ≈ 17 (both shift toward yellow-olive); under **tritanopia** red and blue collapse to ΔL\* ≈ 16 (the blue-yellow axis is absent). For all three cases the color-bar letters (`r`/`b`/`g`) are the guaranteed discriminator." This is a pure spec/documentation change; no code changes required.
- **Fix effort:** small (one paragraph addition to spec)

---

### F3: Fingerprint-of marker loses hue salience under protanopia/deuteranopia; spec's "clearly hue-distinct" claim is overstated

- **Population:** CVD (protanopia, deuteranopia)
- **Severity:** MEDIUM
- **Confidence:** CONFIRMED (Machado 2009 simulation)
- **Location:** `docs/spec.md §label-strips` ("Fill color: #a00000"); `src/entviz/pipeline.py:666–671`
- **Finding:** The spec claims that #a00000 "remains clearly hue-distinct from the rest of the label under common CVD simulations." Under Machado protanopia simulation, #a00000 maps to #413704 (very dark brownish, L*=23.2); under deuteranopia, to #5a5700 (dark olive, L*=36.0). The rest of the label is #666666 (L*=43.2). Under protanopia the ΔL*=20.0 lightness difference is clear. Under deuteranopia ΔL*=6.8, which is marginal for a text-sized element. In both cases the hue distinction (dark red vs. gray) is entirely lost: the two colors become dark brown vs. gray-olive and dark olive vs. neutral gray respectively, rendering the label segment "a different shade of brown/gray" rather than "red." Bold font-weight remains the primary differentiator. The WCAG contrast requirement (8.4:1 vs. white) and the Oklab L ∈ [0.35, 0.55] bounds both hold, and the spec correctly specifies these as the normative requirements. The "clearly hue-distinct under common CVD" claim in the spec is what is overstated.
- **Evidence:** Protanopia simulation: marker #413704 (L*=23.2) vs. label #666666 (L*=43.2) — ΔE76=36.4, lightness difference clear but hue collapsed. Deuteranopia: marker #5a5700 (L*=36.0) vs. label #656566 (L*=42.8) — ΔE76=45.4, ΔL*=6.8, both appear gray-olive. The WCAG and Oklab constraints are satisfied; the "hue-distinct" prose claim is not.
- **Recommended action:** Revise the spec's prose claim from "remains clearly hue-distinct from the rest of the label under common CVD simulations" to "remains lightness-distinct from the rest of the label under common CVD simulations; bold font-weight and a lightness difference ≥ 7 are the primary differentiators for CVD users, with hue being a bonus under normal vision." This is a spec-text correction, not a code change. No algorithm or color change is required since the WCAG/Oklab constraints are the normative spec requirements and both pass.
- **Fix effort:** small (spec prose correction only)

---

### F4: No CVD test coverage for blank-cell map dot colors (#d62828/#1d4ed8) or fingerprint-of marker (#a00000)

- **Population:** CVD (all types), GRAYSCALE/LOW-COLOR
- **Severity:** MEDIUM
- **Confidence:** CONFIRMED (confirmed by inspection of `tests/test_v6_palette_lightness.py` — it tests only `POSSIBLE_EDGE_COLORS`)
- **Location:** `tests/test_v6_palette_lightness.py`; `src/entviz/pipeline.py:535,544` (#d62828, #1d4ed8); `src/entviz/pipeline.py:449` (#a00000 marker)
- **Finding:** The existing CVD test (added after adversarial-2026-06-02 F3) tests only `POSSIBLE_EDGE_COLORS` (the 5-color palette). It does not cover the blank-cell map dot colors (#d62828 red, #1d4ed8 blue) or the fingerprint-of truncation marker (#a00000). These colors have distinct CVD profiles from the palette: under protanopia, red dot #d62828 → L*=36.4 and blue dot #1d4ed8 → L*=40.9, giving ΔL*=4.5 (below the palette's 20-unit design floor and even below the admitted protanopia red/blue exception at 7.4). For the marker: under deuteranopia, #a00000 → #5a5700 at L*=36.0, which is only ΔL*=6.8 above the gray label (#666666 L*=43.2). Neither of these behaviors is pinned by any test, so a color change to either could go undetected. This is particularly concerning for the map dots, which are the visual CRC channel a habituated user relies on first and whose CVD behavior is now partially covered in this review (see F1).
- **Evidence:** `test_v6_palette_lightness.py` imports `from entviz.colors import POSSIBLE_EDGE_COLORS` and tests only those 5 values. `grep -r "d62828\|1d4ed8\|a00000" tests/` returns no hits.
- **Recommended action:** Add a second test function (or extend the existing test) that pins the CVD behavior of the map dot colors and the marker color. Specifically: (a) assert that under protanopia, ΔL*(red_dot, blue_dot) ≥ 4.0 and that the two simulated colors have sufficiently different hue (the primary discriminator under protan — brown vs. blue is still correct); (b) assert that under achromatopsia, the two dot colors produce different luminance values (ΔL* ≥ 5); (c) for the marker, assert that Oklab L of #a00000 remains in [0.35, 0.55] and that the marker's lightness is ≥ 5 units below #666666 under all simulations.
- **Fix effort:** small (adds ≈20 lines to the existing palette test)

---

### F5: Ellipse "16 steps ≈ JND" claim is valid for side-by-side comparison but unverified and likely weaker for across-tab/across-zoom comparison (the realistic scenario)

- **Population:** ALL
- **Severity:** MEDIUM
- **Confidence:** SPECULATIVE (needs user study to confirm or deny)
- **Location:** `docs/spec.md §ellipse-overlay` ("16 discrete steps per parameter is intentional: it's near the just-noticeable-difference threshold for both pixel-level radius changes and degree-level rotations, so adjacent steps produce overlays that are visibly distinct from each other")
- **Finding:** The 16-step claim is geometry-defensible for the radius parameter: at a 3×4 grid, the r_step is 4.1px per step (r_range = 61px / 15 steps). A 4.1px shift in the ellipse rim is above the standard 2–4px edge-position JND for a side-by-side comparison at typical viewing distance. For rotation at 12° per step: psychophysical literature (Riesz 1979; Howard & Rogers 1995) puts orientation JND at 2–5° for small targets but up to 10–15° for complex shapes with brief exposure. The 12° step is above the low-end JND but not firmly above the complex-shape threshold. The **critical practical scenario** — comparing two entvizes in separate browser tabs, where the user cannot view both simultaneously and must rely on visual memory — is not side-by-side. Memory-based orientation and size comparison has a much higher effective JND than simultaneous comparison: estimates of 2–4× inflation are common. Under across-tab comparison, adjacent rotation steps (12°) and rx/ry steps (4.1px) may be imperceptible, making the effective discriminable steps perhaps 6–8 rather than 16. This would reduce the ellipse channel's contribution from ~10 bits nominal to ~6 bits. The claim in the spec is technically qualified ("near the just-noticeable-difference threshold") but does not flag the across-tab degradation, and the spec's opening requirement is that comparison can be done to detect differences — the comparison modality is unspecified.
- **Evidence:** Geometry computation at 12pt: r_step=4.1px, rotation_step=12°. No user study in the repo (none cited). The spec names the JND claim as a design rationale but provides no citation and no measurement. The ellipse audit (`reviews/ellipse-audit-2026-06-02.md`) covers coverage percentages, not discriminability.
- **Recommended action:** Add a qualification to the ellipse-overlay section: "The JND estimates assume simultaneous side-by-side comparison; for across-tab or delayed comparison the effective JND for both radius and rotation is higher, and the discriminable step count may be 6–8 rather than 16." Also note that no formal user study validates the JND claim. Optionally, add a user-study suggestion to Residual Unknowns in the spec or the paper. This is a documentation change; no algorithm change is implied.
- **Fix effort:** small (spec documentation addition)

---

### F6: Surround-box individual discriminability collapses at small display sizes; 24-bit channel reduces to a density histogram

- **Population:** LOW-VISION, small-display (mobile/scaled)
- **Severity:** MEDIUM
- **Confidence:** LIKELY (geometry analysis; no empirical user study)
- **Location:** `docs/spec.md §geometry` (box dimensions); spec requirement "Work in environments that can draw bitmapped or vector graphics"
- **Finding:** At 12pt/96dpi the surround boxes are 6×10px — individually resolvable for normal-acuity viewers. At 6pt (the minimum allowed reference font size) boxes shrink to 3×5px. More practically: if a 12pt entviz is displayed at 50% scale in a browser (e.g., a small viewport that scales the SVG proportionally), the boxes visually become 3×5px equivalents. At ≤3px width, anti-aliasing and sub-pixel rendering smear adjacent boxes together, converting the 24-bit pattern channel into a density histogram. A dense surround and a sparse surround become distinguishable (perhaps 3–4 bits), but individual box positions (which is what makes 24-bit patterns discriminable) are lost. The spec geometry section derives box dimensions from font_size_px but does not specify a minimum rendered size below which the box-level interpretation degrades. The spec requirement for SVG responsiveness (`viewBox` for scaling) means the degradation is reachable in any responsive layout. The 30pt maximum font size provides protection from the upper end but nothing explicitly guards the lower visual rendering size.
- **Evidence:** Geometry: at 6pt, box_width = 3px, box_height = 5px. CSS-scaled 12pt at 50% → same. Standard display-acuity limit for individual feature resolution: ~2px on a 96dpi display at arm's length. At 3px width, inter-box spacing is 0 (boxes are flush), so adjacent filled boxes merge into a solid strip. The surround pattern's discriminability comes from the spatial arrangement of filled/empty boxes; merging eliminates the spatial information and leaves only aggregate fill count.
- **Recommended action:** (a) Add a note to the spec that box-level discriminability depends on rendered physical size: "At display sizes rendering surround boxes below ~4×7px (e.g., a 6pt reference font or a 12pt entviz scaled to ≤50% of its design size), individual boxes may merge visually and the surround channel degrades to a fill-density hint." (b) Consider recommending a minimum rendered font size of 8pt for comparison purposes (boxes at 8pt are 4×6.67px — above the critical threshold). This is documentation; no algorithm change required.
- **Fix effort:** small (spec note)

---

### F7: Comparison ergonomics — the same/different asymmetry is documented in the README but has no in-band cue near the comparison act

- **Population:** ALL
- **Severity:** LOW
- **Confidence:** SPECULATIVE (no user study; established in cognitive psychology literature)
- **Location:** `README.md:21` (the asymmetry statement); no in-SVG equivalent
- **Finding:** The README correctly states "Reject on any visible difference. The check is asymmetric: *any* visible difference ... means the values are **different**. A match is **never proof** of identity." This is the right guidance, and it is present. However, a user who renders an entviz from a library (not from the CLI) and embeds it in a web page or email may never see the README. The SVG itself carries no advisory text reminding the viewer of the comparison semantics. The habituated user — checking the color bar and blank map for the 100th time — has been conditioned by prior successes to interpret "looks the same" as "is the same." There is no in-band prompt to also verify channels not yet checked. This is a known cognitive failure mode (the "looks-same-means-safe" bias) for which the SHA-512 fingerprint-driven channels provide the technical defense, but that defense is only active if the user actually *looks* at those channels. Prior review finding F4 (adversarial-2026-06-02) raised this as an unresolved concern; the README addition is a partial fix. The current architecture correctly requires full multi-channel comparison but provides no enforcement or reminder mechanism at the point of comparison.
- **Evidence:** `README.md:21`: "Reject on any visible difference." Present and correct. No comparable text in the SVG metadata (`data-entviz-version`, `data-cols`, etc.). No visible warning label inside the SVG for users who may be viewing the SVG directly without the README context.
- **Recommended action:** Accept this as a known design limitation of a standalone SVG output (SVGs cannot run scripts or change their rendering based on viewer context). Document in the spec as an accepted risk. For the planned comparison UI (mentioned in `docs/spec.md §thoughts-about-comparing`), recommend that the UI surface the comparison semantics prominently ("any difference = reject") near the comparison view. Fix effort in the planned UI: small. Fix effort in the SVG itself: none practical.
- **Fix effort:** small (accept-risk documentation + future UI note)

---

## Additional Patterns Noted

**Color-bar letter fill under CVD.** The letter `r` on the red band uses black fill (Oklab L=0.657 > 0.6 → black text, `pipeline.py:1028`). Under protanopia, the red band simulates to brownish #7b6932 (L*≈56); black letter on L*=56 gives contrast ≈ (56+5)/(0+5) ≈ 12:1 — still legible. The spec comment in `pipeline.py` flags this as the lowest-contrast band/letter pair; it is correct that it is lowest, but it is still above WCAG AA. No further action required, but this is worth monitoring if the reference red color ever changes.

**Gold/red near-miss under deuteranopia in the surround channel.** Per the palette test, gold/red ΔL*≈17.2 under deuteranopia (sub-20 floor). This means per-cell surround rings that differ only in gold vs. red edge color will be harder to distinguish for deuteranopia users — both shift to similar yellow-olive tones. The color-bar letters `g`/`r` compensate in the bar, but the per-cell surround ring has no letter. A deuteranopia user comparing two entvizes where the surround ring colors differ only in gold vs. red across cells will perceive the surrounds as the same color in ~50% of cells. The spec says "perceptual selection ensures that even color-blind viewers can detect each cell as a separate object distinct from the background" — this claim is about detection from background (still true), not discrimination between cells with different edge colors (not guaranteed). This was prior F3 (adversarial-2026-06-02), partially addressed by the test but not resolved in the algorithm; the accepted risk is that the letters carry the gestalt fallback and the per-cell surround is a hint, not a standalone discriminator, under severe CVD.

**Font chain completeness.** The MONOSPACE_FONT_FAMILY chain (`renderer.py:15–18`) correctly includes JetBrains Mono, Menlo, Consolas, DejaVu Sans Mono, Liberation Mono, Roboto Mono, Noto Sans Mono, monospace. All named fonts have good 0/O and 1/l/I disambiguation. The final `monospace` fallback is a necessary safety valve but resolves to platform defaults that may not have slashed zeros or serif-distinguished glyphs (e.g., some Android system fonts). This is the known residual risk documented in the spec; the spec correctly forbids bare `monospace` alone. No new action required.

**Protanopia red/blue ΔL*=10.5 vs. spec claim of ΔL*≈7.** The spec says "red and blue swatches collapse to ΔL\* ≈ 7 regardless of palette choice." Machado 2009 simulation gives ΔL*=10.5 (red L*=45.9, blue L*=35.3 under protanopia). ΔL*=7 would be the Vienot 1999 model estimate. The Machado model is more accurate for full dichromacy simulation. The spec's "≈7" is therefore slightly pessimistic compared to the more modern model — not a finding per se, but worth correcting if the spec is updated to name all sub-floor pairs (see F2).

---

## Residual Unknowns

**U1: Across-tab rotation JND.** Does a 12° rotation step in the ellipse overlay remain detectable when the viewer must switch tabs and recall the previous orientation from visual memory? The geometry argument for simultaneous JND is sound; the memory-based JND is unknown. The smallest study that would settle this: 20–30 participants performing a same/different judgment on tab-switched pairs that differ by 0, 1, or 2 rotation steps, measured as d' from signal detection theory.

**U2: Surround box merge threshold in practice.** At what actual rendered pixel width does the surround shift from "per-box discrimination" to "density histogram"? The 3px threshold above is an engineering estimate. The smallest measurement: present surround patterns at the font-size range [6pt, 30pt] and measure accuracy of a specific box-identification task (locate the filled box at position N) vs. a density estimation task (is the pattern more than 50% filled?).

**U3: Habituation degradation rate.** How quickly does a repeated-comparison user collapse from "full multi-channel inspection" to "check color bar + blank map + done"? This directly quantifies the security margin for a habituated user. Cannot be settled analytically; requires a longitudinal user study with 10–20 participants performing 50–100 comparisons each.

**U4: Achromatopsia map dot usability.** Can an achromatopsia user reliably perform the "are both gray dots in the same position" positional check, given that they cannot assign max/min semantics by color? This is a specific usability question for the ~1-in-50,000 achromatopsia population.

---

## Findings Manifest

```yaml
findings:
  - id: PSY-F1
    persona: perception-reviewer
    title: Blank-cell map dots semantically indistinguishable under achromatopsia; marginal under tritanopia
    severity: HIGH
    confidence: CONFIRMED
    location: src/entviz/pipeline.py:535-542; docs/spec.md §blank-cell-map
    dedupe_key: blank-map-indiscriminable-under-cvd
    recommended_disposition: recommend-fix
    rationale: Under achromatopsia both dots become gray (ΔL*=7.8); the max/min semantic carried by red vs. blue hue is invisible; the habituated check first channel loses color semantics entirely.
    revisit_condition: null
    fix_effort: small

  - id: PSY-F2
    persona: perception-reviewer
    title: Spec palette honesty caveat omits deuteranopia gold/red and tritanopia red/blue sub-floor pairs
    severity: HIGH
    confidence: CONFIRMED
    location: docs/spec.md §palette-rationale; tests/test_v6_palette_lightness.py:CVD_EXCEPTIONS
    dedupe_key: palette-indiscriminable-under-cvd
    recommended_disposition: recommend-fix
    rationale: Test suite pins deutan gold/red (ΔL*≈17.2) and tritan red/blue (ΔL*≈15.7) as known exceptions but spec text only names protan red/blue; implementors and users reading the spec are misinformed about the full CVD guarantee.
    revisit_condition: null
    fix_effort: small

  - id: PSY-F3
    persona: perception-reviewer
    title: Fingerprint-of truncation marker loses hue salience under protanopia/deuteranopia
    severity: MEDIUM
    confidence: CONFIRMED
    location: docs/spec.md §label-strips; src/entviz/pipeline.py:666-671
    dedupe_key: fingerprint-marker-indiscriminable-under-cvd
    recommended_disposition: recommend-fix
    rationale: Under deutan, #a00000 → L*=36.0 vs. #666666 L*=43.2 (ΔL*=6.8); bold weight is the only surviving differentiator; spec prose claim "clearly hue-distinct under common CVD" is overstated and could mislead replacement implementations.
    revisit_condition: null
    fix_effort: small

  - id: PSY-F4
    persona: perception-reviewer
    title: No CVD regression test for blank-cell map dot colors or fingerprint-of marker color
    severity: MEDIUM
    confidence: CONFIRMED
    location: tests/test_v6_palette_lightness.py; src/entviz/pipeline.py:535,544,449
    dedupe_key: blank-map-missing-test-cvd
    recommended_disposition: recommend-fix
    rationale: Palette CVD test covers only POSSIBLE_EDGE_COLORS; map dots (#d62828/#1d4ed8) and marker (#a00000) have distinct CVD profiles (protan dots ΔL*=4.5; deutan marker ΔL*=6.8) that could regress silently on any color change.
    revisit_condition: null
    fix_effort: small

  - id: PSY-F5
    persona: perception-reviewer
    title: Ellipse 16-step JND claim is unqualified and may not hold for across-tab comparison
    severity: MEDIUM
    confidence: SPECULATIVE
    location: docs/spec.md §ellipse-overlay
    dedupe_key: ellipse-indiscriminable-on-small-display
    recommended_disposition: recommend-fix
    rationale: Spec asserts 16 steps ≈ JND without qualification; memory-based comparison (the across-tab scenario) has effectively higher JND than simultaneous side-by-side; the claim needs a qualifier and a residual-unknown callout.
    revisit_condition: null
    fix_effort: small

  - id: PSY-F6
    persona: perception-reviewer
    title: Surround box individual discriminability collapses below ~4px box width (6pt or scaled small)
    severity: MEDIUM
    confidence: LIKELY
    location: docs/spec.md §geometry; src/entviz/pipeline.py:237-241
    dedupe_key: surround-indiscriminable-on-small-display
    recommended_disposition: recommend-fix
    rationale: At 6pt (minimum) or when a 12pt entviz is displayed at ≤50% scale, boxes reach ~3×5px and adjacent filled boxes merge under anti-aliasing; the 24-bit surround degrades to a 3-4 bit density hint. No spec guidance protects against this.
    revisit_condition: null
    fix_effort: small

  - id: PSY-F7
    persona: perception-reviewer
    title: Same/different asymmetry is documented in README but has no in-SVG equivalent for embedded contexts
    severity: LOW
    confidence: SPECULATIVE
    location: README.md:21; docs/spec.md §thoughts-about-comparing
    dedupe_key: comparison-guidance-missing
    recommended_disposition: recommend-accept-risk
    rationale: The asymmetry guidance is present in README and the planned comparison UI can surface it; an SVG cannot self-enforce comparison semantics. Accepting this as a design boundary is appropriate with a note pointing toward the planned UI for mitigation.
    revisit_condition: When a comparison UI is implemented; the UI should surface this prominently.
    fix_effort: small
```
