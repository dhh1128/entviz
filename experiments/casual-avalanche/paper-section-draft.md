# Paper section draft — the casual channel and colour singletons

*Draft for integration into `docs/entviz-paper.md`, near §3.2 (the visual
avalanche) and the Figure 4b discussion. House style: plain prose, peer-review
honesty, modeled vs measured kept distinct. Numbers are from
`experiments/casual-avalanche/` (n = 100,000; seed 1). Confirm the locked-design
aggregate against the regenerated `results/RESULTS.md` before merging.*

---

## 3.x Two comparison modes, and a gap between them

A reader compares two entvizes in one of two ways. The careful reader works cell
by cell, reads the text, and checks the marks; this reader has the full
fingerprint to draw on, and almost any change betrays itself. The casual reader
glances, and a glance does not read text or count boxes — it takes in the colour
gestalt: the background, and the broad field of cell colours. entviz is built on
the promise that the glance suffices for most differences, so the glance is the
mode that matters, and it is the mode an adversary will attack.

The two modes do not have the same bandwidth, and a channel rich in one can be
empty in the other. The surround pattern is the clearest case. Each cell's ring
of boxes carries twenty-four fingerprint bits, and on a one-character change
about half of them toggle — ample signal for the careful reader. Yet the change
is nearly invisible to a glance: in Figure 4b half the boxes have moved and the
two surrounds still read as the same texture. The pattern is high-bandwidth for
careful comparison and close to silent for casual comparison.

What the glance does read — colour — turns out to be the channel that moves
least on a small change. The text and the nucleus colour are drawn from the
entropy, so they barely shift when one character does; five of six cells are
untouched. The surround colour echoes the nucleus, so it is just as still. The
one colour that could move the whole picture is the background, and the
background carries only two bits, so a one-character change leaves it unchanged
once in four. When it is unchanged, the entire colour palette is unchanged with
it, and the glance sees two pictures that match.

We measured how often this happens. Over 100,000 one-character-neighbour pairs,
scoring colour difference by CIEDE2000 and counting a pair as casually
indistinguishable when no colour patch and no background moved by more than a
glance threshold, **27.1%** of the pairs in the background-unchanged quarter
were casually colour-identical (95% CI [26.6, 27.7]; the figure is stable from
ΔE 5 to ΔE 20). The misses concentrate in the dense, full-grid inputs that are
also the most common: within that quarter, a random UUID and its one-character
neighbour were colour-identical **61%** of the time. This is not a rare
adversarial construction; it is a structural quarter of all neighbours, and the
two-bit background is cheap for an adversary to match on purpose. (A careful
comparison still separates these pairs easily — the surround pattern, colour
bar, ellipse, blank positions, and quartile marks all change. The gap is in the
glance.)

## 3.x The colour-singleton levers

The fix is to put fingerprint signal into the channel the glance actually uses,
and to put it where the eye will find it. We colour a small, fixed handful of
cells not from their nucleus but from the fingerprint, so their hue changes on
any input change. A cell coloured against the grain of its neighbours is a
*singleton*, and a singleton of colour is found pre-attentively — in parallel,
at a glance, wherever it sits. The effect depends on rarity: a few discordant
cells pop out, but if many cells are recoloured the field becomes noise and
nothing pops. Partiality is therefore not a compromise but a requirement, and it
also lets the rule scale down gracefully to small inputs that have few cells to
spare.

Three cells carry the load. The two cells holding the first and second quartile
ftoks are already fingerprint-positioned check cells, and they move with the
fingerprint, so a recolour there changes both a hue and a location. The top-left
cell is fixed, because in left-to-right reading it is where the eye lands first.
For inputs that carry blank cells — and only the larger or mid-sized inputs do —
we also fill the blanks from the fingerprint; the blanks were already
fingerprint-positioned but nearly invisible as empty outlines, and a fill makes
that motion legible. The small inputs that have exactly one blank are a special
case, because that blank is the one bearing the min/max markers; we colour it
when it is the only blank (recolouring the markers to keep them legible, which
is safe because their max/min meaning is carried by shape, not hue) and leave it
as a plain anchor when other blanks are present to carry the colour.

Measured against the same set of pairs, the quartile recolour alone takes the
background-unchanged quarter from a quarter of neighbours to under one percent;
with the top-left and blank rules together the figure is **0.40%** (95% CI
[0.28, 0.57]), and every input type falls to two percent or below. The per-type picture shows the division of labour plainly: the
quartile rule is what rescues the full-grid inputs that have no blanks (UUID and
hex-128 fall from 61% to roughly 2%), while the blank fill is what rescues the
small inputs that do (a Legal Entity Identifier falls from 9.8% to about 0.3%).

Two honesties are worth stating. First, these levers buy *casual salience*, not
collision resistance: the careful-comparison channels are unchanged, and the few
bits the levers spend are already spent elsewhere. Their job is to move a
difference the careful reader would have caught anyway into the channel a glance
can catch. Second, the claim that rarity preserves pop-out, and that recolouring
a handful of cells helps while recolouring many would hurt, is a perceptual
argument drawn from the feature-search literature; the miss rates above are
measured, but the pop-out account of *why* they fall is modelled, and a human
study would be needed to confirm it. It is for the same reason that we leave the
four fingerprint cells of a large entviz uncoloured: they read as deliberately
neutral, they already avalanche in their text, and on a crowded grid they are
part of the coherent field a singleton needs in order to stand out.
