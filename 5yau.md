# Propagate DID-method support to 4 sister-repo ports (js, rs, java, go) after spec + python ref impl land
kind: todo
tags: did, ports
created: 2026-06-23T16:37Z

- 2026-06-23T16:37Z Gated on: docs/spec.md DID amendment + python parse_did rewrite + DID conformance vectors added to compliance/corpus. Once goldens regen, each port (entviz-js, entviz-rs, entviz-java, entviz-go — sister repos, shared branch main) must reproduce Tier A for the new DID vectors; port CIs gate Tier A only (no cairosvg). Scope: new DID-URL stripping (/,?,#), method prefix-fold binding, per-method alphabet selection, multibase-in-core. See memory entviz-did-support-plan.
