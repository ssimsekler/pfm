"""Application configuration (Pydantic settings, env-driven)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_prefix="")

    # Database
    database_url: str = "postgresql+psycopg://pfm:change-me-postgres@db:5432/pfm"
    db_schema: str = "pfm"

    # Security
    backend_secret_key: str = "change-me-secret"

    # Currencies
    app_default_txn_currency: str = "AED"
    app_reporting_currency: str = "USD"

    # LLM
    llm_master_enabled: bool = False
    ollama_base_url: str = "http://ollama:11434"
    ollama_default_model: str = "llama3.2"

    # Keycloak / OIDC
    keycloak_url: str = "http://keycloak:8080/auth"
    keycloak_realm: str = "pfm"
    keycloak_client_id: str = "pfm-frontend"

    # Object storage
    minio_endpoint: str = "objectstore:9000"
    minio_root_user: str = "pfm-minio"
    minio_root_password: str = "change-me-minio"
    minio_bucket: str = "pfm-documents"

    # SQL console guards (Decision #10)
    sql_console_row_limit: int = 1000
    sql_console_timeout_ms: int = 5000


@lru_cache
def get_settings() -> Settings:
    return Settings()