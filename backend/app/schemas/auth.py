from pydantic import BaseModel


class TelegramMiniAppAuthRequest(BaseModel):
    init_data: str


class AuthenticatedUser(BaseModel):
    id: str
    telegram_user_id: int
    first_name: str | None = None
    last_name: str | None = None
    role: str
    status: str
    currency: str
    timezone: str


class TelegramMiniAppAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthenticatedUser
