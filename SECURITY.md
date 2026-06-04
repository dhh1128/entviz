# Security Policy

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues,
discussions, or pull requests.**

Instead, report them privately through GitHub's private vulnerability reporting:

1. Go to the [**Security** tab](https://github.com/dhh1128/entviz/security) of this repository.
2. Click **Report a vulnerability** to open a private advisory draft.
3. Fill in as much detail as you can (see "What to include" below).

This routes the report directly and privately to the maintainer, who is
notified by GitHub. Your report is not visible to the public.

### What to include

A good report helps us confirm and fix the issue quickly. Where possible,
please include:

- The type of issue (e.g. injection, data exposure, auth bypass, dependency vuln).
- The affected component, file path, and/or version or commit.
- Step-by-step instructions to reproduce.
- Proof-of-concept or exploit code, if you have it.
- The impact: what an attacker could do with this.

## Our Commitment

We follow a responsible (coordinated) disclosure model:

- **Acknowledgement:** We will acknowledge your report within **3 business days**.
- **Assessment:** We will investigate and let you know whether we agree it is a
  vulnerability, and our planned course of action.
- **Fix timeline:** For issues we confirm, we aim to release a fix within
  **30 days** of acknowledgement. Complex issues may take longer; if so, we
  will keep you informed of progress.
- **Coordination:** We will coordinate the timing of public disclosure with you
  and credit you in the published advisory unless you prefer to remain anonymous.

We ask that you give us a reasonable opportunity to address the issue before
any public disclosure.

## No Bug Bounty

Entviz is a personal open-source project. **We do not offer a paid bug bounty
or any other monetary reward** for vulnerability reports. We genuinely
appreciate responsible disclosure and are happy to publicly credit reporters in
the advisory, but please report only because you want to help — not in
expectation of payment.

## Supported Versions

Entviz is pre-1.0 and ships from the `main` branch. Security fixes are applied
to `main`; there are no long-term support branches. Please ensure you are
running the latest version from `main` before reporting.
