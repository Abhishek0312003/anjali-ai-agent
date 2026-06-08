"""
Environment-based configuration for Abhishek AI Agent — Vereda Digital Technologies.
Copy .env.example → .env and fill in your keys before running.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ── FreJun / Teler ──────────────────────────────────────────────
    TELER_API_KEY: str = ""
    TELER_FROM_NUMBER: str = "+918065179538"

    # ── Deepgram (STT) ───────────────────────────────────────────────
    DEEPGRAM_API_KEY: str = ""
    DEEPGRAM_MODEL: str = "nova-3"
    DEEPGRAM_LANGUAGE: str = "hi-en"

    # ── OpenAI ──────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # ── Sarvam AI (TTS) ─────────────────────────────────────────────
    SARVAM_API_KEY: str = ""
    SARVAM_TTS_MODEL: str = "bulbul:v3"
    SARVAM_SPEAKER: str = "niharika"
    SARVAM_LANGUAGE: str = "hi-IN"
    SARVAM_SAMPLE_RATE: int = 8000

    # ── Server ──────────────────────────────────────────────────────
    PUBLIC_HOST: str = "your-domain.com"
    PORT: int = 8000

    # ── CRM / Lead Capture ──────────────────────────────────────────
    CRM_WEBHOOK_URL: str = ""

    # ── WhatsApp: Call-End Notification (Interakt) ──────────────────
    IS_WHATSAPP_NOTIFICATION_ACTIVE: bool = False
    INTERAKT_API_KEY: str = ""                          # Interakt → Settings → Developer → API Key (Base64)
    WHATSAPP_ADMIN_NUMBER: str = "+919934601244"        # Admin number to notify
    INTERAKT_TEMPLATE_NAME: str = "ai_agent_call_alert"

    # ── WhatsApp: Callback Request Notification (Interakt) ──────────
    IS_CALLBACK_NOTIFICATION_ACTIVE: bool = False
    INTERAKT_CALLBACK_TEMPLATE_NAME: str = "ai_agent_callback_request"


settings = Settings()