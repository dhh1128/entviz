#!/usr/bin/env python3
"""Cut an entviz release: bump version, regenerate version-stamped assets, test,
commit, tag, push.

Order matters: the bump and the asset regeneration happen BEFORE the test run,
because the gallery and the repo self-image both embed the library version. The
pre-bump tree is not the tree that gets tagged, so testing it proves nothing;
the suite runs against the exact content the tag will point at. If it fails, the
working tree is restored and nothing is committed, pushed, or tagged.

HUMAN-run by default: pushes to main and tags are reserved for a human
maintainer. An AI agent may run this script ONLY when a human has explicitly
instructed it to cut a release.

Usage:
    python3 scripts/release.py                     # patch bump, default message
    python3 scripts/release.py -m "fix overlay"    # patch bump, custom message
    python3 scripts/release.py --minor -m "spec v6" # minor bump
    python3 scripts/release.py --major -m "1.0"    # major bump
    python3 scripts/release.py --set 0.6.0 -m "..." # set an explicit version
                                                          #   (must be > current; a
                                                          #    major jump > 1 needs
                                                          #    --allow-major-jump)
    python3 scripts/release.py --no-bump            # tag the CURRENT version
                                                          #   as-is (no bump, no
                                                          #    commit) — for the first
                                                          #    release of a version
                                                          #    already on main

Self-guarding: the script establishes the right state instead of demanding you
set it up first. It refuses a dirty working tree, switches to main if you are
on another branch, and fast-forwards main to origin/main (failing only if local
main has unpushed/diverged commits a human must resolve). It is pure-stdlib and
operates on the repo root regardless of cwd, so `python3 /path/to/scripts/release.py`
works from anywhere — no `cd` needed. (`uv` must be on PATH: the script shells
out to `uv run` for the test suite and the asset regeneration. The social-card
step additionally needs the opt-in `render` group's cairosvg, which wants system
libcairo.)

The library version is single-sourced in src/entviz/__init__.py (`__version__`);
this script edits that one line and hatch derives the package version from it.

Versioning convention (see AGENTS.md / src/entviz/__init__.py): the library's
MINOR component tracks the spec major version — spec `v5` -> lib `0.5.x`. When
SPEC_VERSION bumps to `v6`, cut a --minor release so the lib lands on `0.6.0`.
This script prints a reminder if the new minor and SPEC_VERSION disagree, but
does not block (the coupling is a convention, not a hard rule).

The pushed `v<x.y.z>` tag triggers .github/workflows/release.yml, which re-runs
the tests on the tagged commit, builds the sdist + wheel with `uv build`,
publishes them to PyPI via Trusted Publishing (OIDC — no API token), and
creates a GitHub Release with the same artifacts attached.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
INIT_PY = REPO_ROOT / "src" / "entviz" / "__init__.py"
GALLERY_SCRIPT = REPO_ROOT / "scripts" / "gallery.py"
SOCIAL_CARD_SCRIPT = REPO_ROOT / "scripts" / "social_card.py"

_VERSION_RE = re.compile(r'^(__version__\s*=\s*)"([^"]+)"', re.MULTILINE)
_SPEC_RE = re.compile(r'^SPEC_VERSION\s*=\s*"v?(\d+)"', re.MULTILINE)


def run(cmd, *, capture=False, check=True):
    return subprocess.run(cmd, capture_output=capture, text=True, check=check, cwd=REPO_ROOT)


def get(cmd):
    return run(cmd, capture=True).stdout.strip()


def current_version():
    m = _VERSION_RE.search(INIT_PY.read_text())
    if not m:
        sys.exit(f"Could not find __version__ in {INIT_PY}")
    return m.group(2)


def spec_major():
    """The integer major from SPEC_VERSION (e.g. 'v5' -> 5), or None."""
    m = _SPEC_RE.search(INIT_PY.read_text())
    return int(m.group(1)) if m else None


def bump(version, part):
    major, minor, patch = (int(x) for x in version.split("."))
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def parse_explicit_version(value, current, *, allow_major_jump=False):
    """Validate an explicit --set version: shape X.Y.Z, strictly greater than
    current, and (unless --allow-major-jump) not raising the major by >1."""
    if not re.fullmatch(r"\d+\.\d+\.\d+", value):
        sys.exit(f"--set expects X.Y.Z (got {value!r}).")
    as_tuple = lambda v: tuple(int(p) for p in v.split("."))  # noqa: E731
    new, cur = as_tuple(value), as_tuple(current)
    if new <= cur:
        sys.exit(f"--set {value} is not greater than current {current}; refusing to downgrade.")
    if new[0] - cur[0] > 1 and not allow_major_jump:
        sys.exit(
            f"--set {value} raises the major version from {cur[0]} to {new[0]} "
            f"(more than one step) — almost always a typo. "
            f"If it is intentional, re-run with --allow-major-jump."
        )
    return value


def check_clean():
    if run(["git", "status", "--porcelain"], capture=True).stdout.strip():
        sys.exit("Working tree is not clean. Commit or stash changes first.")


def ensure_on_main():
    """Switch to main if we are not already there. check_clean() must run first,
    so a clean working tree guarantees the checkout cannot lose local edits."""
    branch = get(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if branch != "main":
        print(f"On {branch!r}; switching to main...")
        run(["git", "checkout", "main"])


def sync_main():
    """Fast-forward local main to origin/main so the release reflects what is
    actually published. Fails (rather than guessing) if local main has unpushed
    commits or has diverged — those need a human decision, not an auto-merge."""
    run(["git", "fetch", "--quiet", "origin"])
    local = get(["git", "rev-parse", "HEAD"])
    remote = get(["git", "rev-parse", "origin/main"])
    if local == remote:
        return
    ahead = get(["git", "rev-list", "--count", "origin/main..HEAD"])
    behind = get(["git", "rev-list", "--count", "HEAD..origin/main"])
    if ahead != "0":
        sys.exit(
            f"Local main is {ahead} commit(s) ahead of origin/main"
            + (f" and {behind} behind" if behind != "0" else "")
            + ". Push or reconcile before releasing."
        )
    print(f"Fast-forwarding main to origin/main ({behind} commit(s) behind)...")
    run(["git", "merge", "--ff-only", "origin/main"])


def check_tag_absent(tag):
    """Refuse to clobber an existing release tag (locally or on origin)."""
    if run(["git", "tag", "--list", tag], capture=True).stdout.strip():
        sys.exit(f"Tag {tag} already exists locally. Delete it or choose another version.")
    if run(["git", "ls-remote", "--tags", "origin", tag], capture=True).stdout.strip():
        sys.exit(f"Tag {tag} already exists on origin. Choose another version.")


def run_tests():
    print("Running tests (uv run pytest)...")
    run(["uv", "run", "pytest"])


def regenerate_gallery():
    """The gallery title embeds the lib version, so it must be rebuilt after a
    bump or the committed gallery's 'generated by' would lag the release."""
    print("Regenerating gallery (reflects the new version in the title)...")
    run(["uv", "run", "python", str(GALLERY_SCRIPT.relative_to(REPO_ROOT))])


def regenerate_social_card():
    """The repo self-image embeds the lib version too, on exactly the same
    footing as the gallery: docs/assets/root-commit-entviz.svg carries a
    `lib="<version>"` attribute, and tests/test_social_card.py fails if the
    committed file drifts from a fresh render. Omitting this step is what sank
    the v0.18.2 release — the tag was pushed with a card still reading 0.18.1,
    so release.yml's test gate failed and nothing was ever published.

    Needs the opt-in `render` group for cairosvg (the PNG step); without it the
    script writes both SVGs and then exits nonzero."""
    print("Regenerating repo self-image + social card (embeds the new version)...")
    run([
        "uv", "run", "--group", "render", "python",
        str(SOCIAL_CARD_SCRIPT.relative_to(REPO_ROOT)),
    ])


def set_version(new_version):
    text = INIT_PY.read_text()
    updated, n = _VERSION_RE.subn(rf'\g<1>"{new_version}"', text)
    if n != 1:
        sys.exit(f"Version substitution in {INIT_PY} affected {n} lines (expected 1).")
    INIT_PY.write_text(updated)


def warn_spec_minor_mismatch(new_version):
    sm = spec_major()
    new_minor = int(new_version.split(".")[1])
    if sm is not None and new_minor != sm:
        print(
            f"  NOTE: new minor ({new_minor}) != SPEC_VERSION major (v{sm}). "
            f"Convention is that the lib minor tracks the spec major. "
            f"If the spec changed, bump SPEC_VERSION in src/entviz/__init__.py too."
        )


def prompt_message(part):
    if not sys.stdin.isatty():
        sys.exit(f"--{part} release requires a commit message; pass -m '<message>'.")
    try:
        msg = input(f"Commit message for {part} release: ").strip()
    except (EOFError, KeyboardInterrupt):
        sys.exit("\nAborted.")
    if not msg:
        sys.exit("Commit message cannot be empty.")
    return msg


def main():
    parser = argparse.ArgumentParser(
        description="Cut a release. Defaults to --patch if no bump flag is given.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--major", dest="part", action="store_const", const="major")
    group.add_argument("--minor", dest="part", action="store_const", const="minor")
    group.add_argument("--patch", dest="part", action="store_const", const="patch")
    group.add_argument(
        "--set", dest="explicit", metavar="X.Y.Z", default=None,
        help="set an explicit version instead of bumping; must be > current",
    )
    group.add_argument(
        "--no-bump", dest="no_bump", action="store_true",
        help="release the CURRENT version as-is (no version change, no commit) — "
             "just tag HEAD and push the tag. Use for the first release of a "
             "version that is already on main (e.g. v0.5.0).",
    )
    parser.add_argument(
        "--allow-major-jump", action="store_true",
        help="permit --set to raise the major version by more than one step",
    )
    parser.add_argument("-m", dest="message", default=None, help="commit message")
    args = parser.parse_args()

    # Establish a clean, current main BEFORE reading the version, so the
    # version (and the tag, gallery stamp, and tests) reflect exactly what will
    # ship — not whatever branch you happened to be standing on.
    check_clean()
    ensure_on_main()
    sync_main()

    old = current_version()
    if args.no_bump:
        new = old
        label = "no-bump"
    elif args.explicit:
        new = parse_explicit_version(args.explicit, old, allow_major_jump=args.allow_major_jump)
        label = "set"
    else:
        label = args.part or "patch"
        new = bump(old, label)

    tag = f"v{new}"

    if args.message:
        message = args.message
    elif label == "patch":
        message = "misc fixes/enhancements"
    elif label == "no-bump":
        message = f"release {tag}"
    else:
        message = prompt_message(label)

    check_tag_absent(tag)

    if args.no_bump:
        # Nothing to bump or regenerate: the version is already on main, so we
        # only tag the current (already-pushed) HEAD and push the tag.
        print(f"Releasing current version {new} (no bump)")
        warn_spec_minor_mismatch(new)
        run_tests()
    else:
        verb = "Setting" if args.explicit else "Bumping"
        print(f"{verb} {old} -> {new}")
        # Bump and regenerate BEFORE testing. Several committed assets embed the
        # version, so the pre-bump tree is not the tree we are about to tag —
        # testing it proves nothing about the release. Test what ships.
        try:
            set_version(new)
            warn_spec_minor_mismatch(new)
            regenerate_gallery()
            regenerate_social_card()
            run_tests()
        except subprocess.CalledProcessError as exc:
            # check_clean() ran above, so every modification to these paths is
            # ours to discard. Leave main exactly as we found it rather than
            # stranding a half-bumped working tree. (Same path list as the
            # `git add` below — keep the two in step.)
            run(["git", "checkout", "--", "src/entviz/__init__.py", "docs"], check=False)
            step = " ".join(str(c) for c in exc.cmd)
            sys.exit(
                f"Release aborted: `{step}` failed on the {new} tree "
                f"(exit {exc.returncode}). Nothing was committed, tagged, or "
                f"pushed; the working tree has been restored to {old}."
            )
        run(["git", "add", "src/entviz/__init__.py", "docs"])
        # DCO sign-off (we work in DCO-enforced repos and sign every commit).
        run(["git", "commit", "-s", "-m", f"Release {tag}: {message}"])
        run(["git", "push", "origin", "main"])

    run(["git", "tag", "-a", tag, "-m", f"Release {tag}: {message}"])
    run(["git", "push", "origin", tag])

    print(f"Tagged and pushed {tag}. The release workflow will build and attach assets.")


if __name__ == "__main__":
    main()
