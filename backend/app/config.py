from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    app_name: str = 'Sales Insight Automator API'
    environment: str = 'development'
    max_file_size_mb: int = 5
    max_rows: int = 20000
    allowed_origins: str = 'http://localhost:5173,http://localhost:3000'

    groq_api_key: str | None = None
    groq_model: str = 'llama-3.1-8b-instant'

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = 'noreply@example.com'
    smtp_use_tls: bool = True

    api_key: str | None = Field(default=None, description='Optional shared key for API calls.')


settings = Settings()
