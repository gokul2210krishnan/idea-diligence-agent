from __future__ import annotations

import os
from enum import Enum

from strands.models.bedrock import BedrockModel
from strands.models.gemini import GeminiModel


class ModelRole(str, Enum):
    """Logical roles in the diligence system."""

    SAFETY_GATE = "safety_gate"
    ORCHESTRATOR = "orchestrator"
    PROBLEM = "problem"
    COMPETITION = "competition"
    ECONOMICS = "economics"
    VERDICT = "verdict"


class ModelProvider(str, Enum):
    """Supported LLM providers."""

    BEDROCK = "bedrock"
    GEMINI = "gemini"


def _get_config(role: ModelRole) -> tuple[ModelProvider, str]:
    """Resolve provider and model ID for a logical role."""

    role_name = role.value.upper()

    provider_name = (
        os.getenv(f"{role_name}_MODEL_PROVIDER")
        or os.getenv("DEFAULT_MODEL_PROVIDER")
    )

    model_id = (
        os.getenv(f"{role_name}_MODEL_ID")
        or os.getenv("DEFAULT_MODEL_ID")
    )

    if not provider_name:
        raise ValueError(
            f"No model provider configured for role '{role.value}'. "
            f"Set {role_name}_MODEL_PROVIDER or DEFAULT_MODEL_PROVIDER."
        )

    if not model_id:
        raise ValueError(
            f"No model ID configured for role '{role.value}'. "
            f"Set {role_name}_MODEL_ID or DEFAULT_MODEL_ID."
        )

    try:
        provider = ModelProvider(provider_name.lower())
    except ValueError as exc:
        raise ValueError(
            f"Unsupported model provider '{provider_name}' "
            f"for role '{role.value}'."
        ) from exc

    return provider, model_id


def create_model(role: ModelRole):
    """Create the configured Strands model for a logical role."""

    provider, model_id = _get_config(role)

    if provider == ModelProvider.GEMINI:
        return GeminiModel(model_id=model_id)

    if provider == ModelProvider.BEDROCK:
        return BedrockModel(
            model_id=model_id,
            region_name=os.getenv("AWS_REGION", "us-east-1"),
        )

    raise ValueError(f"Unsupported model provider: {provider}")