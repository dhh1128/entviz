# Propagate DID-method support to 4 sister-repo ports (js, rs, java, go) after spec + python ref impl land
kind: todo
tags: did, ports
created: 2026-06-23T16:37Z
closed: 2026-06-23T23:36Z

- 2026-06-23T16:37Z Gated on: docs/spec.md DID amendment + python parse_did rewrite + DID conformance vectors added to compliance/corpus. Once goldens regen, each port (entviz-js, entviz-rs, entviz-java, entviz-go — sister repos, shared branch main) must reproduce Tier A for the new DID vectors; port CIs gate Tier A only (no cairosvg). Scope: new DID-URL stripping (/,?,#), method prefix-fold binding, per-method alphabet selection, multibase-in-core. See memory entviz-did-support-plan.
- 2026-06-23T23:36Z DONE 2026-06-23. All 4 ports implement v11 DID/URN. entviz-rs (76/76, commit fde4cfe), entviz-go (76/76, ac5848b), entviz-java (76/76, GoldenTest +22 ids, bdd5879) committed+pushed to main. entviz-js: PR #10 (branch did-urn-v11) — adds the prefix-fold mechanism the partial port lacked; all short DID/URN vectors pass; did-peer-2/did-jwk-large fail ONLY on the pre-existing >512-bit large-input gap (not v11), to be closed when that path is ported. Each port bumped SPEC_VERSION->v11 (load-bearing: checker compares data-entviz-version) + lib 0.11.0. Publishing (crates/npm/maven/go-tag) + java-needs-JDK21 are user's release steps.
