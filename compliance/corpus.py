"""The conformance corpus: the inputs every implementation is certified against.

Two lists:

* :data:`RENDER_VECTORS` — inputs that MUST render, each producing golden Tier-A
  and Tier-B artifacts. Curated (not arbitrary) to exercise every normative
  branch: each alphabet, each grid size / aspect ratio, the blank-shift counts,
  small-grid (external-anchor) vs. large-grid ellipses, the >512-bit truncation
  path, every reference font size, the user-note caption, and the
  dash/undash + case-normalization invariants (which MUST collapse to identical
  models).
* :data:`ERROR_VECTORS` — inputs that MUST be rejected (docs/spec.md →
  Conformance → "Error conditions").

Each vector has a stable ``id`` used as the corpus directory name.
"""
from __future__ import annotations

# (id, entropy, kwargs)
RENDER_VECTORS: list[tuple[str, str, dict]] = [
    # --- hex, several sizes (4-bit alphabet, 6-char tokens) ---
    ("hex-64", "a1b2c3d4e5f6a7b8", {}),
    ("hex-128", "0123456789abcdef0123456789abcdef", {}),
    ("hex-256", "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef", {}),
    ("hex-512", "0123456789abcdef" * 8, {}),

    # --- UUID: dashed and undashed MUST produce identical models ---
    ("uuid-dashed", "550e8400-e29b-41d4-a716-446655440000", {}),
    ("uuid-undashed", "550e8400e29b41d4a716446655440000", {}),
    ("uuid-nil", "00000000-0000-0000-0000-000000000000", {}),
    ("uuid-max", "ffffffff-ffff-ffff-ffff-ffffffffffff", {}),

    # --- avalanche pairs (single-char differences) ---
    ("avalanche-a", "550e8400-e29b-41d4-a716-446655440000", {}),
    ("avalanche-b", "550e8400-e29b-41d4-a716-446655440001", {}),

    # --- Ethereum (hex; case-validated) ---
    ("eth-lower", "0x742d35cc6634c0532925a3b844bc454e4438f44e", {}),
    ("eth-checksummed", "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed", {}),

    # --- ULID / crockford32 (5-bit alphabet; case + I/L/O aliases) ---
    ("ulid-canonical", "01ARZ3NDEKTSV4RRFFQ69G5FAV", {}),
    ("ulid-lowercase", "01arz3ndektsv4rrffq69g5fav", {}),

    # --- base58 (Bitcoin legacy, Ripple) ---
    ("btc-legacy", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", {}),
    ("ripple", "rEb8TK3gBgk5auZkwc6sHnwrGVJH8DuaLh", {}),

    # --- bech32 (5-bit alphabet; HRP-named) ---
    ("btc-segwit", "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4", {}),
    ("btc-segwit-p2wsh",
     "bc1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3qccfmv3", {}),
    ("litecoin", "ltc1qhw6dgkk52v9eqzukju7vrqpw0jt4wll6e6n4q5", {}),
    ("bitcoincash", "bitcoincash:qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a", {}),
    ("cosmos", "cosmos1qqqsyqcyq5rqwzqfpg9scrgwpugpzysnrk363e", {}),

    # --- base32 (Stellar, IPFS CIDv1) ---
    ("stellar", "GCKFBEIYTKP5RDBQMUTAPDCDHF2TR4LPNRGW4JBQQTQUYZP4LDKP3SGM", {}),
    ("cid-v1", "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi", {}),

    # --- base58 IPFS CIDv0 ---
    ("cid-v0", "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG", {}),

    # --- base36 (GLEIF LEI; bound MOD 97-10 suffix) ---
    ("lei-bloomberg", "5493001KJTIIGC8Y1R12", {}),
    ("lei-lowercase", "213800wavvops85n2205", {}),

    # --- decimal (snowflake) ---
    ("snowflake-discord", "80351110224678912", {}),
    ("snowflake-19", "1234567890987654321", {}),

    # --- base64 / base64url (CESR, EOS, SSH) ---
    # v7 identity-in-core: the CESR derivation code stays in the core (cell 0
    # shows it) AND binds the fingerprint. cesr-aid-d / cesr-aid-b are the SAME
    # 43-char body under different codes (D=transferable vs B=non-transferable);
    # they MUST now differ in cell 0 text *and* every fingerprint-driven
    # channel — the swap-test "identity" case (this.i:s3mpr3fx).
    ("cesr-aid-d", "DKxy2sgzfplyr_tgwIxS19f2OchFHtLwPWD3v4oYimBx", {}),
    ("cesr-aid-b", "BKxy2sgzfplyr_tgwIxS19f2OchFHtLwPWD3v4oYimBx", {}),
    ("cesr-said-e", "EBfdlu8R27Fbx_ehrqwImnK_8Cm79sqbAQ4caaZG_LFv", {}),
    ("ssh-ed25519",
     "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDtJVH9hM+2DyhmgRZBfeIDoVqCTbXY+0nKlS5pTkkXY user@example.com",
     {}),

    # --- git-hash prefix schemes (SWHID / gitoid) ---
    # v7 prefix-fold: the object-type binds via SHA-512(prefix ‖ core).
    # swhid-rev / swhid-cnt are the SAME 40-hex body under different object
    # types (rev vs cnt); they MUST now differ in every fingerprint channel
    # (the label shows the type; the body cells still match).
    ("swhid-rev", "swh:1:rev:309cf2674ee7a0749978cf8265ab91a60aea0f7d", {}),
    ("swhid-cnt", "swh:1:cnt:309cf2674ee7a0749978cf8265ab91a60aea0f7d", {}),
    ("gitoid-blob-sha256",
     "gitoid:blob:sha256:473a0f4c3be8a93681a267e3b1e9a7dcda1185436fe141f7749120a303721813",
     {}),

    # --- arbitrary text → UTF-8 → base64url fallback ---
    ("text-hello", "hello world", {}),
    ("text-lorem", "Lorem ipsum dolor sit amet, consectetur adipiscing elit.", {}),

    # --- large inputs (>512 bits → truncated text channel) ---
    ("hex-1024", "0123456789abcdef" * 16, {}),
    ("b64-large",
     "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvkLpZUVjlW8zG3p"
     "4G7m7Q1xQfP8aZ8WUEpiE8WxC8mTLg3aN8gqK2y1zGfKbXc9p2YtNvJ5h0sX", {}),

    # --- aspect ratios on one input (grid-selection branch) ---
    ("ar-1x1", "deadbeefcafebabe1234567890abcdef0fedcba9876543210123456789abcdef", {"target_ar": 1.0}),
    ("ar-2x1", "deadbeefcafebabe1234567890abcdef0fedcba9876543210123456789abcdef", {"target_ar": 2.0}),
    ("ar-1x2", "deadbeefcafebabe1234567890abcdef0fedcba9876543210123456789abcdef", {"target_ar": 0.5}),

    # --- font sizes (geometry scaling) ---
    ("fs-6", "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08", {"font_size_pt": 6}),
    ("fs-12", "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08", {"font_size_pt": 12}),
    ("fs-24", "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08", {"font_size_pt": 24}),

    # --- user note caption (bottom strip; out of comparison surface) ---
    # The note is printable ASCII (U+0020-U+007E): spaces and punctuation are
    # valid (they used to be rejected — see the removed err-note-space/punct).
    ("note-git", "309cf2674ee7a0749978cf8265ab91a60aea0f7d", {"note": "git"}),
    ("note-space", "309cf2674ee7a0749978cf8265ab91a60aea0f7d", {"note": "two words"}),
    ("note-punct", "309cf2674ee7a0749978cf8265ab91a60aea0f7d", {"note": "a.b_c-d!"}),

    # --- DIDs (v11): method bound by prefix-fold (did:<method>: ‖ core), body
    # kept verbatim & base64url-tokenized, DID URL (/?#) dropped, case preserved,
    # no-type `did:<method>:...` label. See docs/spec.md *Decentralized
    # Identifiers* and this.i:d1dm3th0. did-web-urldrop / did-key-fragment are
    # INVARIANT_PAIRS with their bare forms (the DID URL is dropped). ---
    ("did-web", "did:web:w3c-ccg.github.io", {}),
    ("did-web-path", "did:web:w3c-ccg.github.io:user:alice", {}),        # colon segments are identity (kept)
    ("did-web-port", "did:web:example.com%3A3000:user:alice", {}),       # percent-encoding kept verbatim
    ("did-web-urldrop", "did:web:w3c-ccg.github.io/path/to/x?q=1#frag", {}),  # == did-web (URL dropped)
    ("did-key-ed25519", "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK", {}),
    ("did-key-secp256k1", "did:key:zQ3shokFTS3brHcDQrn82RUDfCZESWL1ZdCEJwekUDPQiYBme", {}),
    ("did-key-fragment",
     "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK#z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
     {}),                                                                # == did-key-ed25519 (fragment dropped)
    ("did-peer-2",
     "did:peer:2.Ez6LSt4Jscr227NFyuzKHT85haVE4AFVXm1tDwYeZ5xenxMmW.Vz6MkfvwnoNS6Cto38MEMbqdnypVDN7gS4oAMaHFkjAUse5JE",
     {}),                                                                # dotted body + purpose codes kept verbatim
    ("did-ion", "did:ion:EiClkZMDxPKqC9c-umQfTkR8vvZ9JPhl_xLDI9Nfk38w5w", {}),
    ("did-ethr-network", "did:ethr:0x5:0xf3beac30c498d9e26865f34fcaa57dbb935b0d74", {}),  # chain segment kept
    ("did-pkh", "did:pkh:eip155:1:0xb9c5714089478a327f09197987f16f9e5d936e8a", {}),       # CAIP-10 colons kept
    ("did-webvh", "did:webvh:QmQyDxVnosYTzHAMbzYDRZkVrD32ea9Sr2XNs8NkgMB5mn:domain.example", {}),
    ("did-keri", "did:keri:EBDCrJM9thBcC3hYZSzKGo-Iv53zQY9KIYEDhN0g5DnV", {}),
    ("did-prism", "did:prism:9b5118411248d9663b6ab15128fba8106511230ff654e7514cdcc4ce919bde9b", {}),
    # did:jwk body is a base64url JWK (>512 bits) → exercises the truncation
    # path together with prefix-fold.
    ("did-jwk-large",
     "did:jwk:eyJjcnYiOiJQLTI1NiIsImt0eSI6IkVDIiwieCI6ImFjYklRaXVNczNpOF91c3pFakoydHBUdFJNNEVVM3l6OTFQSDZDZEgyVjAiLCJ5IjoiX0tjeUxqOXZXTXB0bm1LdG00NkdxRHo4d2Y3NEk1TEtncmwyR3pIM25TRSJ9",
     {}),

    # --- URNs (v11, RFC 8141): NID bound by prefix-fold, NSS verbatim &
    # base64url-tokenized, r-/q-/f-components dropped, `urn:<nid>:` prefix
    # LOWERCASED (NID case-insensitive) but NSS case preserved. NSS keeps `/`
    # and ends only at `?`/`#`. urn-isbn-upper / urn-components are
    # INVARIANT_PAIRS. See docs/spec.md *Uniform Resource Names*. ---
    ("urn-isbn", "urn:isbn:0451450523", {}),
    ("urn-isbn-upper", "URN:ISBN:0451450523", {}),                       # == urn-isbn (NID case-insensitive)
    ("urn-oid", "urn:oid:2.16.840.1.113883.6.1", {}),                    # colons + dots in NSS
    ("urn-uuid", "urn:uuid:f81d4fae-7dec-11d0-a765-00a0c91e6bf6", {}),   # generic, NOT re-parsed as a bare UUID
    ("urn-nss-slash", "urn:example:a123,z456/foo", {}),                  # `/` is a legal NSS char (kept)
    ("urn-base", "urn:example:weather", {}),
    ("urn-components", "urn:example:weather?=op=map&lat=39#frag", {}),    # == urn-base (components dropped)
]

# (id, entropy, kwargs, expected_category)
# expected_category is a free-text label of WHY it's rejected; the runner only
# checks that an error is raised, not the message text.
ERROR_VECTORS: list[tuple[str, str, dict, str]] = [
    # EIP-55: mixed case that fails the checksum (first uppercase of the
    # canonical spec vector flipped to lowercase).
    ("err-eip55-bad-checksum",
     "0x5aaeb6053F3E94C9b9A09f33669435E7Ef1BeAed", {}, "eip55-checksum"),
    # user-note sanitization. The note is printable ASCII only, so the rejected
    # cases are now (a) too long, (b) a control character, (c) any non-ASCII
    # codepoint (which closes the homoglyph/bidi/zero-width surface).
    ("err-note-too-long", "a1b2c3d4e5f6a7b8", {"note": "toolongnote"}, "note-length"),
    ("err-note-control", "a1b2c3d4e5f6a7b8", {"note": "ab\tcd"}, "note-charset"),
    ("err-note-nonascii", "a1b2c3d4e5f6a7b8", {"note": "café"}, "note-charset"),
    # render params out of the reference's supported range
    ("err-fontsize-low", "a1b2c3d4e5f6a7b8", {"font_size_pt": 4}, "font-size-range"),
    ("err-fontsize-high", "a1b2c3d4e5f6a7b8", {"font_size_pt": 40}, "font-size-range"),
]


# Invariant pairs: two vector ids whose render models MUST be identical
# (case / dash normalization). The runner asserts equality beyond per-vector
# certification.
INVARIANT_PAIRS: list[tuple[str, str]] = [
    ("uuid-dashed", "uuid-undashed"),
    ("ulid-canonical", "ulid-lowercase"),
    ("avalanche-a", "uuid-dashed"),  # same input, different id → identical model
    # v11: the DID URL (path/query/fragment) is a free annotation → dropped, so
    # a DID and the same DID carrying a URL render identically.
    ("did-web", "did-web-urldrop"),
    ("did-key-ed25519", "did-key-fragment"),
    # v11: a URN's NID is case-insensitive (prefix lowercased), and its
    # r-/q-/f-components are dropped (RFC 8141 non-equivalence).
    ("urn-isbn", "urn-isbn-upper"),
    ("urn-base", "urn-components"),
]
