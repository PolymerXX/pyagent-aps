from hindsight_pydantic_ai import configure, create_hindsight_tools
from pathlib import Path
from pydantic_ai import Agent
from dotenv import load_dotenv
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic import BaseModel
from pydantic_ai import WebSearchTool
import asyncio
from hindsight_client import Hindsight
_env = Path(__file__).resolve().parent / ".env"
load_dotenv(_env, override=True)

import logfire

logfire.configure()
logfire.instrument_pydantic_ai()

client = Hindsight(base_url="http://localhost:8888",timeout=60)
BANK_ID = "Evan-boy"
configure(
    hindsight_api_url="http://localhost:8888",
    budget="low",                  # Recall budget: low/mid/high
    max_tokens=4096,               # Max tokens for recall results
    tags=["env:prod"],             # Tags for stored memories
    recall_tags=["scope:global"],  # Tags to filter recall
    recall_tags_match="any",       # Tag match mode: any/all/any_strict/all_strict
)
MCP_SERVER = MCPServerStreamableHTTP('http://localhost:8800/mcp')

Tools = create_hindsight_tools(bank_id=BANK_ID)



async def main():
    HindsightAgent = Agent(
    "openrouter:xiaomi/mimo-v2-flash",
    toolsets=[MCP_SERVER],
    tools=Tools,
    builtin_tools=[WebSearchTool()],
    instructions= 
    """
    You are helpful Assistant who can answer user's query.
    **Task Instructions** give a summary of the output including details.
    **Audience** Support AI developer
    **Tone** Clear and natural

    **Example**
    User: what is SUZHOU foods native people like eat?
    Assistant: Suzhou people enjoy a variety of foods, with local favorites including Suzhou soup noodles, sweet and sour mandarin fish, and pan-fried buns. 
    details:
    - title: Top 10 Suzhou Foods You Should Try.
    - source: https://www.travelchinaguide.com/cityguides/jiangsu/suzhou/dining.html

    **Warning** always output in chinese.
    """,
)
    result = await HindsightAgent.run(  """
规划Evan未来10天的旅行计划，包括每天的行程，景点，交通，住宿，餐饮，费用等。
你需要各位注重Evan的个人习惯喜好等特性，给出最符合他个人习惯的旅行计划。
你还需要计算出总费用，并给出预算。
给出A，B，C三个方案并且给出每个方案的优缺点。
""")
    print(result.output)

#uv run hindsightagent.py 启动异步任务
if __name__ == "__main__":
    asyncio.run(main())