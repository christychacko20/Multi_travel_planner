from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agent Orchestration Platform"
    environment: str = "development"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/agent_platform"
    approval_required: bool = True
    max_plan_steps: int = 8

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
