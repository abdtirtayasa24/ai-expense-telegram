from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_base_url: str
    mini_app_url: str

    telegram_bot_token: str
    admin_telegram_id: int
    admin_contact_telegram: str = ""
    admin_contact_whatsapp: str = ""

    supabase_url: str
    supabase_service_role_key: str

    gemini_api_key: str
    gemini_model: str = "gemini-3.1-flash-lite"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 10080
    telegram_init_data_max_age_seconds: int = 86400

    default_language: str
    default_currency: str
    default_timezone: str

    parser_confidence_threshold: float = 0.75
    advisor_mode_timeout_minutes: int = 15
    advisor_chat_history_limit: int = 60
    cron_secret: str | None = None

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
