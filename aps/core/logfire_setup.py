"""Logfire 初始化：按需启用 pydantic-ai 可观测性。"""

from __future__ import annotations

_configured: bool = False


def init_logfire() -> None:
    """根据 ``APS_LOGFIRE_ENABLED`` 配置 Logfire 并挂载 pydantic-ai。

    幂等：重复调用无效。无 token 时不强制上报（``send_to_logfire='if-token-present'``）。
    """
    global _configured
    if _configured:
        return

    from aps.core.config import get_settings

    if not get_settings().logfire_enabled:
        _configured = True
        return

    import logfire

    logfire.configure(send_to_logfire="if-token-present")
    logfire.instrument_pydantic_ai()
    _configured = True
