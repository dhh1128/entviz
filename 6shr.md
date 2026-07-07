# Entropy characterization redesign: split the conflated Parsed.type into encoding/scheme/role(closed enum)/qualifiers/size_bits + parts-with-bind (replaces prefix+prefix_semantic). Model-only + byte-identical labels first (goldens untouched); subsumes 3ek3 (entropyType = scheme??encoding). Locked design + staged plan: reviews/entropy-characterization-redesign.md; this.i:ch4rmod3l.
kind: todo
created: 2026-07-07T20:29Z

- 2026-07-07T21:40Z Pressure-tested 17 corpus cases. Model gained an EXPLICIT size_basis{decoded,utf8} field (scheme-driven; alphabet is ambiguous). CRITICAL Stage-0 gotcha: size_bits is REPORTING-ONLY and must NOT be wired to the >512-bit truncation trigger — that keeps using _core_byte_length (len(core)*bits_per_char//8), unchanged; they diverge for 65-86-char text cores and re-pointing it moves goldens. Two impl-divergence principles recorded: role from GENERIC recognizer only; bind at part-granularity. See this.i:ch4rmod3l + the note.
