from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database (SQLite by default, use postgresql:// for production)
    database_url: str = Field(default="sqlite:///ai_news_digest.db")

    # API Keys
    anthropic_api_key: str = Field(default="")
    youtube_api_key: str = Field(default="")
    sendgrid_api_key: str = Field(default="")

    # Email settings
    from_email: str = Field(default="digest@example.com")
    to_email: str = Field(default="")
    digest_send_hour: int = Field(default=7)  # 7 AM PT

    # Processing settings
    claude_model: str = Field(default="claude-sonnet-4-20250514")
    max_summary_tokens: int = Field(default=500)

    # Polling intervals (hours)
    rss_poll_interval: int = Field(default=6)
    youtube_poll_interval: int = Field(default=24)


class Sources(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    rss_feeds: list[dict[str, str]] = Field(
        default=[
            {"name": "TechCrunch Startups", "url": "https://techcrunch.com/category/startups/feed/"},
            {"name": "a16z Podcast", "url": "https://feeds.simplecast.com/JGE3yC0V"},
            {"name": "20VC Podcast", "url": "https://thetwentyminutevc.libsyn.com/rss"},
        ]
    )

    youtube_channels: list[dict[str, str]] = Field(
        default=[
            {"name": "Dwarkesh Patel", "channel_id": "UCChAT3VUzU0kkBn2t9oT7dQ"},
            {"name": "Silicon Valley 101", "channel_id": "UCcW_IiQPdz0WIsB22MfXKRw"},
        ]
    )


settings = Settings()
sources = Sources()
