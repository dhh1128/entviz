# Corpus has no vector for three recognizer branches — EOS, hex multihash, Litecoin legacy — so every port may implement them wrongly or not at all while certifying green
kind: todo
tags: spec
created: 2026-08-10T22:24Z
closed: 2026-08-11T04:03Z

- 2026-08-10T22:25Z Filed 2026-08-10. The debt lists in tests/test_corpus_recognizer_coverage.py (UNCOVERED_FUNCTIONS, UNCOVERED_BRANCHES) are the authoritative statement; that test fails if a NEW recognizer appears without a vector, and ALSO fails if one of these gains coverage and the list is not shrunk.

WHY IT MATTERS, with precedent rather than theory. v16 added the first Cardano corpus vectors and discovered entviz-go and entviz-java had NO Cardano parser at all — a divergence that existed indefinitely and was invisible until a vector existed. The 0.17.2 pass then found the corpus has no Litecoin-legacy vector (the 'litecoin' vector is the bech32 ltc1 form), so the Go and Java agents each had to generate their own base58check fixture; neither the reference nor any port had ever been checked against another on that path. Expect filling these to surface real divergences.

COST: adding vectors changes the corpus, so it is a reference release plus a four-port re-pin pass. Deliberately NOT done as its own train — batch with the next substantive spec change. Nothing is broken meanwhile; the paths are simply untested.

SAMPLES verified against the reference: EOS 'eosio.token'; hex multihash '1220b1674191a88ec5cdd733e4240a81803105dc412d6c6708d53ab94fc248f4f553'; Litecoin legacy 'LKDyUEtTR1HXamkiEphisSiBJu6o3ZPE34' (version 0x30 over a fixed hash). Look for FURTHER branch gaps while doing it — the curated inventory covers only what has been noticed, and function-level coverage cannot see branch-level holes.
- 2026-08-11T04:03Z PAID 2026-08-11 in 0.17.3: eos-system, multihash-sha256-hex and ltc-legacy added as corpus vectors. The pass found three of four ports had never implemented parse_hex_multihash at all (entviz-go since its first v10 release; entviz-java and entviz-rs for their whole lives). entviz-js was correct. Both coverage debt lists are now empty.
