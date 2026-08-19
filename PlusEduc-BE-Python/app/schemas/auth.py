from pydantic import BaseModel, ConfigDict, Field, field_validator


class AuthenticationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Invalid email")
        return normalized


class AuthenticationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accessToken: str
    refreshToken: str
    tokenType: str
    expiresIn: int
    userId: str
    userEmail: str
    role: str
    studentId: str | None = None
    name: str | None = None
