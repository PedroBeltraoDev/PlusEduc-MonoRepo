from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "PlusEduc API"
    app_version: str = "0.1.0"
    app_env: str = "development"
    log_level: str = "INFO"

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "pluseduc"
    mongodb_required: bool = False
    mongodb_server_selection_timeout_ms: int = Field(default=2000, ge=50)
    mongodb_connect_timeout_ms: int = Field(default=2000, ge=50)

    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"]
    )
    cors_allow_credentials: bool = True

    jwt_secret: str = ""
    # Access token curto (30 min): a renovação é feita com o refresh token rotativo (/api/auth/refresh).
    jwt_expiration_ms: int = Field(default=1_800_000, ge=1_000)
    jwt_refresh_expiration_ms: int = Field(default=604_800_000, ge=1_000)

    audit_enabled: bool | None = None  # None: ligado, exceto quando APP_ENV começa com "test"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_api_version: str = "v1"
    gemini_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    gemini_connect_timeout_seconds: float = Field(default=10.0, gt=0.0)
    gemini_read_timeout_seconds: float = Field(default=45.0, gt=0.0)
    ai_demo_fallback_enabled: bool = True

    # Estatísticas de notas em GPU/CPU via OpenCL (usa o caminho em Python se não houver dispositivo).
    opencl_enabled: bool = True
    # Abaixo disso o Python é mais rápido que o envio à GPU (equilíbrio medido perto de 100 mil registros,
    # docs/sprint-08/resultados/benchmark_opencl.txt). Antes o padrão era 0: GPU até para 5 notas.
    opencl_min_records: int = Field(default=50_000, ge=0)
    opencl_device: str = ""  # trecho do nome do dispositivo (ex.: "Radeon"); vazio = a primeira GPU

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "PlusEduc"

    # Quando preenchido, todo código de recuperação de senha é enviado para este
    # endereço em vez do e-mail da conta (útil em ambiente de demonstração, onde
    # as contas de professor/aluno não são caixas de e-mail reais).
    password_reset_override_email: str = ""
    password_reset_code_ttl_minutes: int = Field(default=15, ge=1)
    # Modo de demonstração da recuperação de senha: código fixo devolvido na resposta da API.
    # Qualquer pessoa que conheça o e-mail de uma conta consegue trocar a senha dela, por isso
    # fica DESLIGADO por padrão e só deve ser ligado em máquina local, para apresentações.
    password_reset_demo_mode: bool = False

    # Limite de tentativas (login, cadastro e recuperação de senha).
    rate_limit_enabled: bool = True
    login_max_failures: int = Field(default=5, ge=1)
    login_window_seconds: int = Field(default=900, ge=1)
    password_reset_max_requests: int = Field(default=5, ge=1)
    password_reset_window_seconds: int = Field(default=900, ge=1)
    registration_max_requests: int = Field(default=10, ge=1)
    registration_window_seconds: int = Field(default=3600, ge=1)

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in {"production", "prod"}

    def insecure_production_settings(self) -> list[str]:
        """Configurações de demonstração que não podem ficar ativas em produção."""
        problems: list[str] = []
        if not self.is_production:
            return problems
        weak_secrets = {"", "change-this-to-a-long-random-secret", "secret", "changeme"}
        if self.jwt_secret in weak_secrets or len(self.jwt_secret) < 32:
            problems.append("JWT_SECRET ausente, fraco ou com o valor de exemplo")
        if self.password_reset_demo_mode:
            problems.append("PASSWORD_RESET_DEMO_MODE=true")
        if self.password_reset_override_email:
            problems.append("PASSWORD_RESET_OVERRIDE_EMAIL preenchido")
        if not self.rate_limit_enabled:
            problems.append("RATE_LIMIT_ENABLED=false")
        return problems

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
