# change label on entviz now that we have better clarity on metadata about encoding, type of entropy, etc. Then update React work.
kind: todo
created: 2026-07-09T17:45Z
closed: 2026-07-11T15:34Z

- 2026-07-11T15:34Z Fixed in spec v15 (lib 0.15.0), commit 731e8d1. The top label is now a projection with a trailing PREFIX slot echoing the stripped front prefix (ETH,0x / bech32,cosmos1 / CIDv1,dag-pb,b / SSH,...,AAAA...), the +hash large-input marker (was 'fingerprint of'), and ecdsa-p256. React/JS port updated in entviz-js commit 4ec4e43 (EntvizPill + core). Ports rs/js/java/go all at v15, 90/90 Tier A conformance. Note: commit hashes were rebased on pull of PR #33; 731e8d1 is the current v15 commit.
