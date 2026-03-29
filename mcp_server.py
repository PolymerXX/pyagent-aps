import json
import os
from datetime import datetime

import mcp_stdio_patch

mcp_stdio_patch.patch()

from mcp.server.fastmcp import FastMCP
from hindsight_client import Hindsight

from e2b_code_interpreter import Sandbox

HAS_E2B = True
app = FastMCP(port=8800)
hindsight = Hindsight(base_url="http://localhost:8888", timeout=90)
BANK_ID = "APS项目memory"


@app.tool()
def get_current_time() -> str:
    """Get the current time"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@app.tool()
def execute_python(code: str) -> str:
    """
    Execute python code in e2b sandbox.
    """
    if not HAS_E2B:
        return json.dumps({"error": "e2b sandbox not available"})
    with Sandbox.create() as sandbox:
        execution = sandbox.run_code(code)
        stdout = [str(x) for x in execution.logs.stdout]
        result = {
            "text": execution.text,
            "stdout": stdout,
            "error": (
                str(getattr(execution, "error", None))
                if getattr(execution, "error", None)
                else None
            ),
        }
        return json.dumps(result, ensure_ascii=False, default=str)


@app.tool()
async def hindsight_retain(content: str, tags: str = "") -> str:
    """Store information to long-term memory.

    Args:
        content: The information to remember
        tags: Comma-separated tags (e.g., "preference,important")
    """
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    result = await hindsight.aretain(bank_id=BANK_ID, content=content, tags=tag_list)
    return f"Memory stored successfully (items: {result.items_count})"


@app.tool()
async def hindsight_recall(query: str, budget: str = "mid") -> str:
    """Search long-term memory for relevant information.

    Args:
        query: Natural language search query
        budget: Search budget (low/mid/high)
    """
    result = await hindsight.arecall(bank_id=BANK_ID, query=query, budget=budget)
    if not result.results:
        return "No relevant memories found."
    lines = [f"{i + 1}. {r.text}" for i, r in enumerate(result.results)]
    return "\n".join(lines)


@app.tool()
async def hindsight_reflect(query: str) -> str:
    """Synthesize a thoughtful answer from long-term memories.

    Args:
        query: The question to reflect on
    """
    result = await hindsight.areflect(bank_id=BANK_ID, query=query)
    return result.text or "No relevant memories found."


if __name__ == "__main__":
    import sys

    transport = "stdio"
    if "--http" in sys.argv:
        transport = "streamable-http"
        print(f"http://localhost:8800/mcp", flush=True)
    app.run(transport=transport)
