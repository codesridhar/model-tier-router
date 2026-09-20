# Model Tier Router

`model-tier-router` is a typed, provider-independent Python library that selects the least capable
configured model expected to complete a request. It returns `fast`, `medium`, `high`, or `max`, a
concrete application model ID, and reason codes that explain the decision.

The library does not invoke models or transmit query data. Applications keep control of provider
SDKs, credentials, execution, retries, and observability.

> **Project status:** pre-`1.0`. The API is suitable for evaluation and early production adoption,
> but routing quality must be validated against your models and workload before serving users.

## Installation

```bash
python -m pip install model-tier-router
```

Optional features are installed separately:

```bash
python -m pip install 'model-tier-router[nlp]'   # local trainable classifier
python -m pip install 'model-tier-router[demo]'  # interactive testing app
```

Python 3.10 through 3.13 are supported.

## Quick start

```python
from model_router import ModelRegistry, ModelSpec, RouteRequest, Router, TaskType, Tier

registry = ModelRegistry(
    [
        ModelSpec(model_id="app-fast", tier=Tier.FAST, context_window=16_000),
        ModelSpec(model_id="app-medium", tier=Tier.MEDIUM, context_window=64_000),
        ModelSpec(
            model_id="app-high",
            tier=Tier.HIGH,
            context_window=128_000,
            capabilities={"text", "vision"},
        ),
        ModelSpec(
            model_id="app-max",
            tier=Tier.MAX,
            context_window=256_000,
            capabilities={"text", "vision", "audio"},
        ),
    ]
)

router = Router(model_registry=registry)
decision = router.route(
    RouteRequest(
        query="Investigate this deadlock across three services",
        task_type=TaskType.CODING,
    )
)

print(decision.tier)  # Tier.HIGH
print(decision.model_id)  # app-high
print(decision.rule_score)  # 8
print(decision.reason_codes)  # explainable routing signals
```

The default registry maps tiers to placeholder IDs with unknown context capacity. It is convenient
for basic experiments; production applications should always provide explicit model metadata.

## How routing works

The dependency-free baseline combines validated application context with transparent heuristics:

- Task type and cost of failure.
- Reasoning and specialized-complexity signals.
- Explicit multi-component and multi-requirement requests.
- Code context and input size.
- Allowed tiers, model capabilities, and context capacity.

| Rule score | Default tier | Intended workload |
| ---: | --- | --- |
| `0–1` | `fast` | Bounded transformations, extraction, and simple questions |
| `2–4` | `medium` | Routine synthesis and modest multi-step reasoning |
| `5–8` | `high` | Complex analysis, debugging, and interacting constraints |
| `9+` | `max` | Exceptional complexity or critical tasks with many constraints |

Heuristics are a transparent baseline, not a universal measure of difficulty. Wording, language,
domain, and the capabilities of the configured models all affect the correct tier. Do not add a
keyword and assume routing quality improved; measure it with representative labeled requests.

The registry chooses the lowest allowed model at or above the required tier that satisfies every
capability and context constraint. If none qualifies, the router returns
`unsatisfied_constraints` rather than silently using an unsuitable model.

`tier_override` is exact and has precedence over automatic routing. Treat it as privileged input;
never expose it through a public API without separate authorization.

## Trained local NLP classifier

The `nlp` extra includes a TF-IDF and balanced logistic-regression baseline. Train it on reviewed
examples from your workload where each label represents the lowest tier that passed your quality
criteria:

```python
from model_router import RouteRequest, Router, RoutingPolicy, TaskType, Tier
from model_router.classifiers import TfidfClassifier, TrainingExample

examples = [
    TrainingExample(query="Extract the invoice date", tier=Tier.FAST),
    TrainingExample(query="Classify this review", tier=Tier.FAST),
    TrainingExample(query="Write a customer email", tier=Tier.MEDIUM),
    TrainingExample(query="Summarize this report", tier=Tier.MEDIUM),
    TrainingExample(
        query="Debug a failure across several files",
        tier=Tier.HIGH,
        task_type=TaskType.CODING,
    ),
    TrainingExample(
        query="Investigate a distributed deadlock",
        tier=Tier.HIGH,
        task_type=TaskType.CODING,
    ),
    TrainingExample(query="Plan a critical region migration", tier=Tier.MAX),
    TrainingExample(query="Prove this optimization theorem", tier=Tier.MAX),
]

classifier = TfidfClassifier(examples)
router = Router(
    classifier=classifier,
    policy=RoutingPolicy(classifier_min_score=0, classifier_max_score=8),
)
decision = router.route(RouteRequest(query="Find why these services lock each other"))
```

By default, classifier output may raise but cannot lower the heuristic tier. Adapter failure uses
the configured fallback and exposes only the exception type. The core also accepts custom local,
embedding, or remote classifiers through the `Classifier` protocol. Remote adapters are
responsible for privacy controls, timeouts, and retries.

## Evaluate routing quality

```python
from model_router import EvaluationCase, RouteRequest, Router, Tier, evaluate

report = evaluate(
    Router(),
    [
        EvaluationCase(
            case_id="extract-001",
            request=RouteRequest(query="Extract the invoice date"),
            expected_tier=Tier.FAST,
        ),
    ],
)

print(report.accuracy)
print(report.under_routing_rate)
print(report.over_routing_rate)
```

See [the evaluation guide](docs/evaluation.md) for dataset construction and release criteria.

## Interactive workbench

```bash
python -m pip install 'model-tier-router[demo]'
model-router-demo
```

Open `http://127.0.0.1:8000`. The workbench displays the rule score, thresholds, selected model,
decision source, detected signals, and constraint failures. It also exposes `POST /api/route` and
interactive OpenAPI documentation at `http://127.0.0.1:8000/docs`.

A bundled dataset exercises every tier, capability escalation, overrides, and an unsatisfied
constraint:

```bash
python examples/run_test_queries.py
```

The cases are stored as editable JSON Lines in `examples/test_queries.jsonl`.

## Development

```bash
git clone <repository-url>
cd model-tier-router
python -m pip install -e '.[dev,demo,nlp]'
ruff format --check .
ruff check .
mypy src/model_router
pytest --cov=model_router --cov-report=term-missing
```

Architecture, trust boundaries, and extension points are documented in
[docs/architecture.md](docs/architecture.md). See [CONTRIBUTING.md](CONTRIBUTING.md),
[SECURITY.md](SECURITY.md), and [the release runbook](docs/releasing.md) for project processes.

## License

MIT
