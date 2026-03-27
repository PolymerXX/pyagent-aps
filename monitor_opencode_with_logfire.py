import os
import sys
import time
from typing import Any, Dict, Optional

import logfire

logfire.configure()
logfire.instrument_pydantic_ai()

def monitor_opencode_execution(
    task_description: str,
    opencode_actions: Optional[Dict[str, Any]] = None,
) -> None:
    """
    监控 opencode 的执行过程，记录日志和追踪。

    Args:
        task_description: opencode 任务描述
        opencode_actions: opencode 操作记录（工具调用、文件读写等）
    """
    # 记录任务开始
    logfire.info(
        "Starting opencode execution monitoring",
        task_description=task_description,
        actions=opencode_actions,
    )

    # 模拟监控 opencode 的不同阶段
    start_time = time.time()
    logfire.info("Processing started")

    # 记录关键操作（如文件读写、命令执行等）
    if opencode_actions:
        for action_name, details in opencode_actions.items():
            logfire.info(
                "Executed action",
                action_name=action_name,
                details=details,
            )

    # 模拟延迟，代表任务执行
    time.sleep(2)
    
    # 记录任务完成
    duration = time.time() - start_time
    logfire.info(
        "Task completed successfully",
        duration_seconds=round(duration, 2),
    )


if __name__ == "__main__":
    # 模拟一个 opencode 操作记录
    sample_actions = {
        "read_file": {
            "file": "/mnt/z/pyagent/example.py",
            "operation": "read",
        },
        "edit_file": {
            "file": "/mnt/z/pyagent/example.py",
            "operation": "edit",
            "changes": "Updated function docstring",
        },
        "bash_command": {
            "command": "ls -la",
            "description": "List directory contents",
        },
    }

    # 监控 opencode 执行
    monitor_opencode_execution(
        task_description="为 opencode 集成 Logfire 监控",
        opencode_actions=sample_actions,
    )
