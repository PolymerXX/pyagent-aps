import asyncio
from dotenv import load_dotenv
from pathlib import Path
from pydantic_ai import Agent
from pydantic_ai.models.openrouter import OpenRouterModelSettings
import asyncio
#uv run opagent.py 启动异步任务
_env = Path(__file__).resolve().parent / ".env"
load_dotenv(_env, override=True)
op_model_settings = OpenRouterModelSettings(
    temperature=0.0,
    max_tokens=10000,
    top_p=1.0,
    frequency_penalty=0.5,
    presence_penalty=0.5,
)
opagent = Agent(
    'openrouter:arcee-ai/trinity-mini:free',
    model_settings=op_model_settings,
    instructions="""
    You are a helpful assistant that can answer questions and help with tasks.
    """,
)
async def main():
    response = await opagent.run('What is the capital city of China?')
    print(response.output)

asyncio.run(main())
