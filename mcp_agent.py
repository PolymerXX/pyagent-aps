import asyncio
from dotenv import load_dotenv
from pathlib import Path
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai import RunContext
_env = Path(__file__).resolve().parent / ".env"
load_dotenv(_env, override=True)

server = MCPServerStreamableHTTP('http://localhost:8800/mcp')
agent = Agent(
    'openrouter:xiaomi/mimo-v2-flash',
    instructions="""
    You are a helpful assistant that can answer questions and help with tasks.
    """,
    toolsets=[server]
)

async def main():
    response = await agent.run('What is the current time?')
    print(response.output)
    response = await agent.run("What is Evan's favorite color?")
    print(response.output)

asyncio.run(main())