"""entviz — visualize high-entropy values as comparable SVG diagrams.

Two independent version axes live here:

* ``SPEC_VERSION`` — which algorithm/spec revision the rendered output
  conforms to (see ``docs/spec.md``'s "Version:" line). Stamped onto every
  SVG as ``data-entviz-version`` and shown in the gallery title. Bump it
  only when the spec/algorithm changes.

* ``__version__`` — the library/package version (PEP 440 semver). This is
  the SINGLE SOURCE OF TRUTH for the package version: ``pyproject.toml``
  declares ``dynamic = ["version"]`` and hatch reads this line, so the
  version exists in exactly one place. ``scripts/release.py`` edits it.
  Stamped onto every SVG as ``data-entviz-lib``.

Versioning convention: the library's MINOR component tracks the spec major
version (spec ``v5`` → lib ``0.5.x``); a spec bump to ``v6`` means the next
release is ``0.6.0``. PATCH covers library-only changes within a spec
version. See AGENTS.md.
"""

SPEC_VERSION = "v12"
__version__ = "0.12.0"
