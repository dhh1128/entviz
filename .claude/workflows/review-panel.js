export const meta = {
  name: 'entviz-review-panel',
  description: 'Multi-persona adversarial code review of the entviz repo; dedupes findings by dedupe_key and adjudicates dispositions. Self-contained — persona prompts are vendored under prompts/review/. args is an OBJECT (see whenToUse).',
  whenToUse: 'At a milestone, for a multi-lens review of entviz. Reads source read-only but WRITES its output to <target>/reviews/ (uncommitted): one synthesis file plus a per-persona report each, then returns the triaged queue + summary. ARGS (object): target = the entviz repo folder, relative ("." / "../entviz") or absolute; for a relative target also pass baseDir = the launching session absolute cwd. For "this repo"/no explicit target, the orchestrator resolves the session git root (git rev-parse --show-toplevel) and passes it as target. personas = optional array of names ("spec","perception","security","devops","architect","testability","maintainability") or prefixes ("SPEC","PSY","SEC","OPS","ARC","TST","MNT"); omit to run the DEFAULT six (spec, perception, testability, maintainability, security, devops) and name "architect" to add it; or the string "auto" to let a git-aware Scope phase pick lenses from the diff/history. Optional: branch (abort if target is not on it), milestone (run label), concurrency (default 3), promptsDir (override the vendored prompts/review/ location). Effort/model tiering: spec-conformance runs deep+Opus, perception+architect deep+Sonnet, the rest medium+Sonnet; override run-wide with effort + model, or per-persona with overrides = {PREFIX: {effort, model}}. verify ("off"|"default"|"all", default "default") runs a pre-merge pass that adversarially tries to REFUTE high-stakes findings (default = spec-conformance/security/CRITICAL; "all" = every CRITICAL+HIGH recommend-fix); refuted findings are excluded from the queue but recorded in the report.',
  phases: [
    { title: 'Preflight', detail: 'verify the target repo + branch exist (and stamp the reviewed commit) before spending on personas' },
    { title: 'Scope', detail: 'git-aware lens selection (only when personas: "auto"): map changes to lenses, skip lenses a recent review already covers' },
    { title: 'Review', detail: 'one agent per persona, unattended, chunked to respect the RAM ceiling' },
    { title: 'Verify', detail: 'adversarially refute high-stakes findings (spec-conformance/security/CRITICAL) before merge; refuted findings are excluded but recorded' },
    { title: 'Synthesize', detail: 'merge by dedupe_key (most-obligated severity wins) + executive summary' },
    { title: 'Persist', detail: 'write the synthesis + per-persona reports to <target>/reviews/' },
  ],
}

// ---- inputs ----
// args.target may be relative ("." / "../entviz") or absolute. A relative target is only unambiguous
// against an explicit base, so it requires args.baseDir = the launching session's absolute cwd.
// We never resolve a relative path against the workflow agents' ambient cwd. The preflight
// canonicalizes whatever we get to the enclosing git repo root.
if (!args || typeof args.target !== 'string' || !args.target.trim()) {
  throw new Error('review-panel requires args.target = the entviz repo folder (relative like "." / "../entviz", or absolute). For a relative target, also pass args.baseDir = the absolute directory it is relative to.')
}
const TARGET_INPUT = args.target.trim()
const BASE_DIR = args && typeof args.baseDir === 'string' ? args.baseDir.replace(/\/+$/, '') : null
const targetIsAbsolute = TARGET_INPUT.startsWith('/')
if (!targetIsAbsolute && !(BASE_DIR && BASE_DIR.startsWith('/'))) {
  throw new Error(`review-panel got a relative target "${TARGET_INPUT}" but no absolute args.baseDir to resolve it against. The orchestrator must pass baseDir = the launching repo's absolute path (the session cwd); a relative path must never resolve against the workflow agents' ambient cwd.`)
}
// Directory the preflight inspects; git resolves any ".." / subdir to the canonical repo root.
const CANDIDATE = targetIsAbsolute ? TARGET_INPUT.replace(/\/+$/, '') : `${BASE_DIR}/${TARGET_INPUT}`
const BRANCH = (args && args.branch) || null // optional; if set, the run aborts on mismatch
const milestone = (args && args.milestone) || 'review'
const CONCURRENCY = (args && args.concurrency) || 3 // self-throttle for this RAM-limited machine

// Per-persona effort/model defaults. entviz's headline claims are CORRECTNESS and PERCEPTION, so
// spec-conformance runs deep on the strongest model (its findings can invalidate every previously
// rendered entviz), perception and architect run deep on Sonnet, and the inherited defect lenses run
// cheap (medium effort, Sonnet). All OVERRIDABLE via args.effort / args.model / args.overrides.
const ALL_PERSONAS = [
  { file: 'spec-conformance-auditor.md', prefix: 'SPEC', persona: 'spec-conformance-auditor', effort: 'deep', model: 'claude-opus-4-8' },
  { file: 'perception-reviewer.md', prefix: 'PSY', persona: 'perception-reviewer', effort: 'deep', model: 'claude-sonnet-4-6' },
  { file: 'security-hawk.md', prefix: 'SEC', persona: 'security-hawk', effort: 'medium', model: 'claude-sonnet-4-6' },
  { file: 'devops-engineer.md', prefix: 'OPS', persona: 'devops-engineer', effort: 'medium', model: 'claude-sonnet-4-6' },
  { file: 'architect.md', prefix: 'ARC', persona: 'architect', effort: 'deep', model: 'claude-sonnet-4-6' },
  { file: 'testability-hawk.md', prefix: 'TST', persona: 'testability-hawk', effort: 'medium', model: 'claude-sonnet-4-6' },
  { file: 'maintainability-expert.md', prefix: 'MNT', persona: 'maintainability-expert', effort: 'medium', model: 'claude-sonnet-4-6' },
]
// Accept either prefixes (SPEC, PSY, …) or friendly names.
const NAME_TO_PREFIX = {
  spec: 'SPEC', conformance: 'SPEC', 'spec-conformance': 'SPEC', 'spec-conformance-auditor': 'SPEC', correctness: 'SPEC',
  psy: 'PSY', perception: 'PSY', psychophysics: 'PSY', 'perception-reviewer': 'PSY', ux: 'PSY',
  sec: 'SEC', security: 'SEC', 'security-hawk': 'SEC',
  ops: 'OPS', devops: 'OPS', 'devops-engineer': 'OPS',
  arc: 'ARC', architect: 'ARC', architecture: 'ARC',
  tst: 'TST', test: 'TST', testability: 'TST', 'testability-hawk': 'TST',
  mnt: 'MNT', maint: 'MNT', maintainability: 'MNT', 'maintainability-expert': 'MNT',
}
const toPrefix = (t) => NAME_TO_PREFIX[String(t).toLowerCase().trim()] || String(t).toUpperCase().trim()
const VALID_PREFIXES = new Set(ALL_PERSONAS.map((p) => p.prefix))
// Default panel when no personas are named: spec, perception, testability, maintainability, security, devops.
// Name architect explicitly via args.personas to add it.
const DEFAULT_PREFIXES = ['SPEC', 'PSY', 'TST', 'MNT', 'SEC', 'OPS']
// args.personas may be: an array of names/prefixes (mapped now); the string 'auto' (resolved later
// by the git-aware Scope phase, after preflight); or omitted (DEFAULT_PREFIXES).
const AUTO_SCOPE = args && args.personas === 'auto'
let wanted = AUTO_SCOPE ? null : (args && Array.isArray(args.personas) ? args.personas.map(toPrefix) : DEFAULT_PREFIXES)
let PERSONAS = AUTO_SCOPE ? null : ALL_PERSONAS.filter((p) => wanted.includes(p.prefix))

const FINDINGS_SCHEMA = {
  type: 'object',
  required: ['findings'],
  additionalProperties: false,
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['id', 'persona', 'title', 'severity', 'confidence', 'location', 'dedupe_key', 'recommended_disposition', 'rationale', 'fix_effort'],
        properties: {
          id: { type: 'string' },
          persona: { type: 'string' },
          title: { type: 'string' },
          severity: { enum: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] },
          confidence: { enum: ['CONFIRMED', 'LIKELY', 'SPECULATIVE'] },
          location: { type: 'string' },
          dedupe_key: { type: 'string' },
          recommended_disposition: { enum: ['recommend-fix', 'recommend-defer', 'recommend-accept-risk'] },
          rationale: { type: 'string' },
          revisit_condition: { type: ['string', 'null'] },
          fix_effort: { enum: ['small', 'medium', 'large'] },
          tier: { type: ['integer', 'null'] },
          cost_category: { type: ['string', 'null'] },
          measurement: { type: ['string', 'null'] },
        },
      },
    },
  },
}

async function runChunked(items, size, fn) {
  const out = []
  for (let i = 0; i < items.length; i += size) {
    const results = await parallel(items.slice(i, i + size).map((it) => () => fn(it)))
    out.push(...results)
  }
  return out
}

// ---- Phase 0: preflight — confirm we are about to review the RIGHT repo+branch ----
phase('Preflight')
const PREFLIGHT_SCHEMA = {
  type: 'object',
  required: ['exists', 'toplevel', 'branch', 'head_sha', 'dirty'],
  additionalProperties: false,
  properties: {
    exists: { type: 'boolean' },
    toplevel: { type: ['string', 'null'] },
    branch: { type: ['string', 'null'] },
    head_sha: { type: ['string', 'null'] },
    dirty: { type: 'boolean' },
  },
}
const pf = await agent(
  `Run exactly these against "${CANDIDATE}" and report the results — make NO edits, review nothing yet:\n` +
    `  git -C "${CANDIDATE}" rev-parse --show-toplevel\n` +
    `  git -C "${CANDIDATE}" rev-parse --abbrev-ref HEAD\n` +
    `  git -C "${CANDIDATE}" rev-parse HEAD\n` +
    `  git -C "${CANDIDATE}" status --porcelain\n` +
    `Return {exists: true/false (false if "${CANDIDATE}" does not exist or is not inside a git repo), toplevel: <absolute repo root, or null>, branch: <name or null>, head_sha: <full HEAD sha or null>, dirty: true/false (true if the status --porcelain output is non-empty)}.`,
  { label: 'preflight', phase: 'Preflight', schema: PREFLIGHT_SCHEMA },
)
if (!pf || !pf.exists || !pf.toplevel)
  return { error: `target does not resolve to a git repo: "${TARGET_INPUT}"${targetIsAbsolute ? '' : ` (relative to ${BASE_DIR})`} → ${CANDIDATE}`, preflight: pf }
// Canonical absolute repo root — a subdir or relative input auto-corrects to here. Used everywhere downstream.
const TARGET = pf.toplevel.replace(/\/+$/, '')
if (BRANCH && pf.branch !== BRANCH)
  return { error: `branch mismatch: wanted "${BRANCH}", ${TARGET} is on "${pf.branch}". Aborting rather than reviewing the wrong branch.`, preflight: pf }
const reviewedBranch = pf.branch
const reviewedSha = pf.head_sha
const dirty = pf.dirty
log(`Resolved "${TARGET_INPUT}" → ${TARGET} (branch ${reviewedBranch}, commit ${reviewedSha || 'unknown'}${dirty ? ', dirty working tree' : ''})`)
const reviewsDir = ((args && args.reviewsDir) || `${TARGET}/reviews`).replace(/\/+$/, '')
// Persona prompts are VENDORED in the entviz repo (self-contained — no external clone dependency).
// Default to <repo>/prompts/review/; overridable via args.promptsDir.
const PROMPTS_DIR = ((args && args.promptsDir) || `${TARGET}/prompts/review`).replace(/\/+$/, '')

// ---- Phase 0.5: git-aware scoping (only when args.personas === 'auto') ----
if (AUTO_SCOPE) {
  phase('Scope')
  const SCOPE_SCHEMA = {
    type: 'object',
    required: ['personas', 'skipped'],
    additionalProperties: false,
    properties: {
      personas: { type: 'array', items: { type: 'string' } },
      skipped: {
        type: 'array',
        items: {
          type: 'object',
          additionalProperties: false,
          required: ['prefix', 'reason'],
          properties: { prefix: { type: 'string' }, reason: { type: 'string' } },
        },
      },
    },
  }
  const personaCatalog = ALL_PERSONAS.map((p) => `${p.prefix} (${p.file.replace(/\.md$/, '')})`).join(', ')
  const scope = await agent(
    `TARGETING — read carefully: before anything, run \`git -C "${TARGET}" rev-parse --show-toplevel\` and confirm ` +
      `it equals "${TARGET}". If it does NOT, STOP and return {"personas":[],"skipped":[]}. Inspect ONLY "${TARGET}".\n\n` +
      `You are scoping which code-review lenses to run for this milestone of entviz. Inspect, under \`nice -n 19 ionice -c 3\`:\n` +
      `  git -C "${TARGET}" status --porcelain\n` +
      `  git -C "${TARGET}" log -5 --stat\n` +
      `  the existing reviews in "${reviewsDir}" — list it, and for each *.md read the header to note its ` +
      `reviewed commit, date, and which personas it covered.\n\n` +
      `Available lenses (prefix → file): ${personaCatalog}.\n\n` +
      `Decide which lenses to RUN. Reason from the actual diff/changes. A change to docs/spec.md, the renderer, ` +
      `fingerprint/keccak/colors, or the conformance suite almost always warrants SPEC; a change to colors, the ` +
      `palette, the renderer's visual output, or the gallery/figures warrants PSY. Recommend SKIPPING a lens ONLY ` +
      `when a recent review for it exists AND no changed file is relevant to that lens since that review's reviewed ` +
      `commit. Be CONSERVATIVE about SPEC and SEC: skip them only when there are ZERO relevant changes since their ` +
      `last review. Every skip MUST carry a human-readable reason.\n\n` +
      `Return {personas: [<prefixes to RUN>], skipped: [{prefix, reason}, ...]}. Use only these prefixes: ` +
      `${[...VALID_PREFIXES].join(', ')}.`,
    { label: 'scope', phase: 'Scope', schema: SCOPE_SCHEMA, agentType: 'Explore' },
  )
  const proposed = (scope && Array.isArray(scope.personas) ? scope.personas : []).map(toPrefix).filter((x) => VALID_PREFIXES.has(x))
  const chosen = [...new Set(proposed)]
  if (chosen.length === 0) {
    wanted = DEFAULT_PREFIXES
    log(`Scope: agent returned an empty/invalid persona set — falling back to DEFAULT_PREFIXES (${DEFAULT_PREFIXES.join(', ')})`)
  } else {
    wanted = chosen
    const skips = (scope && Array.isArray(scope.skipped) ? scope.skipped : []).map((s) => `${s.prefix}: ${s.reason}`)
    log(`Scope: running ${wanted.join(', ')}${skips.length ? `; skipped — ${skips.join(' | ')}` : ''}`)
  }
  PERSONAS = ALL_PERSONAS.filter((p) => wanted.includes(p.prefix))
}

// ---- Phase 1: fan the personas out against the verified target ----
phase('Review')
// Resolve each persona's effort + model: per-persona override (args.overrides[PREFIX]) beats a
// run-wide override (args.effort / args.model) beats the per-persona default baked into ALL_PERSONAS.
const personaPlan = PERSONAS.map((p) => {
  const eff = (args.overrides && args.overrides[p.prefix] && args.overrides[p.prefix].effort) || args.effort || p.effort
  const mdl = (args.overrides && args.overrides[p.prefix] && args.overrides[p.prefix].model) || args.model || p.model
  return { ...p, eff, mdl }
})
log(`Review plan (persona → effort/model):\n${personaPlan.map((p) => `  ${p.prefix.padEnd(4)} → ${p.eff} / ${p.mdl}`).join('\n')}`)
const perPersona = await runChunked(personaPlan, CONCURRENCY, (p) =>
  agent(
    `TARGETING — read carefully:\n` +
      `Review ONLY the repository at "${TARGET}" (branch "${reviewedBranch}"). Before reading any code, run ` +
      `\`git -C "${TARGET}" rev-parse --show-toplevel\` and confirm it equals "${TARGET}"; if it does NOT, STOP and ` +
      `return {"findings": []} with no other action. Resolve every file path under "${TARGET}" (use \`git -C "${TARGET}"\` ` +
      `or absolute paths).\n\n` +
      `Read your persona instructions from "${PROMPTS_DIR}/${p.file}" and execute them in UNATTENDED mode ` +
      `(mode: unattended, effort: ${p.eff}, run_label: "${milestone}"). Run heavy shell work — and especially anything ` +
      `that runs the renderer, the test suite, or the figure/gallery generators — under \`nice -n 19 ionice -c 3\`. ` +
      `Use id prefix "${p.prefix}-" and the dedupe_key convention in ${PROMPTS_DIR}/orchestrating-reviews.md §3. ` +
      `Write your full narrative report to the ABSOLUTE path "${reviewsDir}/${p.file.replace(/\.md$/, '')}-${milestone}.md" ` +
      `(create "${reviewsDir}" if needed; do NOT git add/commit). Then return the findings manifest as structured output.`,
    { label: `review:${p.prefix}`, phase: 'Review', schema: FINDINGS_SCHEMA, model: p.mdl },
  ).then((r) => (r && Array.isArray(r.findings) ? r.findings : [])),
)
const raw = perPersona.filter(Boolean).flat()

// ---- Phase 1.5: pipelined-intent verification — adversarially try to REFUTE high-stakes findings ----
// Gated by args.verify:
//   'off'             → skip entirely
//   'all'             → verify all CRITICAL+HIGH recommend-fix findings
//   unset | 'default' → verify spec-conformance / security findings OR any CRITICAL
const verifyMode = (args && args.verify) || 'default'
const VERIFY_SCHEMA = {
  type: 'object',
  required: ['verdict', 'note'],
  additionalProperties: false,
  properties: {
    verdict: { enum: ['confirmed', 'refuted', 'uncertain'] },
    note: { type: 'string' },
  },
}
const verifyGate = (f) => {
  if (verifyMode === 'all')
    return (f.severity === 'CRITICAL' || f.severity === 'HIGH') && f.recommended_disposition === 'recommend-fix'
  // default
  return f.persona === 'spec-conformance-auditor' || f.persona === 'security-hawk' || f.severity === 'CRITICAL'
}
let refuted = []
const verificationById = new Map()
if (verifyMode !== 'off') {
  phase('Verify')
  const toVerify = raw.filter(verifyGate)
  if (toVerify.length === 0) {
    log(`Verify (mode: ${verifyMode}): no findings matched the gate — skipping`)
  } else {
    log(`Verify (mode: ${verifyMode}): adversarially checking ${toVerify.length} of ${raw.length} findings`)
    const verifyOne = (f) => {
      // CAPABLE verifier (Opus, full agent) for spec-conformance, security, or any CRITICAL; LIGHT read-only Explore otherwise.
      const capable = f.persona === 'spec-conformance-auditor' || f.persona === 'security-hawk' || f.severity === 'CRITICAL'
      const opts = { label: `verify:${f.id}`, phase: 'Verify', schema: VERIFY_SCHEMA }
      if (capable) opts.model = 'claude-opus-4-8'
      else opts.agentType = 'Explore'
      return agent(
        `TARGETING — read carefully: before doing anything, run \`git -C "${TARGET}" rev-parse --show-toplevel\` ` +
          `and confirm it equals "${TARGET}". If it does NOT, STOP and return {"verdict":"uncertain","note":"could not confirm target repo"}. ` +
          `Review ONLY the repository at "${TARGET}". Run heavy shell work (including running the renderer or tests) under \`nice -n 19 ionice -c 3\`.\n\n` +
          `Your job is to ADVERSARIALLY attempt to REFUTE the following code-review finding by inspecting the actual code, the spec (docs/spec.md), and — where it settles the question — the rendered output. ` +
          `Do NOT try to confirm it; actively look for evidence that it is wrong, already mitigated, a false positive, or not present. For a spec-conformance claim, confirm the cited normative MUST/SHALL actually exists and that the code truly diverges.\n` +
          `Finding:\n` +
          `  id: ${f.id}\n` +
          `  title: ${f.title}\n` +
          `  location: ${f.location}\n` +
          `  severity: ${f.severity}\n` +
          `  rationale: ${f.rationale}\n\n` +
          `Return {verdict, note} where verdict is:\n` +
          `  "confirmed"  — you found concrete evidence the finding holds as stated;\n` +
          `  "refuted"    — you found concrete CONTRARY evidence (the issue is absent, already mitigated, or a false positive);\n` +
          `  "uncertain"  — you could not establish the claim either way.\n` +
          `DEFAULT to "uncertain" whenever you cannot establish the claim. Mark "refuted" ONLY with concrete contrary evidence. ` +
          `note = one line summarizing the evidence for your verdict.`,
        opts,
      )
        .then((r) => ({ id: f.id, verdict: (r && r.verdict) || 'uncertain', note: (r && r.note) || '' }))
        // A verifier that errors out or never emits its structured verdict (e.g. the subagent
        // finishes without calling StructuredOutput) must NOT crash the run — agent({schema})
        // rejects in that case, which parallel() turns into a null slot. Default to 'uncertain'
        // (the safe disposition: the finding stays in the queue, unverified) and keep the id.
        .catch(() => ({ id: f.id, verdict: 'uncertain', note: 'verifier did not return a structured verdict; defaulted to uncertain' }))
    }
    const verdicts = (await runChunked(toVerify, CONCURRENCY, verifyOne)).filter(Boolean)
    for (const v of verdicts) verificationById.set(v.id, { verdict: v.verdict, note: v.note })
    // Annotate raw findings with their verification; partition out the refuted ones.
    for (const f of raw) {
      const v = verificationById.get(f.id)
      if (v) f.verification = v
    }
    refuted = raw.filter((f) => f.verification && f.verification.verdict === 'refuted')
    const refutedIds = new Set(refuted.map((f) => f.id))
    raw.splice(0, raw.length, ...raw.filter((f) => !refutedIds.has(f.id)))
    const confirmedCount = verdicts.filter((v) => v.verdict === 'confirmed').length
    const uncertainCount = verdicts.filter((v) => v.verdict === 'uncertain').length
    log(`Verify: ${confirmedCount} confirmed, ${refuted.length} refuted (excluded), ${uncertainCount} uncertain`)
  }
}
const verificationCounts = {
  confirmed: [...verificationById.values()].filter((v) => v.verdict === 'confirmed').length,
  refuted: refuted.length,
  uncertain: [...verificationById.values()].filter((v) => v.verdict === 'uncertain').length,
}

// ---- merge by dedupe_key (plain JS) ----
const SEV_RANK = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 }
const merged = new Map()
for (const f of raw) {
  const key = f.dedupe_key
  if (!merged.has(key)) {
    merged.set(key, { ...f, reported_by: [f.persona], locations: [f.location] })
  } else {
    const m = merged.get(key)
    if (!m.reported_by.includes(f.persona)) m.reported_by.push(f.persona)
    if (!m.locations.includes(f.location)) m.locations.push(f.location)
    if (SEV_RANK[f.severity] < SEV_RANK[m.severity]) m.severity = f.severity
  }
}
const items = [...merged.values()].sort((a, b) => SEV_RANK[a.severity] - SEV_RANK[b.severity])
log(`${raw.length} raw findings from ${PERSONAS.length} personas → ${items.length} after exact-key dedupe`)

// ---- Phase 2: synthesis — executive summary + a semantic dedup pass ----
phase('Synthesize')
const SYNTHESIS_SCHEMA = {
  type: 'object',
  required: ['summary', 'duplicateGroups'],
  additionalProperties: false,
  properties: {
    summary: { type: 'string' },
    duplicateGroups: {
      type: 'array',
      description: 'Each inner array is a set of finding ids that describe the SAME underlying issue and should merge. Singletons need not be listed.',
      items: { type: 'array', items: { type: 'string' } },
    },
  },
}
const synth = await agent(
  `You are the review orchestrator for the entviz repo at ${TARGET} (branch ${reviewedBranch}), milestone "${milestone}". ` +
    `Here are ${items.length} findings, already merged by exact dedupe_key (JSON):\n${JSON.stringify(items)}\n\n` +
    `Do TWO things and return both:\n` +
    `1. "summary": a 4-6 sentence executive summary — overall posture, the milestone-blocking findings ` +
    `(CRITICAL/HIGH with recommend-fix), and the single most urgent action. Do not restate every finding.\n` +
    `2. "duplicateGroups": semantic deduplication. Independent personas often emit DIFFERENT dedupe_keys for ` +
    `the SAME underlying issue (e.g. a perception finding and a spec-conformance finding both about the surround ` +
    `channel collapsing under CVD). Judge sameness from each finding's title + location + rationale. Return an array ` +
    `of arrays of finding "id" strings, where each inner array is a set of ids describing the SAME underlying issue. ` +
    `Be CONSERVATIVE: only group findings that are genuinely the same issue. Singletons need not be listed; return [] if nothing should merge.`,
  { label: 'synthesize', phase: 'Synthesize', schema: SYNTHESIS_SCHEMA },
)
const summary = (synth && typeof synth.summary === 'string') ? synth.summary : ''
const duplicateGroups = (synth && Array.isArray(synth.duplicateGroups)) ? synth.duplicateGroups : []

// ---- apply the semantic merges (plain JS) → reconciled ----
const byId = new Map(items.map((f) => [f.id, f]))
const consumed = new Set()
const canonicalReplacing = new Map()
const droppedIds = new Set()
let semanticMerged = 0
for (const group of duplicateGroups) {
  const seen = new Set()
  const members = []
  for (const id of Array.isArray(group) ? group : []) {
    if (!byId.has(id) || consumed.has(id) || seen.has(id)) continue
    seen.add(id)
    members.push(byId.get(id))
  }
  if (members.length < 2) continue
  const canonical = members.reduce((best, m) =>
    SEV_RANK[m.severity] < SEV_RANK[best.severity] ? m : best, members[0])
  const reportedBy = [...canonical.reported_by]
  const locations = [...canonical.locations]
  for (const m of members) {
    consumed.add(m.id)
    if (m === canonical) continue
    for (const p of m.reported_by) if (!reportedBy.includes(p)) reportedBy.push(p)
    for (const loc of m.locations) if (!locations.includes(loc)) locations.push(loc)
    droppedIds.add(m.id)
    semanticMerged++
  }
  canonicalReplacing.set(canonical.id, { ...canonical, reported_by: reportedBy, locations })
}
const reconciled = items
  .filter((f) => !droppedIds.has(f.id))
  .map((f) => canonicalReplacing.get(f.id) || f)
  .sort((a, b) => SEV_RANK[a.severity] - SEV_RANK[b.severity])
log(`semantic dedup pass merged ${semanticMerged} finding(s) → ${reconciled.length} reconciled findings`)

const blockers = reconciled.filter((i) => (i.severity === 'CRITICAL' || i.severity === 'HIGH') && i.recommended_disposition === 'recommend-fix')

// ---- Phase 3: persist the synthesis to the target repo's reviews/ (durable + greppable) ----
phase('Persist')
const personaFiles = PERSONAS.map((p) => `${p.file.replace(/\.md$/, '')}-${milestone}.md`)
const PERSIST_SCHEMA = { type: 'object', required: ['path'], additionalProperties: false, properties: { path: { type: 'string' } } }
const persisted = await agent(
  `Write a review-panel synthesis report, then return its path. Make NO source edits and do NOT git add/commit.\n` +
    `Create the directory "${reviewsDir}" if needed, then use the Write tool to create "${reviewsDir}/review-panel-${milestone}.md" with this structure:\n` +
    `1. A header with: target "${TARGET}", branch "${reviewedBranch}", milestone "${milestone}", today's date (get it by running: date +%F), a line "reviewed commit: ${reviewedSha || 'unknown'} (dirty working tree: ${dirty ? 'yes' : 'no'})", a line "verification: ${verificationCounts.confirmed} confirmed, ${verificationCounts.refuted} refuted, ${verificationCounts.uncertain} uncertain (verify mode: ${verifyMode})", personas reviewed (${PERSONAS.map((p) => p.prefix).join(', ')}), and counts (${raw.length} raw findings, ${reconciled.length} after dedupe, ${blockers.length} CRITICAL/HIGH recommend-fix blockers).\n` +
    `2. "## Executive summary" containing verbatim:\n${summary}\n` +
    `3. "## All findings" — a markdown table of every finding, sorted severity CRITICAL→LOW, columns: id | severity | confidence | location | disposition | effort | reported_by | title.\n` +
    `4. "## Per-persona reports" — a bullet list naming these sibling files in the same directory (a file may be absent if that persona found nothing): ${personaFiles.join(', ')}.\n` +
    `5. "## Refuted (excluded from findings)" — a markdown table of findings that adversarial verification REFUTED and that were therefore excluded from the findings above (so nothing is silently lost), columns: id | title | location | refutation note. Use exactly these rows (empty table is fine if none):\n${JSON.stringify(refuted.map((f) => ({ id: f.id, title: f.title, location: f.location, note: f.verification ? f.verification.note : '' })))}\n` +
    `6. "## Machine-readable manifest" — a fenced JSON code block (triple-backtick, language json) containing exactly this findings array so a future session can parse it without re-running:\n${JSON.stringify(reconciled)}\n` +
    `Return {path: "<the absolute path you wrote>"}.`,
  { label: 'persist', phase: 'Persist', schema: PERSIST_SCHEMA },
)
const reportPath = persisted && persisted.path ? persisted.path : `${reviewsDir}/review-panel-${milestone}.md`
log(`Synthesis report written to ${reportPath}`)

return { target: TARGET, branch: reviewedBranch, reviewedSha, dirty, milestone, reportPath, reviewsDir, personaReports: personaFiles, personaCount: PERSONAS.length, rawCount: raw.length, blockerCount: blockers.length, items: reconciled, summary, verification: verificationCounts, refuted }
