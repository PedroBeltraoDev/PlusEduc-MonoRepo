from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: str
    version: str
    environment: str
    database: str = Field(description="Estado da conexão MongoDB")
    timestamp: datetime
    opencl: dict[str, bool | int | str | None] = Field(description="Estado do processamento OpenCL das estatísticas de notas")
