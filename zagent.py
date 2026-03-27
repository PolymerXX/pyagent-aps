from dotenv import load_dotenv
from pathlib import Path
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings
import os
import asyncio
#uv run zagent.py 启动异步任务
_env = Path(__file__).resolve().parent / ".env"
load_dotenv(_env, override=True)
model = OpenAIChatModel(
    'glm-5-turbo',
    provider=OpenAIProvider(
        base_url=os.getenv('BIGMODEL_BASE_URL'), api_key=os.getenv('BIGMODEL_API_KEY')
    ),
)
model_settings = ModelSettings(
    temperature=0.0,
    max_tokens=10000,
    top_p=1.0,
    frequency_penalty=0.5,
    presence_penalty=0.5,
)

zagent = Agent(
    model,
    model_settings=model_settings,
    instructions="""
    You are a helpful assistant that can answer questions and help with tasks.
    """,
)

async def main():
    response = await zagent.run('What is the capital city of China?')
    print(response.output)

asyncio.run(main())