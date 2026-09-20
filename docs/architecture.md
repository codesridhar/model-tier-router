# Architecture

## Goal

Model Tier Router selects the least capable configured model expected to complete a request. It
does not call the selected model. This boundary lets applications use any provider, gateway, tool
framework, or deployment topology.

## Decision flow

```text
RouteRequest
    │
    ├── trusted exact override ───────────────────────────────┐
    │                                                        │
    └── deterministic feature assessment                     │
             │                                               │
             ├── policy thresholds → rule tier               │
             │                                               │
             └── optional classifier → same or higher tier   │
                                                              ▼
           allowed tiers + context + capabilities → ModelRegistry
                                                              │
                                      RouteDecision ◄─────────┘
```

The classifier cannot lower the rule tier by default. The registry can move the decision upward
to the first eligible model. If no model satisfies every constraint, the result is
`unsatisfied_constraints`; the router never silently selects an incapable model.

## Extension points

- `Classifier` accepts a validated `RouteRequest` and returns `ClassifierResult`.
- `RoutingPolicy` controls thresholds, ambiguity range, downgrade behavior, and fallback tier.
- `ModelRegistry` maps abstract tiers to concrete models and capabilities.
- `evaluate()` measures a router against reviewed examples.

## Trust boundaries

`query`, `context`, and `metadata` are untrusted data. They never alter policy or model registry
configuration. `tier_override` is intended only for trusted application code; public APIs should
remove it or authorize it separately. A remote classifier is a separate data processor and must
be reviewed by the integrating application.

## Stability

The package is pre-`1.0`. Public classes exported from `model_router` form the intended API.
Modules under `model_router.features` are internal implementation details and can change between
minor versions until the first stable release.

