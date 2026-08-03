from pydantic import BaseModel, Field
from app.schemas.user import UserResponse


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int | None = None
    email: str | None = None


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str


class AuthResponse(BaseModel):
    user: UserResponse
    token: Token
