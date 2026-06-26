from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_base_url: str
    mini_app_url: str

    telegram_bot_token: str
    admin_telegram_id: int

    supabase_url: str
    supabase_service_role_key: str

    gemini_api_key: str
    gemini_model: str = "gemini-3.1-flash-lite"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 10080

    default_language: str = "id"
    default_currency: str = "IDR"
    default_timezone: str = "Asia/Jakarta"

    parser_confidence_threshold: float = 0.75

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
