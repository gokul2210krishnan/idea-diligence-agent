from strands import Agent
from strands.models.gemini import GeminiModel

model = GeminiModel(
    model_id="gemini-3.6-flash",
)

agent = Agent(model=model)

response = agent("Say hello in one short sentence.")

print(response)