from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Discord
    discord_bot_token: str
    discord_channel_id: int          # #wall-e — main chat
    discord_briefings_channel_id: int  # #briefings — morning briefings
    discord_drafts_channel_id: int     # #drafts — post approvals

    # AI
    groq_api_key: str
    tavily_api_key: str

    # Database — PostgreSQL on Railway, SQLite for local dev
    database_url: str = "sqlite+aiosqlite:///wall_e.db"

    # Scheduling
    timezone: str = "America/New_York"
    morning_brief_cron: str = "0 9 * * *"

    # Agent
    groq_model: str = "llama-3.3-70b-versatile"
    max_tool_iterations: int = 10
    max_conversation_history: int = 20

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# For convenience — lazy property that initializes on first access
class _SettingsProxy:
    def __getattr__(self, name: str):
        return getattr(get_settings(), name)


settings = _SettingsProxy()  # type: ignore[assignment]
