# entviz paper — open items and critique disposition

**Paper under management:** `docs/entviz-paper.md` (v6 draft; peer-review target).
**This file** is the single forward-looking tracker for that paper. It records what
is still open and the disposition of prior external review, so the raw review
inputs no longer need to live in the tree.

---

## Open items (deferred)

### 1. Audit each JND value in Table 2 against the source it is attributed to — *substantive, do before submission*
Table 2 (§2.2.2) re-points the just-noticeable-difference figures to specific
papers: length/area/aspect → Regan & Hamstra [16]; orientation → Heeley &
Buchanan-Smith [17]; luminance → Gescheider [14]; chromaticity → MacAdam [18] /
Sharma et al. [19]. The *numbers themselves* were inherited from the v1 paper,
whose originals came from **different** sources (e.g. the "area Weber fraction
0.13–0.16" traced to a haptic-volume study, not a visual one). Each number must
be confirmed to appear in — or be derivable from — the paper now cited, or the
citation swapped to one that supports it. A peer reviewer will check this.
- Both 2025-09 external critiques raised it (ChatGPT §4 "self-audit"; Gemini
  "the underlying sources must be impeccable").
- Cheapest path: pull the four cited papers, confirm each value; where a value
  isn't supported, either soften to a qualitative claim or cite the right study.

### 5. Mint an archival DOI for the algorithm/spec — *author action*
Reference [8] cites the spec at a commit-pinned GitHub URL
(`.../blob/647df30/docs/spec.md`), which is stable but not a DOI. For a
peer-reviewed venue, archive the spec/repo (e.g. Zenodo) and cite the minted DOI.
Author decision; no paper-text change until the DOI exists.

### (also open, from the drafting pass — not from the critiques)
- **Figures F-a … F-g** are placeholders with captions + render commands
  (§4.3). Generate/crops from the v6 reference implementation or the
  `docs/assets/gallery/*.svg` renders before submission. Palette figures
  (`palette-swatch.svg`, `palette-cvd.svg`) already exist.
- **Framework-citation page-check.** Citations [9]–[19], [21], [25]–[29] are
  standard works cited from knowledge; page-check before submission. One DOI to
  confirm by a manual click: **[4] ACSAC '09 `10.1109/ACSAC.2009.20`** (taken
  from cross-index agreement, not a direct IEEE-page load).

---

## Disposition of the 2025-09 external critiques

Two external reviews of the **v1** paper (ChatGPT and Gemini, 8 Sep 2025) were
triaged on 2026-06-03 against the v6 draft. Their actionable content is recorded
here; the raw files were removed (history retained in git).

**Resolved by the v6 rewrite:**
- Weber's-law formula was garbled (`IΔI=k`) → fixed to `ΔI / I = k` (§2.2.1).
- Bibliography leaned on blogs/Wikipedia/Lumen/Verywell/Khan/Hacker News/
  ResearchGate/vendor pages, duplicate Perrig & Song links, URL-only entries →
  fully replaced by 31 curated ACM-format entries with DOIs/stable sources.
- Cite Sweller for cognitive load [12]; Isola for memorability [11]; Gescheider/
  Fechner for JND [14,15]; ISO/IEC 18004 for QR [28]; Loss et al. + Tan + ACSAC
  for randomart [27,3,4], dropping blogs/HN.
- Internal `entviz-readme.pdf` citation → replaced by the spec at a pinned
  commit [8].
- Randomart's perceptual-entropy figure framed as a *preliminary* estimate
  attributed to Loss et al. [27] (the critiques themselves misattributed it to
  "Dechand/ACSAC" — not adopted).
- "Theoretical claim presented as if validated" → the v6 draft is explicitly
  hedged throughout (§1.4, §4.3.9, §5.3, §6); the habituated budget is labeled
  modeled-not-measured and the user study is named the central open problem.
- Textbook-mirroring Gestalt/Weber phrasing → rewritten in original voice.
- Verbose/passive prose flagged at length → addressed by the EB-White rewrite
  (final polish still deferred by author preference).

**Applied 2026-06-03 (this pass):**
- Added Whitten & Tygar (1999) as the canonical usable-security anchor for the
  "human bottleneck" claim [31] (§1.1).
- Softened academic tone: "catastrophic design errors" → "critical security
  errors" (§1.4); "would be a disaster" → "a critical, exploitable
  vulnerability" (§3.2).
- Labeled the perceptual-hashing / authentication-visualization taxonomy as the
  paper's own framing rather than field consensus (§3); flagged "visual
  avalanche effect" as a coined term (§3.2).

**Deferred:** the JND-value audit (item 1 above) and the archival DOI (item 5).

**Not adopted (critique errors):** their suggested citation metadata contained
mistakes — randomart figure misattributed to Dechand/ACSAC; Gemini's Tan author
list ("Komanduri, Kelley") is wrong. The v6 references use verified author lists.
