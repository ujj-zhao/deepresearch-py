"""应用配置。

使用 pydantic-settings 从环境变量或 `.env` 文件加载配置。
环境变量命名与 admin 服务（ruoyi-fastapi）保持同风格，便于 docker-compose 统一注入。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置。所有字段从 .env 读取，缺省值见默认。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # 应用
    APP_NAME: str = "deepresearch-ai"
    DEBUG: bool = True

    # Postgres（P3 RAG 阶段启用 pgvector 扩展）
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "deepresearch"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "deepresearch"

    # Redis（与 admin 共享实例，用独立 db 号隔离：admin 用 0，AI 用 1）
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 1
    REDIS_PASSWORD: str = ""

    # JWT：与 admin 共享同一密钥，用于校验 admin 签发的 token（集成阶段实现）
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS512"


settings = Settings()
