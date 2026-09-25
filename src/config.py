"""
Configuration management for MCP Legal Assistant.
Loads environment variables and provides typed settings.
"""

import os
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ============================================================
    # LLM API Keys
    # ============================================================
    openai_api_key: str = Field(
        default="sk-placeholder",
        env="OPENAI_API_KEY"
    )

    anthropic_api_key: str = Field(
        default="sk-ant-placeholder",
        env="ANTHROPIC_API_KEY"
    )

    groq_api_key: str = Field(
        default="",
        env="GROQ_API_KEY"
    )

    # ============================================================
    # Pinecone Vector Database
    # ============================================================
    pinecone_api_key: str = Field(
        default="placeholder-pinecone-key",
        env="PINECONE_API_KEY"
    )

    pinecone_environment: str = Field(
        default="us-west-2",
        env="PINECONE_ENVIRONMENT"
    )

    pinecone_index_name: str = Field(
        default="legal-assistant-index",
        env="PINECONE_INDEX_NAME"
    )

    # ============================================================
    # Database (PostgreSQL)
    # ============================================================
    database_url: str = Field(
        default="postgresql://localhost:5432/legal_assistant",
        env="DATABASE_URL"
    )

    database_async_url: Optional[str] = Field(
        default=None,
        env="DATABASE_ASYNC_URL"
    )

    # ============================================================
    # Google Calendar API (Deadline Tracker)
    # ============================================================
    google_client_id: Optional[str] = Field(
        default=None,
        env="GOOGLE_CLIENT_ID"
    )

    google_client_secret: Optional[str] = Field(
        default=None,
        env="GOOGLE_CLIENT_SECRET"
    )

    google_calendar_id: str = Field(
        default="primary",
        env="GOOGLE_CALENDAR_ID"
    )

    # ============================================================
    # Twilio (SMS Alerts)
    # ============================================================
    twilio_account_sid: Optional[str] = Field(
        default=None,
        env="TWILIO_ACCOUNT_SID"
    )

    twilio_auth_token: Optional[str] = Field(
        default=None,
        env="TWILIO_AUTH_TOKEN"
    )

    twilio_phone_number: Optional[str] = Field(
        default=None,
        env="TWILIO_PHONE_NUMBER"
    )

    # ============================================================
    # Stripe (Billing)
    # ============================================================
    stripe_secret_key: Optional[str] = Field(
        default=None,
        env="STRIPE_SECRET_KEY"
    )

    stripe_webhook_secret: Optional[str] = Field(
        default=None,
        env="STRIPE_WEBHOOK_SECRET"
    )

    # ============================================================
    # Court Listener API (Case Research)
    # ============================================================
    courtlistener_api_key: Optional[str] = Field(
        default=None,
        env="COURTLISTENER_API_KEY"
    )

    # ============================================================
    # Server Configuration
    # ============================================================
    host: str = Field(
        default="0.0.0.0",
        env="HOST"
    )

    port: int = Field(
        default=8000,
        env="PORT"
    )

    log_level: str = Field(
        default="info",
        env="LOG_LEVEL"
    )

    # ============================================================
    # Security
    # ============================================================
    secret_key: str = Field(
        default="dev-secret-key",
        env="SECRET_KEY"
    )

    encryption_key: Optional[bytes] = Field(
        default=None,
        env="ENCRYPTION_KEY"
    )

    # ============================================================
    # Firm Defaults
    # ============================================================
    default_jurisdiction: str = Field(
        default="Texas",
        env="DEFAULT_JURISDICTION"
    )

    default_billing_increment: float = Field(
        default=0.1,
        env="DEFAULT_BILLING_INCREMENT"
    )

    conflict_check_required: bool = Field(
        default=True,
        env="CONFLICT_CHECK_REQUIRED"
    )

    # ============================================================
    # Model Configuration
    # ============================================================

    # Main orchestrator
    orchestrator_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        env="ORCHESTRATOR_MODEL"
    )

    # Contract Reviewer → Groq
    contract_reviewer_model: str = Field(
        default="openai/gpt-oss-120b",
        env="CONTRACT_REVIEWER_MODEL"
    )

    # Other agents - currently unchanged
    case_researcher_model: str = Field(
        default="gpt-4o",
        env="CASE_RESEARCHER_MODEL"
    )

    document_drafter_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        env="DOCUMENT_DRAFTER_MODEL"
    )

    deadline_tracker_model: str = Field(
        default="gpt-4o",
        env="DEADLINE_TRACKER_MODEL"
    )

    billing_calculator_model: str = Field(
        default="gpt-4o",
        env="BILLING_CALCULATOR_MODEL"
    )

    # ============================================================
    # Pydantic Settings Configuration
    # ============================================================
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# ============================================================
# Global settings instance
# ============================================================

_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings

    if _settings is None:
        _settings = Settings()

    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global _settings

    _settings = Settings()

    return _settings