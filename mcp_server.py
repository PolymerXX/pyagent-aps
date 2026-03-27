from mcp.server.fastmcp import FastMCP
from datetime import datetime
from e2b_code_interpreter import Sandbox
from hindsight_client import Hindsight
import json

app = FastMCP(port=8800)
hindsight = Hindsight(base_url="http://localhost:8888", timeout=60)
BANK_ID = "user-default"

@app.tool()
def get_current_time()->str:
    """Get the current time"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

@app.tool()
def execute_python(code: str) -> str:
    """
    Execute python code in e2b sandbox.
    """
    with Sandbox.create() as sandbox:
        execution = sandbox.run_code(code)
        stdout = [str(x) for x in execution.logs.stdout]
        result = {
            "text": execution.text,
            "stdout": stdout,
            "error": str(getattr(execution, "error", None)) if getattr(execution, "error", None) else None,
        }
        return json.dumps(result, ensure_ascii=False, default=str)

@app.tool()
def hindsight_retain(content: str, tags: str = "") -> str:
    """Store information to long-term memory.
    
    Args:
        content: The information to remember
        tags: Comma-separated tags (e.g., "preference,important")
    """
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    result = hindsight.retain(bank_id=BANK_ID, content=content, tags=tag_list)
    return f"Memory stored successfully (items: {result.items_count})"

@app.tool()
def hindsight_recall(query: str, budget: str = "mid") -> str:
    """Search long-term memory for relevant information.
    
    Args:
        query: Natural language search query
        budget: Search budget (low/mid/high)
    """
    result = hindsight.recall(bank_id=BANK_ID, query=query, budget=budget)
    if not result.results:
        return "No relevant memories found."
    lines = [f"{i+1}. {r.text}" for i, r in enumerate(result.results)]
    return "\n".join(lines)

@app.tool()
def hindsight_reflect(query: str) -> str:
    """Synthesize a thoughtful answer from long-term memories.
    
    Args:
        query: The question to reflect on
    """
    result = hindsight.reflect(bank_id=BANK_ID, query=query)
    return result.text or "No relevant memories found."

if __name__ == '__main__':
    app.run()