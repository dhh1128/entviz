# Entviz — project tasks

This original task list is **retired**. It tracked the v1→v2 build of the reference
implementation, which has been complete for many releases (the algorithm is now at
spec **v15**), and it described mechanisms that no longer exist (per-edge shapes,
`shape_shift`/`color_shift`, HLS text contrast). The historical list is preserved in
the git history.

For current and planned work, see:

- **[`RELEASE-TRAIN.md`](RELEASE-TRAIN.md)** — the cross-repo ordering: what has to happen,
  in what sequence, for a spec change to reach all four ports, plus the current state of the
  in-flight release and the items that block nothing. Start here when you want to know what
  is next across the family; `tick` ledgers are per-repo and cannot show you this.
- **Open issues:** <https://github.com/dhh1128/entviz/issues>
- **The `tick` task ledger** in this repo (local per-repo task tracking).
- **`docs/spec.md`** — the normative algorithm.
- **`reviews/spec-improvement-notes.md`** — the deferred spec-improvement backlog
  (the one substantive item still open is a standalone normative parser spec).
