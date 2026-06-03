# Plan: updating the entviz paper to match the v6 spec

**Date:** 2026-06-02
**Author of plan:** Claude (Opus 4.8, 1M context), research agent
**Paper under review:** `docs/entviz-paper.md` ("Amplifying Difference…", dated September 2025, written against the **v1** algorithm)
**Authoritative spec:** `docs/spec.md` (**v6** DRAFT)
**Inputs consulted:** the paper in full; `docs/spec.md` in full; `this.i`; `reviews/spec-improvement-notes.md`; `reviews/ellipse-audit-2026-06-02.md`; `reviews/adversarial-2026-05-27.md` (v4-era); git history of `docs/spec.md`/`docs/index.md` (v1→v6).

> **Scope note / non-goal.** This file is a *plan*, not an edit. It does not modify the paper, spec, source, or `this.i`. A concurrent adversarial-review agent is producing `reviews/adversarial-2026-06-02.md` with a v6 per-channel perceptual-entropy budget and threat model; that file is flagged below as a hard input for the paper's Section 4.3 / analysis numbers. Do not block on it.

---

## 0. Reconciliation overlay (added 2026-06-02, post-hardening)

> **Read this first.** This plan was written earlier on 2026-06-02, *before* the v6 hardening commits landed later the same day (palette/CVD rework, the F1/F2 fingerprint-middle redesign, the overlay edge-stroke, and the F4–F7 fixes). The plan's **framework analysis (§1–§3, §5), figure list (§4.2), citation list (§5.2), and effort model (§6) all stand.** But several specifics it treats as *open/concurrent* or describes *from the then-current spec* have since changed. Apply this overlay on top of the rest of the document; where they conflict, this section wins.

**Now resolved (no longer "concurrent"):**
- **`reviews/adversarial-2026-06-02.md` exists and is committed** — the "hard dependency / do not block / if not ready" caveats (P3, §4.1.1, §5.1) are moot. ⚠️ But that review did **not** produce a fresh full per-channel budget; it *inherited* the v4-era numbers (~220–270 bits careful / ~25–40 habituated) plus a **v6-deltas** table. Table 3 still needs the full re-derivation — the review supplies the deltas, not the table.
- **All seven findings F1–F7 are now fixed/addressed** (review + commits). The three that change what the paper should say:

**① Palette / CVD — supersedes §4.1.3, the §4.3 "Color Palette" row, Table 4, and open-question #3:**
- **F6's diagnosis was wrong and was corrected.** Gold/red is *not* the weak pair (it is both lightness- and hue-separated). The real weak pair was **white/gold**.
- **Gold was darkened** from `#ffd966` (L\*≈88) to **`#e7be00`** (L\*≈78, the maximin between white L\*100 and red L\*57). **Wherever this plan writes `#ffd966`, the current gold is `#e7be00`.**
- **The CVD metric is ΔL\* (lightness), NOT ΔE.** ΔE76 over-credits chroma — the channel that *collapses* under CVD/mono — so it is the wrong metric. Every "recompute pairwise ΔE under CVD" / "Table 4 ΔE-under-CVD" instruction in this plan should become **ΔL\* under CVD**, with the honest note that **protanopia red/blue collapses to ΔL\*≈7 regardless of palette** (unfixable; the color-bar letters are the guaranteed fallback).
- **The spec's CVD claim was downgraded** (honest caveat added) — i.e. the plan's recommended option (a) for open-question #3 was taken; paper and spec now agree.
- **Authoritative source: `reviews/palette-optimization-findings.md`** (the maximin derivation, why ΔE76 is rejected, the rejected alternatives, the honest limits, citations). This supersedes the plan's §4.1.3 and is the primary input for the paper's palette/CVD discussion. **Figures already exist:** `docs/assets/palette-swatch.svg` and `docs/assets/palette-cvd.svg` (the CVD-simulated grid the plan asks for in F-c / Table 4 — normal + 3 dichromacies + achromatopsia, regenerable via `scripts/palette_figures.py`).

**② Large-input middle — supersedes §4.3.8, §4.1.2, and figure F-f's caption:**
- The middle is **no longer "digest bytes 24–35 in the input alphabet."** v6 now uses a **domain-separated second hash** — `SHA-512("entviz/fingerprint-middle/v6\0" ‖ core)` — rendered as **hex** (6 hex chars = 24 bits per cell). This makes the ≈2⁹⁶ partial-preimage **exact and injective for every alphabet** (it was 80-bit and non-injective for 5-bit alphabets in the first v6 draft) **and independent of the gestalt** (domain separation, closing F2). The F-f caption should read "hex fingerprint-middle," not "input alphabet."
- Head/tail cover **192 bits for 4-/6-bit alphabets but 160 bits for 5-bit alphabets** (the plan's/paper's "first 192 bits" is only right for hex/base64).

**③ Ellipse overlay — refines §4.3.6 / figure F-d:**
- Beyond the coverage clamp the plan already notes, the overlay is now a **subtler interior fill + a 2px edge stroke** at higher opacity (per-bg fill/edge: white 20/30, gold 20/30, red 25/35, blue 35/45). Describe the edge-emphasis split if §4.3.6 covers the overlay's rendering.

**Minor (no paper impact):** blank-map dot radius +1px (2.5→3.5 nominal); fingerprint-middle cells correctly downsized to the 6-char font on non-hex inputs.

**Effect on the effort model (§6):** **P4 (CVD) is largely pre-done** — the analysis, the correct metric (ΔL\*), the honest framing, the two figures, and the citations already exist in `palette-optimization-findings.md`; P4 becomes "import + cite," not "derive." P3's dependency is unblocked (with the budget-table caveat above). All other phases stand.

---

## 1. Summary

**How stale is the paper?** The paper's *framework* (Sections 1, 2, 3, the Gestalt/JND theory, the perceptual-vs-authentication-hashing dichotomy) is **largely sound and reusable** — roughly 55–60% of the text survives with light touch-ups. But every concrete description of **how entviz works** is written against v1 and is now **factually wrong**. The algorithm has been through five major revisions (v2 added the fingerprint + color bar + SCS + ellipse; v3 reworked edges/color-bar-skew/ellipse; v4 replaced the entire edge channel with a 24-box surround, removed the SCS, switched the color-bar data source, added hybrid ellipse anchoring; v5 added head+middle+tail large-input handling, color-bar letters, the loud truncation marker; v6 changed the long-input middle to a fingerprint readout, widened the color bar, replaced the blank-cell clock-hands marker with a map, and clamped the ellipse). **Section 4.3 (the entviz description) and the two comparison tables must be substantially rewritten**, and the central quantitative thesis — that entviz's multi-channel design beats randomart's ~20–24 perceptual bits — **must be re-derived for the v6 channel set**, because the v1 channels the paper credits (8 named edge shapes, a tertiary nucleus-color hint, "quartile marks") are not the v6 channels.

**Highest-risk staleness (in priority order):**
1. **The edge/shape channel is described as it never again existed.** §1.3, §4.3, and Table 1 credit entviz with "a palette of eight distinct geometric primitives (triangle, hook, rect, box, slant, hammer, pyramid, double bars)" forming Gestalt patterns. v6 has **no shapes at all** — the edge channel is a **24-box on/off surround** driven by the ftok quant, with a **single per-cell edge color**. The paper's marquee Gestalt-Continuity/Closure argument is built on a channel that does not exist. This is the single most damaging error: it is repeated, it is load-bearing for the thesis, and a reader who pulls up a real entviz will immediately see the paper describing a different program.
2. **The perceptual-entropy budget is asserted, not computed, and is for the wrong channels.** The paper's Table 1 says entviz has "High (Theoretically all bits are represented in perceptible channels)" and the prose leans on "multi-channel redundancy" — but it never produces a number to put beside randomart's ~20–24 bits. The thesis *demands* a v6 per-channel budget. The v4-era adversarial review already computed one (~220–270 bits careful / ~25–40 bits habituated); v6 changes several channels and the upcoming `adversarial-2026-06-02.md` will refresh it.
3. **Large-input (>512-bit) handling is absent from the paper entirely**, yet it is where the threat model is most interesting (head + fingerprint-middle + tail; the `fingerprint of` marker; the ≈2⁹⁶ partial-preimage argument). A 2025 security-visualization paper that omits this looks incomplete.
4. **"Visual CRCs" are described as "blank cells and quartile marks"** placed as landmarks — true in spirit, but v6's blank-cell **map** (red/blue dots locating the maxftok/minftok cells in a scale model of the grid) and the quartile **corner-triangle orientation** marks are new and concrete and should be shown.
5. **The color palette is described as "5-color [white, gold, red, blue, black]"** used for "edge shapes and colors" — the colors are right, but the *role* changed (single per-cell edge color chosen by perceptual nearest-neighbor to the nucleus bg; black always in the edge palette; bg is 1-of-4 from 2 bits) and the CVD claim is **contradicted by the project's own v4 adversarial finding F6** (gold/red collapse under deuteranopia, ΔE≈27 vs. the paper's own 50–60 severe-CVD threshold). The paper currently makes an accessibility claim the maintainers' own review flags as unsupported.

**Recommended overall approach:** **Targeted rewrite, not a from-scratch paper.** Keep Sections 1.1–1.2, 2 (entire framework), 3 (entire dichotomy), 5.2 (design principles), and 6 with edits. **Rewrite §1.3, §4.3, Table 1, and Table 2's color rows**; **add** a new analysis subsection computing the v6 perceptual-entropy budget and a large-input subsection; **soften or re-scope** the CVD accessibility claim. Treat the empirical-validation gap honestly (§5.3 already does; reinforce it — there is still no entviz user study).

---

## 2. Stale-content inventory

Severity key: **WRONG** = factually incorrect about v6 / will mislead a reader who looks at a real entviz; **INCOMPLETE** = silent about a v6 feature that matters; **DATED** = correct in spirit but uses superseded terminology/numbers.

| Paper location (line / quote) | What it says now | v6 reality | Severity |
|---|---|---|---|
| §1.3 ¶ "three distinct…channels" (l.23–29) | "A secondary channel of **edge shapes and colors**, designed to form larger, emergent patterns." | Edge channel is a **24-box on/off surround** (no shapes); one per-cell edge color chosen as palette entry nearest the nucleus bg. | **WRONG** |
| §1.3 (l.29) | "A **tertiary** channel of nucleus background colors, serving as a redundant hint." | Still present and still a hint, but it is now one of **several** fingerprint/entropy channels; framing as the lone tertiary is dated. Also: the color bar, ellipse, blank-map, quartile marks, entviz-bg are all distinct channels the §1.3 enumeration omits. | INCOMPLETE / DATED |
| §1.3 (l.31) "visual CRCs—deterministically placed blank cells and quartile marks" | Blank cells + quartile marks as landmarks. | Correct concept; v6 specifics differ: blank cells carry a rounded-rect outline, the **first** blank cell is a **map** with red (maxftok) / blue (minftok) dots; quartile marks are **corner triangles whose orientation** (TL/TR/BR/BL) encodes the quartile, filled in the text fg color. | DATED → needs concrete rewrite |
| §1.3 (l.23) "across **three** distinct…channels" | Three channels (text, edge shape+color, nucleus color). | v6 has many more fingerprint-driven channels (surround pattern, per-cell edge color, entviz bg, color bar, ellipse overlay, blank-cell map, quartile marks) layered on the two entropy channels (text, nucleus bg). "Three channels" undercounts. | **WRONG** (count) |
| §4.3 "Algorithm and Goal" (l.164) | "divides it into 3-byte (24-bit) tokens…controls…the text content…the shape and color of the cell's **six edges**…and the background color of the nucleus." | No six edges; **24-box surround** from the ftok quant; **single** edge color per cell; text + nucleus bg from entropy, surround from the **fingerprint** (not the token directly). The corner rects of v1 are gone. | **WRONG** |
| §4.3 "Edge Shapes (Gestalt Coherence)" (l.170–171) | "palette of eight distinct geometric primitives (triangle, hook, rect, box, slant, hammer, pyramid, double bars)…richer set of shapes…Continuity and Closure…varying angles, curvatures, and aspect ratios." | **No shapes exist in v6.** (Even the names are v1; v2 renamed them fin/axe/brick/inf/wave/hole/keel/mound; v4 deleted the channel.) Gestalt grouping in v6 comes from the surround **pixel pattern** "leaking" the edge color outward and from the ellipse overlay — a different, defensible argument that must be rewritten from scratch. The "angles/curvatures/aspect ratios vs JND" tie-in no longer applies to edges; it now applies (if anywhere) to the surround box size and the ellipse axes. | **WRONG** (most load-bearing) |
| §4.3 "Color Palette" (l.173) | "limited, high-contrast **5-color** palette ([white, gold, red, blue, black])…usable by people with common forms of color blindness…ΔE large enough to exceed JND…for color-deficient vision." | Palette colors are right (`#ffffff`,`#ffd966`,`#ff3f2f`,`#2f3fbf`,`#000000`). But: bg is 1-of-4 (2 bits, from median ftok); black is **always** an edge color, never bg; edge color is **deterministic** from nucleus bg (carries 0 independent bits). CVD claim is **contradicted by the repo's own finding F6**: gold vs red ΔE≈26.7 (deuteranopia) / 45.9 (protanopia) — below the paper's quoted 50–60 severe-CVD bar. | **WRONG** (accessibility claim) + DATED (role) |
| §4.3 "Visual CRCs (Salient Landmarks)" (l.175) | Blank cells + quartile marks as landmarks; "Are the blank cells in the same place?" | Concept survives and is good; v6 specifics (the map; corner-triangle quartiles; blank placement via median/ASCII-endpoint shifts driven by the fingerprint) are new and should be described. Also the v6 blank-map explicitly closes adversarial F-A6 (the v5 clock-hand was invisible in non-browser rasterizers). | DATED → rewrite |
| §4.3 "Multi-Channel Redundancy" (l.177) | "same entropy across text, edge shape/color, and nucleus color." | Redundancy story is right, but the channels are different: text + nucleus bg are the **entropy** channels (lossless ≤512 bits); surround, color bar, ellipse, blank-map, quartiles, entviz-bg are **fingerprint**-driven (avalanche). The text-vs-avalanche split (text gives fidelity, fingerprint channels give difference amplification) is a v2+ idea the paper never states. | INCOMPLETE |
| Table 1 (l.181–192) "Entviz" column | "Core Mechanism: Multi-Channel Feature Mapping"; "Estimated Perceptual Entropy: High (Theoretically all bits are represented in perceptible channels)"; Gestalt principles "Proximity, Similarity, Continuity, Closure, Figure-Ground." | Mechanism wording OK. "Theoretically all bits" is **not** a defensible perceptual claim — perceptual bits ≪ nominal bits (the whole point of comparing to randomart's ~20–24). Needs an actual computed number. Continuity/Closure rationale rested on shapes (gone); re-justify via surround-pattern emergence + ellipse. | **WRONG** (entropy cell) / DATED |
| Table 2 (l.87–98) JND table | Generic JND values for size/shape/aspect/curvature/angle/luminance/chromaticity/CVD. | Values are fine and still citable; **but** the table is currently generic and not tied to v6 primitives. Should map each row to the v6 feature that actually uses it (surround box on/off = luminance/contrast not shape; ellipse axes = size/aspect; quartile triangle = angle/orientation; nucleus & edge color = chromaticity + CVD). The "Shape (Curvature)" and "Shape (Aspect Ratio)" rows that justified the *edge shapes* now have no referent unless re-pointed at the ellipse. | DATED → re-map |
| §1.3 / §4.3 — large inputs | **Silent.** Paper never mentions >512-bit handling, truncation, or the fingerprint. | v6: inputs >512 bits show head (8 tok) + **fingerprint-middle (4 tok, digest bytes 24–35 in the input alphabet)** + tail (8 tok); a bold dark-red `fingerprint of` marker; ≈2⁹⁶ partial-preimage resistance; blank placement unified with short inputs. This is a major v5/v6 feature and a core security argument. | **INCOMPLETE** (whole topic missing) |
| §4.3 / Table 1 — the fingerprint | Paper never mentions that most channels derive from a SHA-512 **fingerprint** rather than the entropy directly. | v2+ core design: text + nucleus bg = entropy (lossless ≤512); everything else = fingerprint (so even non-avalanching inputs like UUIDs avalanche visually). This is *the* mechanism that makes the "visual avalanche effect" the paper praises (§3.2) actually true for chosen inputs. Its absence is a real gap. | **INCOMPLETE** (key mechanism missing) |
| §4.1 randomart "~19.71–23.71 bits" (l.148) and Table 1 "~20–24 bits" | Cites ref 56 (the ACSAC'09 Loss/Limmer/von Gernler paper). | Figure is fine to keep **but** must be presented honestly: that paper's own authors call the result *preliminary* (Markov model + limited brute force), and there is no human-subjects perceptual-entropy measurement of randomart. The paper should frame ~20–24 bits as "the best published estimate, acknowledged preliminary," not a hard benchmark — otherwise entviz's "we beat it" claim inherits the shakiness. | DATED (framing) |
| Title block / date (l.7) "September 2025"; author email | Old date; `daniel.hardman@gmail.com`. | If re-released, bump date and confirm the canonical email (`daniel@provenant.net` per environment) and version ("analysis of the v6 algorithm"). | DATED (housekeeping) |
| §5.3 "Avenues for Future Research" | Calls for a user study comparing entviz vs randomart. | Still true and still unmet — reinforce. The adversarial review's Residual Unknown #1 (habituated-user perceptual entropy study) is the single most informative experiment; cite it. | DATED (good, strengthen) |
| Ref 11 "entviz-readme.pdf" | The paper cites a v1 README PDF as its primary source for the algorithm. | The algorithm source of truth is now `docs/spec.md` (v6). Update the citation to the v6 spec + commit hash for reproducibility. | DATED |

---

## 3. Section-by-section change plan

### §1 Introduction
- **§1.1 (human bottleneck), §1.2 (hash visualization / Perrig & Song):** **Keep.** Timeless framing; light copy-edit only. Optionally refresh ¶ with the 2021–2023 word-based-fingerprint usability findings (see §5) to show the bottleneck is still an active research problem.
- **§1.3 (introducing entviz):** **Rewrite.** Replace "three distinct…channels" enumeration with the v6 channel inventory:
  - *Entropy channels (lossless ≤512 bits):* (1) tokenized **text** grid; (2) per-cell **nucleus background color**.
  - *Fingerprint channels (avalanche, work even for chosen/structured inputs):* (3) the **24-box surround** pattern; (4) the per-cell **edge color**; (5) the **entviz background color**; (6) the **color bar** (2-bit-pattern histogram of the digest, count⁴ skew, color letters); (7) the **ellipse overlay**; (8) **blank-cell positions + the blank-cell map**; (9) **quartile corner-triangle marks**.
  - Introduce the **fingerprint** (SHA-512 of normalized entropy) as the mechanism that gives chosen inputs a visual avalanche.
  - Replace "eight geometric primitives" sentence entirely. Keep "visual CRCs" but describe the v6 map + corner triangles.
- **§1.4 (thesis/structure):** **Keep**, but ensure the thesis sentence promises a *computed* v6 perceptual-entropy comparison (currently it only promises a qualitative one).

### §2 Perceptual & cognitive framework
- **§2.1 (Gestalt), §2.1.1–2.1.3, §2.2.1 (Weber):** **Keep as-is.** Framework is independent of algorithm version.
- **§2.2.2 Table 2 (JND thresholds):** **Keep the data; re-map the rows** to v6 primitives (see inventory). Add a column or footnote "entviz feature governed" so each JND threshold has a v6 referent. Repoint the aspect-ratio/curvature rows from the (defunct) edge shapes to the **ellipse axes** and **surround box geometry**. Add an explicit note that the **surround boxes encode bits as filled/empty** — i.e., the relevant threshold is luminance/contrast detection of a small filled rectangle, not shape discrimination.
- **§2.2.3 (ordinary vision / 20/40 / CVD):** **Keep, strengthen.** This is where to introduce CVD prevalence numbers (≈8% of men, ≈0.5% of women; deuteranomaly ≈5% of men) and the Machado et al. (2009) physiologically-based simulation as the standard tool — both back the accessibility discussion and set up the honest §4.3 CVD caveat.

### §3 Two philosophies (perceptual hashing vs authentication visualization)
- **Entire section: keep.** This taxonomy is the paper's strongest original contribution and is version-independent. Optional: add one sentence noting entviz's fingerprint-driven channels are what operationalize the "visual avalanche effect" §3.2 describes (ties §3 to the corrected §4.3).

### §4 Comparative analysis
- **§4.1 SSH randomart:** **Keep, reframe one claim.** Present the ~20–24-bit figure as the best published *but preliminary* estimate (the source authors say so). Everything else (drunken-bishop description, user-study accuracy/time numbers, verbal-description weakness) stays.
- **§4.2 QR codes:** **Keep as-is.** Version-independent baseline.
- **§4.3 Entviz:** **Rewrite substantially** — this is the bulk of the work. New structure:
  1. *Algorithm and goal:* normalize → SHA-512 fingerprint → tokenize entropy (24-bit tokens) → grid. State the entropy-vs-fingerprint split. State the ≤512-bit losslessness promise.
  2. *Text channel (Gestalt: Proximity / chunking):* keep the existing chunking argument; it survives.
  3. *Surround channel (replaces "edge shapes"):* 24 boxes, bit i of the ftok quant fills box i, single edge color = palette entry nearest the nucleus bg by weighted RGB distance. Gestalt argument: the filled-box pattern reads as the nucleus color "leaking outward," tying the cell into one perceived object; adjacent cells' patterns + the ellipse overlay create emergent large-scale structure. **Drop the shape/Continuity/Closure-via-shapes claim**; rebuild on pattern emergence + the ellipse.
  4. *Nucleus + edge color (chromaticity / JND / CVD):* the entropy-driven nucleus bg (16M colors, lossless ≤512 bits, hint-only because fine gradations fall below JND / collapse at low color depth); the deterministic edge color. **Honest CVD treatment:** state the palette aims for CVD usability, then disclose finding F6 (gold/red collapse under deutan/protan) and the mitigations (luminance contrast for object detection survives; color letters on the color bar; quartile marks carry info by orientation not color; blank map by position). Re-scope the claim from "discriminable for all" to "detectable as distinct objects for all; some palette *pairs* are not chromatically discriminable under severe CVD, so no channel relies on color alone."
  5. *Color bar:* digest 2-bit-pattern histogram, count⁴ skew → readable dominance, descending bands, **color letters (w/g/r/b/k)** for CVD/monochrome/filtered displays, wider bar (v6).
  6. *Ellipse overlay:* fingerprint-anchored, hybrid interior/external anchor, **v6 coverage clamp** [0.22·d_far, 0.58·d_far] keeping coverage ≈8–70% (median ≈32%); cite the ellipse audit. Tie to size/aspect JND (Table 2).
  7. *Visual CRCs:* blank-cell positions (median + ASCII-endpoint shifts from the fingerprint), the **blank-cell map** (red maxftok / blue minftok dots in a scale model — closes F-A6), **quartile corner triangles** (orientation = quartile).
  8. *Large-input handling (NEW):* head + fingerprint-middle + tail; the `fingerprint of` marker; the ≈2⁹⁶ partial-preimage argument; why the v6 fingerprint-middle (vs v5 body slices) guarantees read-aloud avalanche.
  9. *Multi-channel redundancy + perceptual-entropy budget:* fold in the new computed budget (§4 new analysis below).
- **Table 1 (philosophies comparison):** **Rewrite the Entviz column.** "Core Mechanism" → "Fingerprint-driven multi-channel feature mapping (text + nucleus lossless; surround/color-bar/ellipse/CRC avalanche)." "Estimated Perceptual Entropy" → the **computed** v6 figure (e.g., "~X bits careful side-by-side; ~Y bits habituated-landmark; clears randomart's ~20–24-bit estimate under careful comparison"). Re-justify the Gestalt-principles cells off the surround/ellipse rather than shapes.

### §5 Synthesis & framework
- **§5.1 (synthesis):** **Light edit** — drop "rich set of geometric primitives" (no longer true); substitute "structured surround patterns, a perceptually-selected palette, fingerprint-driven gestalt channels, and visual CRCs."
- **§5.2 (design principles 1–4):** **Keep.** All four principles are version-independent and, if anything, v6 supports them *better* (P3 salient landmarks ← blank map; P4 redundancy ← more channels). Principle 1's "easily nameable geometric primitives" should be softened to "simple regular primitives" since entviz no longer uses *nameable* shapes.
- **§5.3 (future research):** **Keep, strengthen.** Reinforce that no entviz user study exists; cite the adversarial review's Residual Unknown #1 (habituated-user perceptual-entropy study) and the 2021–2023 fingerprint-verification methodology as a template. Add CVD human-subjects validation of the palette (finding F6) as a named open question.

### §6 Conclusion
- **Keep**, update the "rich set of geometric primitives" phrasing if echoed, and make the summary-of-contributions consistent with the corrected channel description.

### Front matter / references
- Update date, version ("v6 algorithm"), author email. Replace ref 11 (v1 README PDF) with `docs/spec.md` at a pinned commit. Add the new citations from §4 below.

---

## 4. New analysis & figures needed

### 4.1 New / re-derived analysis (internal)
1. **v6 per-channel perceptual-entropy budget (the central re-derivation).** This is the paper's thesis and must be recomputed for v6's channel set, *not* inherited from v1. Inputs needed:
   - Per-channel nominal vs. perceptually-discriminable bits under (a) normal vision + 16M color, careful side-by-side; (b) habituated landmark-only; (c) severe deuteranopia; (d) 256-gray / low-color-depth; (e) small / 20/40 acuity.
   - Channels to score: text (verbatim, special-cased), 24-box surround (24 nominal bits/cell × token count; perceptual ≪ nominal), nucleus bg (24/cell, hint), per-cell edge color (**0 independent bits** — deterministic from nucleus), entviz bg (**2 bits**), color bar (4 buckets + count⁴ skew ≈ a few bits), ellipse overlay (anchor × rx × ry × rotation, ~16 nominal, fewer perceptual), blank-cell positions + **map** (positions, no longer angles — recompute vs. v4's clock-hands estimate), quartile marks (4 cells × orientation).
   - **Dependency:** the concurrent `reviews/adversarial-2026-06-02.md` will contain a v6 budget table and threat model — use it as the primary input and cite it. The v4-era `adversarial-2026-05-27.md` table (≈220–270 bits careful / ≈25–40 habituated / ≈130–180 severe-CVD) is the starting point; v6 deltas to fold in: blank-map replaces clock-hands (position vs. angle), wider color bar, clamped ellipse coverage, fingerprint-middle for large inputs.
   - **Output:** a v6 budget table to replace Table 1's hand-wavy "High (all bits)" cell, plus a sentence stating the headline (clears randomart's ~20–24 under careful comparison; habituated-landmark figure is the honest weak point).
2. **Large-input security argument (NEW subsection).** Derive/explain the ≈2⁹⁶ partial-preimage cost of matching head + tail + the 4 displayed fingerprint tokens, and why the v6 fingerprint-middle guarantees read-aloud (screen-reader) avalanche where v5's body slices did not. Source: spec "Large-input handling" + `this.i` migration notes.
3. **CVD ΔE re-derivation for the v6 palette.** Recompute pairwise ΔE of `{white, gold, red, blue, black}` under deuteranopia/protanopia/tritanopia/achromatopsia (Machado 2009 matrices, ΔE in CIELAB or ΔE00), confirm/cite finding F6's gold/red ≈27 (deutan) result, and state which channels carry information *without* relying on the collapsing pair (color letters, orientation, position, luminance).
4. **Surround-pattern / box-size JND check.** A short note on whether a single filled 6×10-px box at 12pt/96dpi is above contrast-detection threshold at 20/40 acuity and typical viewing distance (drives the "is the surround channel readable for ordinary vision" claim). Can be a back-of-envelope using the Table 2 luminance Weber fraction + acuity geometry.

### 4.2 Figures needed (the paper currently has **none** of these; v1 README figures are obsolete)
Regenerate all from the v6 reference implementation (`PYTHONPATH=src python -m entviz …`), at a fixed reference font size, and caption with the input used:
- **F-a. Anatomy of a v6 cell:** nucleus + 24-box surround + edge color + (if applicable) quartile triangle, labeled. (Replaces the v1 6-edge-rect / shape diagrams.)
- **F-b. The 24-box surround:** the same input vs. a 1-bit-different input, showing how the surround pattern avalanches while the text barely changes. Directly illustrates §3.2's "visual avalanche."
- **F-c. v6 color bar:** with count⁴-skewed bands and the w/g/r/b/k letters; ideally a CVD-simulated copy beside it to show the letters survive.
- **F-d. Clamped ellipse overlay:** 2–3 grids (small external-anchor + large interior-anchor) showing noticeable-but-partial coverage; cite the audit's coverage band.
- **F-e. Blank-cell map + quartile triangles:** a grid annotated to show the map's red/blue dots locating maxftok/minftok and the four corner-triangle orientations.
- **F-f. Large-input layout:** a >512-bit input showing head | fingerprint-middle (neutral nuclei, gold/white frame) | tail, with the bold red `fingerprint of …` top label.
- **F-g. Whole-entviz comparison:** two near-identical inputs side by side (the paper's core use case), demonstrating multi-channel difference amplification.
- **(Keep)** a randomart and a QR example for §4.1/§4.2 contrast (likely already implied; ensure present).

### 4.3 New / updated tables
- **Updated Table 1** (Entviz column rewrite + computed entropy).
- **Updated Table 2** (JND rows re-mapped to v6 features).
- **New Table 3 — v6 per-channel perceptual-entropy budget** (the core deliverable; mirrors the adversarial review's structure).
- **New Table 4 — v6 palette ΔE under CVD** (small, backs the honest accessibility claim).

---

## 5. Research & citations

### 5.1 Internal re-derivations required (recap)
- v6 per-channel perceptual-entropy budget (§4.1.1) — **primary input: `reviews/adversarial-2026-06-02.md`** (concurrent).
- ≈2⁹⁶ large-input partial-preimage argument (§4.1.2) — from spec + `this.i`.
- v6 palette CVD ΔE table (§4.1.3) — recompute, cross-check finding F6.
- Surround-box contrast-detection sanity check at 20/40 (§4.1.4).

### 5.2 External sources found (candidate citations, with the claim each supports)

**Randomart / drunken bishop perceptual-entropy benchmark (the ~20–24-bit figure; frame as preliminary):**
- Loss, Limmer, von Gernler, *The Drunken Bishop: An Analysis of the OpenSSH Fingerprint Visualization Algorithm* (2009). PDF: http://dirk-loss.de/sshvis/drunken_bishop.pdf — the source of the ~19.71–23.71-bit estimate; authors explicitly call it preliminary (Markov model + limited brute force). **Already paper ref 53/56; re-cite with the "preliminary" framing.**
- Perrig & Song, *Hash Visualization: A New Technique to Improve Real-World Security* (CrypTEC '99). https://users.ece.cmu.edu/~adrian/projects/validation/ — foundational; already paper refs 2–4/8. Keep.

**Recent (2021–2023) key-fingerprint verification usability — refreshes §1 and §5.3 "related work" and the user-study template:**
- Livsey, Petrie, Shahandashti, Fray, *Performance and Usability of Visual and Verbal Verification of Word-based Key Fingerprints* (HAISA 2021). arXiv: https://arxiv.org/abs/2106.01131 — 62-participant study; visual comparison more effective against non-security-critical errors, verbal perceived easier. Supports the "humans are the bottleneck; visual vs verbal trade-offs" framing and gives a methodology template for the proposed entviz study.
- Turner, Shahandashti, Petrie, *The Effect of Length on Key Fingerprint Verification Security and Usability* (ARES 2023). arXiv: https://arxiv.org/abs/2306.04574 — 162 participants; security-critical errors rise with fingerprint length. Supports "longer strings are worse for humans → visualize instead," and motivates entviz's chunking/landmark approach.
- (Background, for §3/§4 related work) Tan et al., *Can Unicorns Help Users Compare Crypto Key Fingerprints?* (CHI 2017) — **already paper ref 55**; keep.

**Color vision deficiency prevalence + simulation — backs §2.2.3 and the honest §4.3 CVD caveat (Table 4):**
- CVD prevalence: ≈8% of men, ≈0.5% of women globally (~300M people); deuteranomaly ≈5% of men, deuteranopia ≈1.2%, protanopia ≈1% of men. Sources: Colour Blind Awareness statistics (https://colorblind.io/learn/statistics); MDPI 2025 review *A Global Perspective of Color Vision Deficiency* (https://www.mdpi.com/2227-9032/13/16/2031); underlying Birch (2012) prevalence study. **New citation** (paper's NEI ref 45 covers types but not prevalence).
- Machado, Oliveira, Fernandes, *A Physiologically-based Model for Simulation of Color Vision Deficiency* (IEEE TVCG 15(6), 2009). https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html — the standard CVD simulation model (unifies dichromacy + anomalous trichromacy via cone spectral shift; severity 0–1). **New citation**; use as the named method for the Table 4 ΔE-under-CVD computation. (More principled than the Brettel/Vienot matrices the v4 adversarial review used; mention both.)

**Color-difference / JND theory — backs Table 2 chromaticity rows and the Oklab text-contrast rule entviz uses:**
- MacAdam (1942) ellipses + ΔE≈1 ≈ JND, with the caveat that ΔE_ab fails at high chroma (hence ΔE94 / ΔE00). https://en.wikipedia.org/wiki/MacAdam_ellipse — **already paper ref 40 (Konica Minolta) covers this; add the ΔE00 caveat** so the ΔE numbers in Table 4 use a defensible metric.
- Ottosson, *A perceptual color space for image processing (Oklab)* (2020). https://bottosson.github.io/posts/oklab/ — entviz v6 picks cell-text/letter foreground by **Oklab lightness** (L<0.6 → white). The paper never mentions this; it is a concrete psychophysics-grounded design choice worth a sentence + citation in §4.3 (and it's the kind of detail that strengthens the "perceptual engineering" thesis). **New citation.**

**Keep (still valid) from the existing reference list:** refs 1 (USENIX human-distinguishable fingerprints), 2–8 (Perrig & Song / hash-viz lineage), 12–27 (Gestalt, memorability, cognitive load), 28–43 (JND/Weber/color JND — the framework), 44–45 (acuity, CVD types), 46–50 (perceptual hashing), 51–56 (randomart/drunken-bishop/QR), 57–66 (QR / MLLM). Most of the framework citations need no change.

**Drop / replace:** ref 11 (`entviz-readme.pdf`, v1) → `docs/spec.md` v6 at a pinned commit.

---

## 6. Effort estimate & suggested ordering

Rough sizing (writing + figure generation; assumes the v6 reference implementation renders figures on demand):

| Phase | Work | Depends on | Rough effort |
|---|---|---|---|
| **P0** | Confirm intent: targeted update vs. broader rewrite; confirm date/version/email; pin spec commit. | author | 0.5 day |
| **P1** | Rewrite §1.3 channel inventory + introduce fingerprint. Re-map Table 2 rows. (Low-risk, no new numbers.) | — | 1 day |
| **P2** | Rewrite §4.3 fully (surround, palette/CVD-honest, color bar, ellipse, CRCs, large inputs). Generate figures F-a…F-g from the v6 impl. | P1 | 2–3 days |
| **P3** | Compute v6 perceptual-entropy budget (Table 3) + rewrite Table 1 entropy cell + headline thesis number. | **`adversarial-2026-06-02.md`** (concurrent); P2 | 1–1.5 days |
| **P4** | CVD ΔE table (Table 4) + Machado/prevalence citations; honest §4.3 + §2.2.3 + §5.3 accessibility text. | P2 | 0.5–1 day |
| **P5** | §4.1 randomart "preliminary" reframing; §5/§6 consistency edits; reference-list update; final pass. | P2–P4 | 0.5–1 day |

**Total: ~6–8 focused days**, dominated by the §4.3 rewrite and the budget re-derivation.

**Dependencies / flags:**
- **Hard dependency:** P3 (the entropy budget, i.e. the thesis number) should consume `reviews/adversarial-2026-06-02.md`. If that file is not ready, P3 can proceed from the v4-era `adversarial-2026-05-27.md` table with v6 deltas applied, but should be reconciled when the new review lands.
- **User-study caveat:** the paper's thesis remains *theoretically supported, empirically untested* — there is still no entviz user study and the randomart benchmark itself is preliminary. The update should not over-claim; P3/§5.3 must keep the "needs empirical validation" framing. Do not let the rewrite imply a measured human result that doesn't exist.
- **Concurrent adversarial review:** any threat-model language in §3/§4.3 should be kept consistent with whatever `adversarial-2026-06-02.md` settles on (attacker tiers, win conditions).

---

## 7. Open questions for the author

1. **Re-release vs. errata?** Is the goal a v6 *revision* of the same paper (recommended) or a fresh paper? This affects whether §1–§3 framing is preserved verbatim or modernized.
2. **Audience/venue?** Academic (USENIX/SOUPS/CHI usable-security) vs. a project whitepaper. A peer-reviewed venue would *require* the empirical user study §5.3 calls for; a whitepaper can ship with the theoretical budget alone. This decides whether P3's number stands as the headline or is explicitly labeled a model estimate pending study.
3. **How honest to be about the CVD finding F6?** Options: (a) disclose gold/red collapse and re-scope the claim (recommended, and consistent with the repo's own review); (b) propose a palette re-tune in the paper as future work; (c) commission CVD human-subjects testing first. The maintainer's call — the spec still asserts CVD usability, so paper and spec should agree.
4. **Should the paper track the spec's DRAFT status?** v6 is marked DRAFT and several deferred items (D1–D11) remain open (parser spec, conformance vectors, numeric-precision rules). Does the paper describe v6 as shipped, or note its draft status?
5. **Author email / identity** to use on the byline (`daniel@provenant.net` vs the paper's current gmail)?
6. **Does the author want the randomart ~20–24-bit benchmark kept as the comparison anchor** given its source authors call it preliminary, or should the paper hedge harder (e.g., "even against the most favorable published estimate of randomart's perceptual entropy, entviz clears it")?
