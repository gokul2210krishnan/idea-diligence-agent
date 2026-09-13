import sys
from pathlib import Path

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from strands import Agent
from src.model_provider import ModelRole, create_model

# Uses the project's model_provider (reads provider & model_id from .env)
model = create_model(ModelRole.ORCHESTRATOR)

agent = Agent(model=model)

response = agent("Say hello in one short sentence.")

print("Smoke test response:", response)