---
name: hindsight-memory
description: >
  Add persistent memory to Pydantic AI agents using Hindsight. Use when the user
  mentions Hindsight, wants agent memory, long-term memory, or persistent context
  across conversations.
license: MIT
compatibility: Requires Python 3.10+, pydantic-ai, hindsight-pydantic-ai
metadata:
  version: "1.0.0"
  author: vectorize
---

# Hindsight Memory for Pydantic AI Agents

Hindsight provides persistent memory for AI agents, enabling them to remember information across conversations and sessions.

## When to Use This Skill

Invoke this skill when:
- User mentions "hindsight" or "Hindsight"
- User wants agents with long-term memory
- User asks to persist information across agent runs
- User wants agents to remember user preferences or past conversations
- Code imports `hindsight_pydantic_ai` or `hindsight_client`

Do **not** use this skill for:
- General Pydantic AI usage without memory requirements
- Short-term/conversational memory (use message_history instead)
- Non-Pydantic AI frameworks

## Installation

```bash
pip install hindsight-pydantic-ai
```

## Configuration

### Local Deployment (No API Key) - Default for this project

```python
from hindsight_client import Hindsight
from hindsight_pydantic_ai import configure

# Local Hindsight server (已在 .env 中配置)
client = Hindsight(base_url="http://localhost:8888", timeout=60)

configure(
    hindsight_api_url="http://localhost:8888",
    budget="low",                  # Recall budget: low/mid/high
    max_tokens=4096,               # Max tokens for recall results
    tags=["env:prod"],             # Tags for stored memories
    recall_tags=["scope:global"],  # Tags to filter recall
    recall_tags_match="any",       # Tag match mode: any/all/any_strict/all_strict
)
```

This project already has hindsight configured in `hindsightagent.py`.

### Cloud Deployment

Set the API key via environment variable:

```bash
export HINDSIGHT_API_KEY=your-api-key
```

Or configure programmatically:

```python
from hindsight_pydantic_ai import configure

configure(
    api_key="your-api-key",
    hindsight_api_url="https://api.hindsight.vectorize.io",
    budget="mid",
    max_tokens=4096,
)
```

## Quick-Start Patterns

### Basic Agent with Memory Tools

```python
from hindsight_client import Hindsight
from hindsight_pydantic_ai import create_hindsight_tools
from pydantic_ai import Agent

# Local Hindsight server (no API key needed)
client = Hindsight(base_url="http://localhost:8888")

agent = Agent(
    "openai:gpt-4o",
    tools=create_hindsight_tools(client=client, bank_id="user-123"),
    instructions="You are a helpful assistant with memory capabilities.",
)

result = agent.run_sync("Remember that I prefer Python over JavaScript")
# Later...
result = agent.run_sync("What programming language do I prefer?")
```

### Agent with Auto-Loaded Memories in Instructions

```python
from hindsight_pydantic_ai import create_hindsight_tools, memory_instructions
from pydantic_ai import Agent

agent = Agent(
    "openai:gpt-4o",
    tools=create_hindsight_tools(client=client, bank_id="user-123"),
    instructions=[
        "You are a helpful assistant.",
        memory_instructions(
            client=client,
            bank_id="user-123",
            query="user preferences and past context",
            budget="low",
            max_results=5,
        ),
    ],
)
```

### Selective Tool Inclusion

```python
from hindsight_pydantic_ai import create_hindsight_tools

# Only include recall (search) and reflect (synthesize), not retain (store)
tools = create_hindsight_tools(
    client=client,
    bank_id="user-123",
    include_retain=False,  # Read-only agent
    include_recall=True,
    include_reflect=True,
)
```

## Available Tools

The `create_hindsight_tools()` function creates up to 3 tools:

| Tool | Description |
|------|-------------|
| `hindsight_retain` | Store information to long-term memory |
| `hindsight_recall` | Search memories, returns numbered list |
| `hindsight_reflect` | Synthesize thoughtful answer from memories |

## Memory Instructions

The `memory_instructions()` function creates dynamic instructions that auto-load relevant memories on each run:

```python
from hindsight_pydantic_ai import memory_instructions

instructions_fn = memory_instructions(
    client=client,
    bank_id="user-123",
    query="relevant context about the user",
    budget="low",
    max_results=5,
    max_tokens=4096,
    prefix="Relevant memories:\n",
    tags=["preferences"],
    tags_match="any",
)

agent = Agent("openai:gpt-4o", instructions=[instructions_fn])
```

## Tag-Based Filtering

```python
# Store with tags
await client.aretain(
    bank_id="user-123",
    content="User prefers dark mode",
    tags=["preferences", "ui"]
)

# Recall with tag filtering
tools = create_hindsight_tools(
    client=client,
    bank_id="user-123",
    recall_tags=["preferences"],
    recall_tags_match="any",  # any/all/any_strict/all_strict
)
```

## Common Patterns

### Per-User Memory Banks

```python
def create_agent_for_user(user_id: str) -> Agent:
    bank_id = f"user-{user_id}"
    return Agent(
        "openai:gpt-4o",
        tools=create_hindsight_tools(client=client, bank_id=bank_id),
        instructions=[
            "You are a personal assistant.",
            memory_instructions(client=client, bank_id=bank_id, query="user context"),
        ],
    )
```

### Session + Long-Term Memory

```python
agent = Agent(
    "openai:gpt-4o",
    tools=create_hindsight_tools(client=client, bank_id="user-123"),
    instructions="Remember important facts for future conversations.",
)

# First conversation
result1 = agent.run_sync("My name is Alice")
# Second conversation (new session)
result2 = agent.run_sync("What's my name?")  # Agent remembers "Alice"
```

## Error Handling

```python
from hindsight_pydantic_ai import HindsightError

try:
    result = await agent.run("Remember this")
except HindsightError as e:
    print(f"Memory operation failed: {e}")
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `hindsight_api_url` | `https://api.hindsight.vectorize.io` | API endpoint |
| `api_key` | `HINDSIGHT_API_KEY` env | Authentication key |
| `budget` | `mid` | Recall budget (low/mid/high) |
| `max_tokens` | `4096` | Max tokens for recall results |
| `tags` | `None` | Default tags for retain |
| `recall_tags` | `None` | Tags to filter recall |
| `recall_tags_match` | `any` | Tag matching mode |
| `verbose` | `False` | Enable debug logging |

## Best Practices

1. **Use meaningful bank_ids**: Organize by user, session, or domain (e.g., `user-123`, `project-abc`)
2. **Tag strategically**: Apply consistent tags for filtering (e.g., `preferences`, `facts`, `decisions`)
3. **Budget appropriately**: Use `low` for instructions, `mid` for tool calls, `high` for complex queries
4. **Handle failures gracefully**: Memory errors shouldn't break the agent
5. **Combine with message_history**: Use message_history for conversation context, Hindsight for cross-session memory
