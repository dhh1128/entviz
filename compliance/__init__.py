"""entviz conformance suite.

A language-agnostic, three-tier checker for entviz implementations, defined
by ``docs/spec.md``'s Conformance section:

* **Tier A — render model** (:mod:`compliance.model`): recover the abstract
  render model from an SVG's normative ``data-*`` attributes + normative
  geometry, and compare it field-for-field to a golden model. Proves the
  algorithm computed the right values; localizes failures.
* **Tier B — canonical raster** (:mod:`compliance.raster`): rasterize the SVG
  with one fixed reference rasterizer and pixel-compare to a golden raster,
  excluding text-glyph regions. Proves layering / color / position / size.
* **Tier C — browser smoke**: optional, not implemented here (a headless
  browser is out of scope for the offline reference harness).

The corpus (:mod:`compliance.corpus`) is generated from the reference Python
implementation (:mod:`compliance.generate`) and run against any implementation
by :mod:`compliance.runner`.
"""

from .model import (  # noqa: F401
    extract_model, models_equal, diff_models, validate_closed_profile,
)

__all__ = [
    "extract_model", "models_equal", "diff_models", "validate_closed_profile",
]
