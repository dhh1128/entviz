# No corpus vector exercises a non-default multihash hash function or a CIDv1 codec beyond dag-pb, so the 48-entry MULTIHASH_HASH_FUNCS table is uncertified in every port
kind: todo
tags: spec
created: 2026-08-11T03:21Z

- 2026-08-11T03:21Z Filed 2026-08-11, straight out of the 0.17.3 pass. Three of four ports turned out never to have implemented parse_hex_multihash at all (entviz-go since its first v10 release, entviz-java for its whole life, entviz-rs likewise; only entviz-js had it). While fixing that, all three ALSO found their multihash hash-function table truncated to ~9 of the reference's entries — just the codes the CID vectors happen to use.

WHY THIS IS ITS OWN TICK. That table feeds two consumers: the multihash label's hash-name MOD slot, and the CIDv1 multicodec decode. Neither has a corpus vector for anything off the default path — every CID vector is dag-pb/sha2-256 and the new multihash vector is sha2-256 — so all three ports 'completed' their tables with no check that they completed them CORRECTLY.

EVIDENCE THAT THIS IS NOT PARANOIA: the reference table has 48 entries. The entviz-rs agent reported it as 63 and the entviz-java agent as 42, in the same hour, both while porting it. At least one, probably both, worked from a miscount. Nothing in the corpus can currently tell us which.

WHAT WOULD CLOSE IT: vectors for (a) a multihash under a hash function that is NOT sha2-256, so the label's MOD slot actually renders a name, and (b) a CIDv1 over a non-dag-pb codec and/or a non-default hash. Mind the code/length pairing — a synthetic <code>20<32-byte digest> is not valid for a 20-byte hash like sha1, and the parser correctly declines it, which makes naive probing useless. Same shape as tick 5dzc: purely additive, no code change, patch release plus a re-pin.
- 2026-08-11T04:03Z PAID 2026-08-11 in v18, but it needed a FIX first, not just vectors. characterize() parsed the multihash hash-function name and discarded it, so qualifiers['hash'] was never set and the v14 MOD slot could never render — which is precisely why the table was uncertifiable: a vector for sha3-256 would have proved nothing, because the name never reached the model. Fixed, then four departing vectors added (multihash-sha3-256-hex, multihash-sha2-512-hex, multihash-sha1-hex, cid-v1-raw-sha3). Rationale this.i:mh4shnam.
