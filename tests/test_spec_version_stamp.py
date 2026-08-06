"""The spec document's own version declaration must track ``SPEC_VERSION``.

`docs/spec.md` opens with a `**Version: N**` line. Nothing checked it, so v16 and
v17 both bumped `SPEC_VERSION`, the change log, the prose sections and the ports
— and left the spec document itself declaring 15. The published spec is the
artifact a reader actually cites, so a stale stamp there is worse than a stale
comment: every implementer reading the docs site was told the wrong version.

Caught 2026-08-06 by an agent working on the paper vendoring, which needed to
know which spec revision the paper analyzed and found the code and the document
disagreeing.
"""
import re
from pathlib import Path

from entviz import SPEC_VERSION

SPEC = Path(__file__).resolve().parent.parent / "docs" / "spec.md"


def test_spec_document_declares_the_current_version():
    head = SPEC.read_text(encoding="utf-8").split("\n", 10)
    declared = None
    for line in head:
        m = re.fullmatch(r"\*\*Version:\s*(\d+)\*\*", line.strip())
        if m:
            declared = m.group(1)
            break
    assert declared is not None, (
        "docs/spec.md no longer opens with a '**Version: N**' line; if the stamp "
        "moved or changed shape, update this guard rather than deleting it"
    )
    assert f"v{declared}" == SPEC_VERSION, (
        f"docs/spec.md declares Version {declared} but SPEC_VERSION is "
        f"{SPEC_VERSION}. Bump the spec document's own stamp — it is what a "
        f"reader on the docs site cites."
    )


def test_the_change_log_has_a_section_for_the_current_version():
    # The other half of the same omission: a version bump with no change-log
    # entry leaves ports and readers with no statement of what changed.
    log = (SPEC.parent / "spec-change-log.md").read_text(encoding="utf-8")
    assert f"## What's new in {SPEC_VERSION}" in log, (
        f"docs/spec-change-log.md has no \"What's new in {SPEC_VERSION}\" section"
    )
