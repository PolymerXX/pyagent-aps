from dotenv import load_dotenv
from pathlib import Path
from pydantic_ai import Agent,RunContext, WebSearchTool, WebSearchUserLocation
from langfuse import get_client
from pydantic_ai.models.openrouter import OpenRouterModelSettings
from pydantic import BaseModel
from typing_extensions import TypedDict

_env = Path(__file__).resolve().parent / ".env"
load_dotenv(_env, override=True)

langfuse = get_client()
Agent.instrument_all()

settings = OpenRouterModelSettings(
    temperature=0.0,
    max_tokens=10000,
    top_p=1.0, #（核采样）
    frequency_penalty=0.5, #（频率惩罚）
    presence_penalty=0.5,   #（存在惩罚）
)

class Task(TypedDict):
    id: int
    name: str
    result: str

class ResearchPlan(BaseModel):
    tasks: list[Task]
    """Numbered tasks for research."""

ResearchAgent = Agent(
    "openrouter:arcee-ai/trinity-mini:free",
    model_settings=settings,
    instructions=
    """
    You are a **research planning assistant** decide which data sources to use based on the user's request.

    **TASK INSTRUCTIONS**Choose the correct location (A = internal knowledge base, B = public web data) based on the user's query to search, and summarize the output.
    **REQUEST** <<<Q
    "<user's query>"
    Q>>>

    **Audience** Support engineers
    **Tone** Clear and natural
    **Time Limit** 3 minutes
    **Max Summary Length** ≤ 120 words

    **Example 1**
    Input: "2023 API rate limit doc document where?"
    Chosen Location:**A**
    Outcome: Found -> provided link and excerpt(110 words).

    **Example 2**
    Input: "Latest competitor pricing for mid-tier plan?"
    Chosen Location:**B**
    Outcome: Found -> Shared three URLs with bullet summary (118 words).

    **Think silently step-by-step first** (do NOT reveal reasoning) to pick the location and craft the summary.
    **Use plain language**; emphasise next steps for the engineer.
    - Exactly **one** chosen location (A or B).
    - **If result found:** include up to **3** bullet points.
    - **IF no result in first source:** Switch to the other location once;if still none, respond "Escalate".
    """,
    builtin_tools=[WebSearchTool(
        kind='web_search',
        search_context_size="medium",
        max_uses=5)],
    output_type=ResearchPlan,
    deps_type=str,
)

ResearchAgent.to_cli_sync()
