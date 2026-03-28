"""核心配置模块"""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """APS系统配置"""

    # 模型配置
    default_model: str = Field(
        default="openrouter:xiaomi/mimo-v2-flash", description="默认LLM模型"
    )
    temperature: float = Field(default=0.3, ge=0.0, le=1.0)
    max_tokens: int = Field(default=10000)
    top_p: float = Field(default=0.9)

    # 求解器配置
    default_time_limit: int = Field(default=60, description="默认求解时间限制(秒)")
    default_strategy: str = Field(default="balanced")

    # MCP配置
    mcp_server_url: str = Field(default="http://localhost:8800/mcp")
    mcp_server_port: int = Field(default=8800)

    # 数据库配置
    database_url: str | None = Field(default=None)

    # 日志配置
    log_level: str = Field(default="INFO")
    logfire_enabled: bool = Field(default=True)

    class Config:
        env_prefix = "APS_"
        env_file = ".env"
        extra = "ignore"


def get_settings() -> Settings:
    """获取配置实例"""
    return Settings()
