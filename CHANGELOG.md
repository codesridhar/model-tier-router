# Changelog

This project follows [Semantic Versioning](https://semver.org/) and records notable user-facing
changes here.

## [Unreleased]

### Added

- Provider-independent routing across `fast`, `medium`, `high`, and `max` tiers.
- Typed request, constraint, model-registry, and decision contracts.
- Explainable heuristic routing with configurable thresholds.
- Optional TF-IDF classifier with bundled generic training data and application-specific extension
  through the `nlp` extra.
- Evaluation metrics for exact, under-, over-, and unsatisfied routing.
- Interactive FastAPI testing workbench through the `demo` extra.
- CI, distribution validation, and PyPI Trusted Publishing workflow.
