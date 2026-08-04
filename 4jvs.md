# The 64 KiB input cap's stated cost model is wrong: a base58 input at the cap costs ~703 ms measured, not the ~14 ms this.i:1nputcap claims (quadratic _decoded_bytes_integer)
kind: todo
created: 2026-08-04T04:49Z

- 2026-08-04T04:50Z Measured 2026-08-03 on this repo: render() of a 64 KiB base58 string takes 703 ms (32 KiB 172 ms, 8 KiB 16 ms — quadratic). pipeline.py:59-65 documents the cap as bounding worst-case work to ~14 ms, which is only true for the paths that were measured when it was written. Unlike entviz-js F3/F9 the cap is NOT bypassable here (render() checks before any O(n) work), so this is a wrong-comment/wrong-model bug, not a DoS hole. Fix: either re-measure and correct pipeline.py + this.i:1nputcap, or compute size_bits as ceil(len * log2(base) / 8) for base58/base36/decimal instead of materializing the integer. Sibling: entviz-js tick 6p7t.
