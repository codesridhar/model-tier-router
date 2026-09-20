"""Configuration and model registry."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import TIER_ORDER, ModelSpec, Tier


class RoutingPolicy(BaseModel):
    """Tunable routing thresholds and classifier behavior."""

    model_config = ConfigDict(frozen=True)

    version: str = "1.0"
    medium_threshold: int = Field(default=2, ge=0)
    high_threshold: int = Field(default=5, ge=0)
    max_threshold: int = Field(default=9, ge=0)
    classifier_enabled: bool = True
    classifier_min_score: int = Field(default=0, ge=0)
    classifier_max_score: int = Field(default=8, ge=0)
    classifier_can_downgrade: bool = False
    fallback_tier: Tier = Tier.MEDIUM

    @model_validator(mode="after")
    def thresholds_are_ordered(self) -> RoutingPolicy:
        if not self.medium_threshold < self.high_threshold < self.max_threshold:
            raise ValueError("thresholds must satisfy medium < high < max")
        if self.classifier_min_score > self.classifier_max_score:
            raise ValueError("classifier_min_score must be <= classifier_max_score")
        return self


class ModelRegistry:
    """Ordered collection of concrete models available to the application."""

    def __init__(self, models: list[ModelSpec] | tuple[ModelSpec, ...]) -> None:
        if not models:
            raise ValueError("model registry must contain at least one model")
        ids = [model.model_id for model in models]
        if len(ids) != len(set(ids)):
            raise ValueError("model_id values must be unique")
        self._models = tuple(models)

    @classmethod
    def default(cls) -> ModelRegistry:
        return cls([ModelSpec(model_id=tier.value, tier=tier) for tier in TIER_ORDER])

    def select(
        self,
        minimum_tier: Tier,
        allowed_tiers: set[Tier],
        required_capabilities: set[str],
        required_context_window: int,
        *,
        exact_tier: bool = False,
    ) -> ModelSpec | None:
        minimum_index = TIER_ORDER.index(minimum_tier)
        for tier in TIER_ORDER:
            if exact_tier and tier != minimum_tier:
                continue
            if not exact_tier and TIER_ORDER.index(tier) < minimum_index:
                continue
            if tier not in allowed_tiers:
                continue
            for model in self._models:
                if model.tier != tier:
                    continue
                if model.context_window < required_context_window:
                    continue
                if not required_capabilities.issubset(model.capabilities):
                    continue
                return model
        return None
