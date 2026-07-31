# Disposition of Paul Knowles's feedback on "Amplifying Difference"

_Prepared 2026-07-30. Target file: `docs/entviz-paper.md` (canonical; vendored to
`../papers/amp-diff.md`). Every edit below is a **proposal**, per AGENTS.md's
propose-never-silently-change rule for prose._

## Scorecard

| # | Knowles's point | Disposition |
|---|---|---|
| 1 | Casual mode is broken against a motivated adversary; say so | **Accept**, with the full range rather than one number |
| 2 | Show Table 3's derivations | **Reframe** — the real defect is two missing/stale channel rows |
| 3 | Attach the proxy caveat to the 0.33% figure | **Accept, strengthened** — report threshold, CI, and stratum |
| 4 | Human-nonce entropy is optimistic | **Accept** — arithmetically false as written |
| 5 | The 96-bit barrier binds only the careful reader | **Reject as stated** — contradicted by the spec; narrow rewrite instead |
| A | Companion paper uncited (ours) | **Accept** |
| B | Table 3 caption quotes a mismatched regime (ours) | **Accept** |
| D | Paper is behind the spec on CVD sub-floor pairs (ours) | **Accept** |
| C | Table 4 ΔL\* conflict (ours) | **Resolved — no change.** See below. |

**C, resolved.** `perception-reviewer-2026-06-08:164` claims Machado 2009 gives
protan red/blue ΔL\* = 10.5 and that 7.4 "would be the Vienot 1999 estimate."
Recomputed from the Machado severity-1.0 matrices applied in linear RGB (the
correct application, and the one `tests/test_v6_palette_lightness.py` uses):
protan red/blue **7.4**, deutan gold/red **17.2**, tritan red/blue **15.7** —
all three reproduce Table 4 exactly. The reviewer's figure matches neither the
correct application nor the gamma-space error (0.7). Table 4 stands.

---

## Edit 1 — §4.3.9: state the consequence, with the honest range

**Add** after the "Two different quantities hide inside the phrase 'how many
bits'" paragraph.

> **What that number costs an attacker.** A habituated total of *b* bits is, by
> the definition just given, a grind cost: an adversary expects to try about 2^*b*
> candidate inputs before one matches the features a habituated user checks. The
> spec already reasons this way about a single channel — the two-bit background is
> matched "in an expected ~4 candidate inputs" [8] — and the same arithmetic
> applies to the whole checked set. At the top of our estimated range, 2⁴⁰
> candidates is hours on commodity hardware; at the bottom, 2²⁰ is seconds.
>
> A companion paper measures the cost directly, grinding a certified
> reimplementation of the render model, and finds it lower than Table 3 implies
> [40]. Three regimes have to be kept apart, and we give all three because they
> disagree:
>
> - A **cheapest-subset** glance — background plus the dominant color-bar band —
>   is forged in **22 attempts**, about four bits.
> - A **one-glance gestalt**, the parallel bundle of global channels a habituated
>   reader takes in involuntarily, measures in the **low-to-mid teens** of bits;
>   a three-landmark read (background, dominant band, ellipse silhouette) is
>   about 2¹⁹, sub-second on a multicore machine.
> - The **20–40 bits** of Table 3 is the sum of the whole inventory, which
>   measures a *diligent* reader of the gestalt — not a habituated one.
>
> The spread is itself a finding, and its low end is unsettled for a reason worth
> naming. Every tolerance behind these estimates is *modeled* — drawn from the
> psychophysics literature, not measured on people — and the largest single
> modeling choice is which regime a habituated reader is in. If she is performing
> same/different *discrimination* against a reference, the thresholds are tight
> and the figures above hold. If she is instead performing *recognition* against a
> remembered gist, the literature puts the thresholds two to three times looser,
> which would pull a three-landmark read toward nine or ten bits. We take the
> discrimination reading, because the security task is detecting that a value
> differs, and because the design disavows familiarity as a goal. But that is an
> assumption, not a result — and it is the assumption the study of §6.3 would
> settle first.
>
> What does not depend on where in the range the truth falls is the conclusion.
> Under every one of these estimates, an adversary who has ground offline against
> a habituated glance wins for an affordable amount of compute. Casual
> comparison is not marginally weak against such an adversary; it is broken. It
> remains the right instruction for the honest-error case of §5, and nothing
> here touches the careful reader, whose text channel is lossless. But wherever
> an adversary is in scope, the seeded walk of §5.2 is a requirement, not an
> enhancement for high-assurance settings.

**Grounding.** `spec.md:407` (the grind-cost idiom and the "~4 candidate inputs"
quotation); `entviz-adversarial/grind/README.md` (`bg-bar` 22 attempts; `glance-3`
2^19.1, "sub-second each on a multicore box"); `m-glance` §1, §6, §11;
`review2-psychophysics:317`, `review2-hci:198–212` (the recognition argument);
`m-glance` §10 (the override, disclosed there). `threat-model.md` already places
glancing outside the trust envelope ("the user's attention during comparison —
i.e., that the user is genuinely looking, not glancing") while keeping T6 in
scope, so this edit resolves an existing tension rather than changing a position.

## Edit 2 — §5.3: stop calling the walk optional

**Replace** the final sentence of §5.3.

- **Current:** "It is a way to spend a fixed budget of attention well, not a way
  to buy security that a full reading would not already provide."
- **Proposed:** "It is a way to spend a fixed budget of attention well, not a way
  to buy security that a full reading would not already provide — but where a
  full reading is impractical *and* an adversary is in scope, it is the only one
  of the two that is on offer, and §4.3.9 is why it is then obligatory."

## Edit 3 — Table 3: two channel rows are stale

The table's channel inventory is a version behind the algorithm the same paper
describes. Two concrete defects:

**3a. The Edge color row contradicts §4.3.4.**

- **Current:** `| Edge color | — | 0 | 0 | deterministic from nucleus background |`
- **Proposed:** `| Edge color | 3 fingerprint cells × 4 | 6 | 4–6 | v10: deterministic for most cells, fingerprint-driven on three singletons |`

§4.3.4 already says: "the three fingerprint-colored singleton cells of §4.3.3,
whose edge color is drawn from the fingerprint (two bits each)." The adversarial
grinder measures the v10 color singletons at 6.7–18.9 bits depending on grid
(`FINDINGS.md`, COLOR_FIELD). Booking them at zero understates the very channel
v10 added to defend the glance.

**3b. No row exists for the v9 color-bar markers.** Add:

`| Color-bar markers | 2 × K fixed slots | 6–8 | 5–7 | discrete, always present; domain-separated digest |`

The markers are described at length in §4.3.5 but priced nowhere. `spec.md:531`:
"2 markers × ~3 bits ≈ 6 independent hard bits." Measured 6.40–8.00 across grids
(`FINDINGS.md`, difficulty curve). They are the only discrete landmark that
survives an exactly-filled grid, so their omission matters most in precisely the
case the blank-cell map vanishes.

Totals move accordingly; recompute after the rows land rather than adjusting by
hand.

## Edit 4 — Table 3 caption: reconcile the regime

- **Current:** "An internal adversarial analysis estimates roughly 220–270 bits
  careful and 25–40 bits habituated for larger inputs; we treat both as ceiling
  estimates and lean on neither."
- **Proposed:** "An internal adversarial analysis estimated roughly 220–270 bits
  careful and 25–40 bits habituated for larger inputs; that analysis has since
  been published as a companion paper [40], which reframes the habituated figure
  as a *curve* rather than a point and finds the operative one-glance value
  materially lower than this table's habituated column — which measures a
  diligent reader of the gestalt. We treat this column as a ceiling and §4.3.9
  gives the range."

**Grounding.** `m-glance:54`: "Summing the whole inventory as one figure measures
a diligent reader, not a habituated one; quoting that sum as *the* habituated
number was the mistake the exercise exists to catch."

## Edit 5 — §4.3.3: report what was actually measured

- **Current:** "Measured, the locked design takes the background-unchanged
  quarter from about a quarter to **0.33%** color-miss, and every input type
  below half a percent"
- **Proposed:** "Measured the same way, the locked design takes that
  background-unchanged quarter to **0.33%** (95% CI 0.27–0.41) color-miss, and
  holds every input type below half a percent across *all* pairs. Both figures
  are CIEDE2000 miss rates at a ΔE00 threshold of 10 — a colorimetric stand-in
  for 'clear at a glance', not a measured human miss rate; at a threshold of 20
  the baseline quarter reads 27% rather than 24%."

Also amend the "Two honesties" sentence: "while the miss rates are measured" →
"while the miss rates are measured, they are measured colorimetrically — a
CIEDE2000 threshold is a proxy for the glance, and §2.3's change-blindness and
texture-collapse results are reasons it could diverge from human performance in
either direction".

**Grounding.** `experiments/casual-avalanche/results/RESULTS.md`: header declares
"ΔE00 threshold T=10 ('clear at a glance'); Wilson 95% CI"; hybrid
background-unchanged 0.33% [0.27, 0.41]; sensitivity table baseline 21.00 / 23.67
/ 27.02% at T=5/10/20; per-type max 0.46% (hex128).

**Note on strata.** The current sentence mixes two strata without saying so —
0.33% and the "UUID ~61% → ~2%" parenthetical are the background-unchanged
quarter, while "every input type below half a percent" is the all-pairs stratum
(per-type max 0.46%). Both claims are true; the reader cannot tell them apart.
The proposed wording fixes this by naming the stratum on each.

## Edit 6 — §5.2: the seed-entropy claim is false as written

- **Current:** "on the order of log₂ C(*K*, *L*) bits, about fourteen for the
  worked example, which two pooled human nonces reach comfortably. Past that
  threshold its length stops mattering…"
- **Proposed:**

> …on the order of log₂ C(*K*, *L*) bits — 13.9 for the worked example. Two
> pooled human nonces do **not** comfortably reach that. "A digit or two" from
> each party is two to four digits, and four *uniform* decimal digits carry
> 13.29 bits — short of the requirement before any human factor is considered.
> Digit preference makes the effective figure lower still, and an attacker models
> it. The shortfall has a hard consequence: with an *s*-bit seed at most 2^*s*
> check-sets are reachable, and since every reachable set of *L* items lies
> inside some matched set of *J* > *L*, an attacker who knows the (public)
> seed-to-checklist map can always choose *J* so that survival is at least 2^−*s*
> — regardless of the combinatorics. Two one-digit nonces cap the worked
> example's "once in twenty-five hundred" at **once in ninety-seven**. Nor does
> the requirement behave like a cliff: convergence to the C(*J*,*L*)/C(*K*,*L*)
> bound is gradual, so a seed at exactly the threshold still runs several times
> worse than the bound suggests.
>
> The remedy is more entropy, not a cleverer derivation — stretching a short seed
> through a KDF realizes no additional orderings. Three digits from each party
> (19.9 bits nominal, and comfortably past 13.9 even at a pessimistic two and a
> half bits per human-chosen digit) costs a party one extra spoken syllable and
> clears the bound. Where the ceremony can afford a physical randomizer — dice,
> or a device-generated nonce — that is strictly better, at the cost of the
> no-tooling appeal the walk is otherwise designed around. A deployment that
> accepts short human nonces should state the residual explicitly rather than
> inherit the bound's optimism.

**Grounding.** log₂ C(20,5) = 13.92 (exact); 4 × log₂10 = 13.29 (exact); the
2^−*s* floor is a one-line argument requiring no simulation. The walk is a
paper-only proposal — one mention across 126 `this.i` entries (`d1scr3t3`, "the
Comparison Procedures spec section is the next design target; not yet locked"),
zero hits across the entire review corpus — so nothing downstream depends on the
current wording.

## Edit 7 — §4.3.5 / §4.3.8: the two uses of the second digest are one digest

The paper says the markers are placed "by a *second, domain-separated* digest"
(§4.3.5) and that the middle is derived from "a second digest" (§4.3.8) without
ever saying these are the *same* digest with disjoint byte ranges. **Add** to
§4.3.8, after the domain-separation bullet:

> This is the same second digest that places the color-bar markers (§4.3.5),
> which read `second[12]` and `second[13]` — disjoint from the middle cells'
> `second[0..11]`. The distinction matters for who is protected by what. The
> 96-bit middle readout binds the *text* channel, so it is evidence only for a
> reader who decodes those four cells; a habituated glance gets nothing from it.
> But the digest behind it is not careful-reader-only: on an entviz of any size
> it also surfaces as the two markers, a discrete, position-checkable landmark
> that costs an attacker a further six to eight bits and is the one such landmark
> that survives an exactly-filled grid. The asymmetry is therefore one of degree,
> not of kind.

**Why this rejects Knowles's #5 as written.** His claim — "the paper's strongest
cryptographic guarantee protects precisely the user who least needs it" — is
contradicted by `spec.md:521`, which derives the markers from "the same digest
the large-input middle cells use," computed "for **every** input." Stating it his
way would understate the design and contradict the spec.

## Edit 8 — §4.3.4: name all three sub-floor CVD pairs

The prose names only the protanopia collapse; Table 4 shows three. The spec was
already corrected (`spec.md:399`) and the gap is logged HIGH/CONFIRMED as PSY-F2
(`review-panel-2026-06-08:24`). **Replace** "We state the limit rather than hide
it. Under **protanopia**…" with a sentence that states the ΔL\* ≥ 20 design floor
and names all three pairs that miss it — protanopia red/blue at 7.4, deuteranopia
gold/red at 17.2, tritanopia red/blue at 15.7 — before giving the protanopia
argument for why no palette choice fixes the worst of them.

## Edit 9 — References: cite the companion

The paper's abstract promises "a companion paper takes up the security-relevant
habituated estimate from the adversary's side," but no such reference exists;
References stop at [39]. Meanwhile `m-glance` is published with a DOI and cites
this paper as its [1]. Add:

> [40] Hardman, D. 2026. *Measuring the Glance: An Adversary's Estimate of
> Habituated Perceptual Entropy.* Codecraft Papers.
> https://doi.org/10.2139/ssrn.6979878

Cite it at §4.3.9 (Edit 1), the Table 3 caption (Edit 4), and §6.3, where the
habituated study is named the central open problem.

---

## Edit 10 — review-provenance language (both papers)

There has been **one** human involved in this work: the author. The "reviews"
in `entviz-adversarial/reviews/` and `entviz/reviews/` are AI models prompted to
argue from a named lens — the files carry persona headers ("Reviewer lens: vision
science / psychophysics"), no name, no affiliation, no credential — produced by
this repo's own `prompts/review/` + `review-panel.js` machinery. Several published
phrasings will read to an outsider as human peer review. Ranked by how misleading:

| Site | Phrase | Problem |
|---|---|---|
| m-glance abstract, §1 | "adversarial **expert** review" | asserts credentials that do not exist |
| m-glance §1, §10, abstract | "**independent** adversarial reviews" | reads as independent *of the author*; they are independent only of each other |
| m-glance §10 | "both **reviewers'** blocking finding" | implies people |
| m-glance §10 | "a third correction — from the **design owner**" | implies the others were *not* the design owner, i.e. a cast of characters |
| m-glance §1, §10 | "we **submitted it to**" | implies sending work out to someone |
| amp-diff §6.3 | "internally adversarially **reviewed**" | ambiguous; "internally" helps, "reviewed" still implies a reviewer |

**Approach.** One honest disclosure at first mention, then the narrative shorthand
("the vision-science review judged…") is unobjectionable, because the reader now
knows what a review is here. Do *not* scrub every downstream mention — it would
wreck the prose and is not needed.

### 10a — amp-diff §6.3 (the only exposed site in this paper)

- **Current:** "the right characterization of entviz is *theoretically motivated
  and internally adversarially reviewed, but empirically untested*"
- **Proposed:** "the right characterization of entviz is *theoretically motivated,
  adversarially self-reviewed, and empirically untested*"

Preserves the self-description Knowles singled out as the paper's credibility
anchor, while removing the implication of a third party. Table 3's "internal
adversarial analysis" needs no change on this ground (it claims an analysis, not
reviewers) and is rewritten anyway by Edit 4.

### 10b — m-glance §1, the primary disclosure (currently lines 52–54)

- **Current:** "we hardened the modeling with two rounds of independent
  adversarial expert review — one general, one focused on the entviz tolerances —
  before locking the numbers"
- **Proposed:** "we hardened the modeling with two rounds of adversarial review
  before locking the numbers — one general, one focused on the entviz tolerances.
  Those reviews were conducted by AI models prompted to argue from a named lens
  (vision science; security usability), not by human domain experts; the author
  directed them and adjudicated every disagreement. They are a structured way to
  attack one's own assumptions, not independent validation."

The last clause is the load-bearing one: it tells the reader exactly how much
weight to give the reviews, which is more useful than either overstating or
hiding them.

### 10c — m-glance, remaining sites

- Abstract: "hardened by two independent adversarial reviews before numbers were
  locked" → "hardened by two adversarial AI review passes (vision-science and
  security-usability lenses), adjudicated by the author, before numbers were
  locked".
- §1 (~line 108): "we submitted it to two independent adversarial expert reviews,
  one in vision science, one in security usability" → "we ran two adversarial
  review passes over it, one in a vision-science lens, one in security usability".
- §10 opening: "We submitted the modeling to two independent adversarial reviews"
  → "We put the modeling through two adversarial review passes".
- §10: "(both reviewers' blocking finding)" → "(both passes' blocking finding)".
- §10: "a third correction — from the design owner — overrode part of it" → "a
  third correction — the author's, overriding part of it —". With one human in
  the loop, "the author" is both accurate and removes the implied cast.

### 10d — publication surfaces to re-check

The "expert review" phrase sits in m-glance's **frontmatter `abstract` and
`description`** (`papers/m-glance.md`), so it also reaches the rendered site
metadata and the SSRN abstract for DOI 10.2139/ssrn.6979878. Fixing the body
alone will not fix those. Re-vendoring updates the site; SSRN needs a manual
abstract revision.

### 10e — standing convention

Adopt one formulation and reuse it: **"adversarial review pass"** for the
artifact, **"AI reviewer persona"** when the mechanism matters, **"the author"**
for every human judgment. Never "expert", never "independent" unqualified, never
"reviewers" as a plural of people.

## Not in scope this pass

- **Table 2 JND sourcing audit.** `paper-todo.md:12-21` logs it as substantive
  and pre-submission: the numbers were inherited from the v1 paper, and the
  "area Weber fraction ≈ 0.13–0.16" originally traced to a haptic-volume study
  rather than a visual one. The citation has since been swapped to [16] Regan &
  Hamstra (a vision study), but confirming each number actually appears in the
  source it now names requires the source PDFs. Still open.
- **The LinkedIn framing note.** Not a paper edit; the paper's self-description
  is already the more careful one.

## Publication steps once edits are approved

1. Apply upstream in `docs/entviz-paper.md`; bump to v1.3, revision date
   2026-07-30.
2. Re-vendor to `../papers/amp-diff.md`; `python scripts/check_drift.py --repin`.
3. Rebuild the PDF; commit in both repos with `-s`.
