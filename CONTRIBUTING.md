# Contributing

Thank you for helping improve Model Tier Router. Contributions should keep the core
provider-independent, deterministic when no classifier is configured, and free of network calls.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev,demo,nlp]'
```

Run the same checks enforced in CI:

```bash
ruff format --check .
ruff check .
mypy src/model_router
pytest --cov=model_router --cov-report=term-missing
python -m build
twine check dist/*
```

## Pull requests

- Add tests for changed behavior, especially precedence and failure cases.
- Update the README or architecture docs when public behavior changes.
- Add user-facing changes to `CHANGELOG.md` under `Unreleased`.
- Avoid adding provider SDKs to the core dependency set.
- Do not add routing keywords without a labeled example and a regression test.

API changes before `1.0` may occur between minor releases. Deprecate widely used public symbols
for at least one minor release whenever practical.

## Reporting defects

Open a GitHub issue with a minimal request, policy, registry configuration, actual result, and
expected result. Do not include credentials, personal data, or proprietary prompt content.

Please report security issues privately as described in `SECURITY.md`.

