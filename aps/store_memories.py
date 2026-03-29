import json
import httpx
import sys

MEMORIES = [
    {
        "content": "APS项目技术栈: Python 3.10+, pydantic v2(BaseModel), pydantic-ai>=0.0.10(LLM Agent框架), pydantic-settings>=2.0(配置管理), OR-Tools CP-SAT>=9.8(约束求解), Streamlit>=1.30+Plotly>=5.18(Web UI/Gantt图), httpx>=0.25(HTTP客户端), websockets>=12.0, pandas>=2.0+openpyxl>=3.1(数据处理), SQLite(persistence), logfire>=3.0(可观测性), pytest>=7.0+pytest-cov+ruff>=0.1+mypy>=1.8(开发工具), python-dotenv(环境变量)",
        "tags": "APS,tech-stack,architecture",
    },
    {
        "content": "APS项目目录结构: adapters/(REST/DB/File数据适配器+parsers统一解析), agents/(8个Agent: Orchestrator/Planner/Scheduler/Validator/Adjuster/Explainer/Monitor/ExceptionHandler), core/(config.py配置/state.py全局状态/database.py SQLite/repository.py持久化/logfire_setup.py可观测), engine/(solver.py求解器/cp_sat_solver.py CP-SAT/cache.py缓存/profiler.py性能/whatif.py场景模拟/schedule_metrics.py指标), mcp/(registry.py工具注册/tools.py 14个工具), models/(order/machine/constraint/schedule/optimization/calendar 共7个模型文件), realtime/(monitor.py监控/adjuster.py调整-非LLM), ui/(app.py+5页面+components/), tests/(25个测试文件)",
        "tags": "APS,directory-structure,architecture",
    },
    {
        "content": "APS核心依赖版本: pydantic>=2.0, pydantic-ai>=0.0.10, hindsight-pydantic-ai>=0.4, pydantic-settings>=2.0, ortools>=9.8, httpx>=0.25, websockets>=12.0, streamlit>=1.30, plotly>=5.18, pandas>=2.0, openpyxl>=3.1, logfire>=3.0. Dev: pytest>=7.0, pytest-asyncio>=0.23, pytest-cov>=4.0, ruff>=0.1(line-length=100, target Python 3.10), mypy>=1.8(strict, ignore_missing_imports). Build: hatchling. License: MIT. Version: 0.1.0",
        "tags": "APS,dependencies,versions",
    },
]

BASE_URL = "http://127.0.0.1:8800/mcp"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def init_session(client):
    data = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "kilo-script", "version": "1.0"},
            },
        }
    ).encode("utf-8")

    with client.stream("POST", BASE_URL, content=data, headers=HEADERS, timeout=30) as resp:
        session_id = resp.headers.get("mcp-session-id")
        for line in resp.iter_lines():
            if line.startswith("data: "):
                result = json.loads(line[6:])
                print(f"Initialized: {result.get('result', {}).get('serverInfo')}")

    return session_id


def call_retain(client, session_id, memory, msg_id):
    headers = {**HEADERS, "mcp-session-id": session_id}
    data = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": msg_id,
            "method": "tools/call",
            "params": {
                "name": "hindsight_retain",
                "arguments": {
                    "content": memory["content"],
                    "tags": memory["tags"],
                },
            },
        }
    ).encode("utf-8")

    with client.stream("POST", BASE_URL, content=data, headers=headers, timeout=300) as resp:
        result_data = None
        for line in resp.iter_lines():
            line = line.strip()
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                if "result" in payload:
                    result_data = payload["result"]
                elif "error" in payload:
                    result_data = payload["error"]
        return result_data


def main():
    with httpx.Client() as client:
        print("Step 1: Initializing MCP session...")
        session_id = init_session(client)
        print(f"Session ID: {session_id}")

        for i, memory in enumerate(MEMORIES, 1):
            print(f"\nStep {i + 1}: Storing Memory {i} (tags: {memory['tags']})...")
            result = call_retain(client, session_id, memory, i + 10)
            if result:
                if isinstance(result, dict) and "content" in result:
                    text = result["content"][0].get("text", "")
                    is_error = result.get("isError", False)
                    status = "FAILED" if is_error else "OK"
                    print(f"  [{status}] {text}")
                else:
                    print(f"  Response: {json.dumps(result, ensure_ascii=False)}")
            else:
                print("  No response received")

        print("\nAll memories stored.")


if __name__ == "__main__":
    main()
