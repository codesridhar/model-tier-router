from model_router import ModelRegistry, ModelSpec, Router, RouteRequest, TaskType, Tier

registry = ModelRegistry(
    [
        ModelSpec(model_id="my-fast-model", tier=Tier.FAST, context_window=16_000),
        ModelSpec(model_id="my-medium-model", tier=Tier.MEDIUM, context_window=64_000),
        ModelSpec(model_id="my-high-model", tier=Tier.HIGH, context_window=128_000),
        ModelSpec(model_id="my-max-model", tier=Tier.MAX, context_window=256_000),
    ]
)
router = Router(model_registry=registry)

decision = router.route(
    RouteRequest(
        query="Investigate this deadlock across three services",
        task_type=TaskType.CODING,
    )
)
print(decision.model_dump_json(indent=2))
