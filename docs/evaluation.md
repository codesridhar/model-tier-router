# Evaluation guide

Tier labels are relative to the models an application assigns to them. A production deployment
must evaluate routing with its own tasks and quality checks.

## Build a dataset

Collect representative requests across task types, languages, input sizes, modalities, and costs
of failure. Remove secrets and personal data. For each request, run every eligible model and label
the lowest tier that meets a documented success criterion. Keep a held-out test set that is not
used for tuning rules or training a classifier.

```python
from model_router import EvaluationCase, RouteRequest, Router, Tier, evaluate

cases = [
    EvaluationCase(
        case_id="extract-001",
        request=RouteRequest(query="Extract the invoice date"),
        expected_tier=Tier.FAST,
    ),
]

report = evaluate(Router(), cases)
print(report.model_dump_json(indent=2))
```

Track exact accuracy, under-routing, over-routing, unsatisfied constraints, downstream task
success, total model cost, and end-to-end latency. Under-routing usually has a larger quality cost;
set separate release thresholds rather than optimizing accuracy alone.

## Train the optional local classifier

Install `model-tier-router[nlp]`, convert only the training split to `TrainingExample`, and inject
the resulting classifier. Re-run `evaluate()` on the untouched test split. Do not interpret raw
logistic-regression probability as calibrated operational confidence until calibration has been
measured on representative data.

Re-evaluate when model assignments, prompts, tools, user populations, or routing policy changes.

