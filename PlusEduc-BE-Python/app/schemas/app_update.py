from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AppVersionResponse(BaseModel):
    version: str


class DownloadState(BaseModel):
    state: Literal["idle", "downloading", "launching", "error"]
    progress: float = Field(ge=0, le=1, description="Fração já baixada do instalador")
    error: str | None = None


class UpdateStatusResponse(BaseModel):
    currentVersion: str
    status: Literal["disabled", "pending", "up_to_date", "available", "no_release", "offline", "rate_limited", "error"]
    message: str = ""
    updateAvailable: bool
    latestVersion: str | None = None
    releaseUrl: str | None = None
    releaseNotes: str | None = None
    installerSize: int | None = None
    canInstall: bool = Field(description="Este app pode baixar e executar o instalador (Windows instalado, com janela)")
    checkedAt: datetime | None = None
    download: DownloadState
