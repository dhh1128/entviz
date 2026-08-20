"""Terminal rendering of entviz values — the pill and its whois line.

    >>> from entviz.terminal import pill, ansi
    >>> print(ansi(pill("DKxy2sgzfplyr_tgwIxS19f2OchFHtLwPWD3v4oYimBx")))

This subpackage is **not part of the entviz algorithm.** It is non-normative,
carries no conformance obligations, implies no port to the other
implementations, and is never imported by the base package — you have to ask for
it. Its design record is ``docs/terminal-pill.md``; the entviz spec
(``docs/spec.md``) says nothing about any of it and wins wherever they appear to
disagree about the visualization itself.

Note that it therefore does *not* follow the library's versioning convention,
where the MINOR component tracks the spec's major version. Nothing here is
bound to a spec version, and a change to this API says nothing about the
algorithm.
"""
from .pill import (BAR, BAR_ALPHABET, CELL, EIGHTHS, GAP, NO_CELLS, SEPARATOR,
                   Pill, Span, ansi, pill, whois)

__all__ = [
    "BAR", "BAR_ALPHABET", "CELL", "EIGHTHS", "GAP", "NO_CELLS", "SEPARATOR",
    "Pill", "Span", "ansi", "pill", "whois",
]
