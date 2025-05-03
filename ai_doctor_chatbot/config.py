from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    openrouter_api_key: str
    secret_key: str = "dev-secret-key"
    database_url: str = "sqlite:///./medical_chat.db"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
