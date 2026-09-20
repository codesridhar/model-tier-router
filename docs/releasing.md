# Release runbook

## Prerequisites

- A public GitHub repository with branch protection enabled.
- A PyPI project or pending trusted publisher for `model-tier-router`.
- A GitHub environment named `pypi` with required-reviewer protection.
- PyPI Trusted Publishing configured for `.github/workflows/release.yml` and environment `pypi`.

## Prepare

1. Move relevant entries from `Unreleased` to a version and date in `CHANGELOG.md`.
2. Update `project.version` in `pyproject.toml` and `__version__` in `model_router/__init__.py`.
3. Run the complete CI command set from `CONTRIBUTING.md`.
4. Build distributions and inspect their contents.
5. Create a signed tag matching the version, such as `v0.1.0`.
6. Create a GitHub release from that tag.

Publishing begins only when the GitHub release is marked published. The workflow rebuilds and
tests the tagged source, checks both distributions, and passes the artifacts to a separate OIDC
publishing job. No long-lived PyPI token is stored.

## Verify

Install the exact version into a clean environment from PyPI, import `model_router`, run a basic
route, and confirm the PyPI provenance attestation. If verification fails, yank the affected file
on PyPI, document the reason, fix forward with a new version, and never reuse a released version.

