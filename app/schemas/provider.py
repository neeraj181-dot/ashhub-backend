from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.core.enums import ProviderType


class ProviderBase(BaseModel):
    name: str
    slug: str
    provider_type: ProviderType = ProviderType.BOTH
    config: dict | None = None
    is_active: bool = True


class ProviderCreate(ProviderBase):
    pass


class ProviderUpdate(BaseModel):
    name: str | None = None
    provider_type: ProviderType | None = None
    config: dict | None = None
    is_active: bool | None = None


class ProviderResponse(ProviderBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
