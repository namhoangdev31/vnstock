import urllib.parse
import warnings
from typing import Literal, Self

from pydantic import (
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

VALID_PSYCOPG_PARAMS: set[str] = {
    "connect_timeout",
    "sslmode",
    "application_name",
    "keepalives",
    "keepalives_idle",
    "keepalives_interval",
    "keepalives_count",
    "channel_binding",
    "options",
    "target_session_attrs",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file=(".env", "../.env"),
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    FRONTEND_HOST: str = "http://localhost:5173"
    FASTAPI_ENV: Literal["development"] | None = None

    PROJECT_NAME: str
    SENTRY_DSN: HttpUrl | None = None
    DATABASE_URL: PostgresDsn
    DIRECT_URL: PostgresDsn | None = None

    # vnstock config
    VNSTOCK_SOURCE: str = "VCI"
    VNSTOCK_FALLBACK_SOURCE: str = "KBS"
    VNSTOCK_TERTIARY_SOURCE: str = "MSN"
    VNSTOCK_REALTIME_CACHE_TTL: int = 5  # seconds
    VNSTOCK_METADATA_CACHE_TTL: int = 86400  # 24 hours
    # Minimum spacing between external vnstock requests (anti-ban, AGENTS §7.2).
    # Spec mandates 0.2–0.5s; 0.3s is a safe default.
    VNSTOCK_REQUEST_MIN_DELAY: float = 0.3

    # Cron & Background Scheduler config
    CRON_SECRET_KEY: str | None = None
    ENABLE_INPROCESS_CRON: bool = False

    @classmethod
    def _validate_and_normalize_postgres_url(
        cls, value: str | PostgresDsn | None, field_name: str
    ) -> str | None:
        if value is None:
            return None
        url_str = str(value).strip()
        if not url_str:
            return None

        # Check for unencoded '@' in credentials authority (RFC 3986)
        rest = url_str
        for prefix in ("postgres://", "postgresql://", "postgresql+psycopg://"):
            if rest.startswith(prefix):
                rest = rest[len(prefix) :]
                break

        authority = rest.split("/", 1)[0].split("?", 1)[0]
        if authority.count("@") > 1:
            raise ValueError(
                f"{field_name} contains unencoded '@' in credentials. "
                "Per RFC 3986, passwords with '@' must be percent-encoded as '%40' to prevent ambiguous URI parsing."
            )

        # Parse query parameters and validate against allow-list
        if "?" in url_str:
            _base_url, query_str = url_str.split("?", 1)
            query_params = urllib.parse.parse_qsl(query_str, keep_blank_values=True)
            unknown_params = [
                k for k, _ in query_params if k not in VALID_PSYCOPG_PARAMS
            ]
            if unknown_params:
                raise ValueError(
                    f"{field_name} contains invalid psycopg connection parameter(s): {unknown_params}. "
                    f"Only valid libpq parameters {sorted(VALID_PSYCOPG_PARAMS)} are allowed. "
                    "Please remove unsupported options like '?pgbouncer=true' from your connection string."
                )

        for scheme in ("postgres://", "postgresql://"):
            if url_str.startswith(scheme):
                return url_str.replace(scheme, "postgresql+psycopg://", 1)
        return url_str

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _validate_database_url(cls, value: str | PostgresDsn) -> str:
        res = cls._validate_and_normalize_postgres_url(value, "DATABASE_URL")
        assert res is not None
        return res

    @field_validator("DIRECT_URL", mode="before")
    @classmethod
    def _validate_direct_url(cls, value: str | PostgresDsn | None) -> str | None:
        return cls._validate_and_normalize_postgres_url(value, "DIRECT_URL")

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.FASTAPI_ENV == "development":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        for host in self.DATABASE_URL.hosts():
            self._check_default_secret("DATABASE_URL password", host["password"])
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )

        return self


settings = Settings()  # type: ignore # ty: ignore[unused-ignore-comment]
