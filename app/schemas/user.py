from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

# Support email string validation without mandatory email-validator dependency
EmailStr = str


class UserBase(BaseModel):
    email: str = Field(..., description="User email address")
    full_name: str | None = None


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    github_access_token: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
