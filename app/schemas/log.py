from datetime import datetime
from pydantic import BaseModel, ConfigDict


class LogCreate(BaseModel):
    log_level: str = "INFO"
    message: str


class LogResponse(BaseModel):
    id: int
    deployment_id: int
    log_level: str
    message: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
