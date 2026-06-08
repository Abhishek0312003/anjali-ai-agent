"""
WhatsApp notifications via Interakt for Anjali AI Agent — Vereda Digital Technologies.

Functions:
  send_call_notification()     — fires on call end (ai_agent_call_alert template)
  send_callback_notification() — fires when caller requests a callback (ai_agent_callback_request template)

Call-End Template variables:
  {{1}} — caller phone number
  {{2}} — call time (HH:MM AM/PM IST)
  {{3}} — duration (e.g. '62 sec')

Callback Template variables:
  Header {{1}} — caller phone number
  Body   {{1}} — caller phone number
  Body   {{2}} — preferred callback time (from caller)
  Body   {{3}} — request received at (IST time)
"""
import logging
from datetime import datetime, timezone, timedelta

import httpx

from app.config import settings

logger = logging.getLogger("abhishek.notifier")

INTERAKT_SEND_URL = "https://api.interakt.ai/v1/public/message/"
IST = timedelta(hours=5, minutes=30)


def _ist_time_str() -> str:
    """Return current IST time as a readable string, e.g. '03:45 PM IST'."""
    now_ist = datetime.now(timezone.utc) + IST
    return now_ist.strftime("%I:%M %p IST")


async def _send_interakt(payload: dict, label: str) -> None:
    """Internal helper — POST to Interakt and log result."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                INTERAKT_SEND_URL,
                headers={
                    "Authorization": f"Basic {settings.INTERAKT_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        if resp.status_code in (200, 201):
            logger.info(f"✅ WhatsApp [{label}] sent — {resp.status_code}: {resp.text}")
        else:
            logger.warning(f"Interakt [{label}] returned {resp.status_code}: {resp.text}")

    except Exception as e:
        logger.error(f"Failed to send WhatsApp [{label}]: {e}")


async def send_call_notification(caller_number: str, duration_seconds: float) -> None:
    """
    Send call-end notification to admin.
    Controlled by IS_WHATSAPP_NOTIFICATION_ACTIVE in .env.

    Args:
        caller_number:    Phone number that called (e.g. '+919876543210').
        duration_seconds: Total call duration in seconds.
    """
    if not settings.IS_WHATSAPP_NOTIFICATION_ACTIVE:
        logger.debug("Call notification disabled — skipping.")
        return

    if not settings.INTERAKT_API_KEY:
        logger.warning("INTERAKT_API_KEY not set — cannot send call notification.")
        return

    admin_raw    = settings.WHATSAPP_ADMIN_NUMBER.lstrip("+")
    country_code = admin_raw[:2]
    phone_number = admin_raw[2:]

    call_time    = _ist_time_str()
    duration_str = f"{int(duration_seconds)} sec"

    payload = {
        "countryCode": f"+{country_code}",
        "phoneNumber": phone_number,
        "callbackData": "anjali_call_end_notification",
        "type": "Template",
        "template": {
            "name": settings.INTERAKT_TEMPLATE_NAME,
            "languageCode": "en",
            "headerValues": [caller_number],
            "bodyValues": [
                caller_number,   # {{1}} Phone Number
                call_time,       # {{2}} Time
                duration_str,    # {{3}} Duration
            ],
        },
    }

    await _send_interakt(payload, label="call_end")


async def send_callback_notification(
    caller_number: str,
    preferred_time: str,
    preferred_date: str = "",
) -> None:
    """
    Send callback request notification to admin.
    Controlled by IS_CALLBACK_NOTIFICATION_ACTIVE in .env.

    Args:
        caller_number:   Phone number of the caller requesting callback.
        preferred_time:  Time they want to be called back (from conversation).
        preferred_date:  Date they want to be called back (optional).
    """
    if not settings.IS_CALLBACK_NOTIFICATION_ACTIVE:
        logger.debug("Callback notification disabled — skipping.")
        return

    if not settings.INTERAKT_API_KEY:
        logger.warning("INTERAKT_API_KEY not set — cannot send callback notification.")
        return

    admin_raw    = settings.WHATSAPP_ADMIN_NUMBER.lstrip("+")
    country_code = admin_raw[:2]
    phone_number = admin_raw[2:]

    # Build preferred callback time string
    if preferred_date:
        callback_time_str = f"{preferred_date} {preferred_time}".strip()
    else:
        callback_time_str = preferred_time

    received_at = _ist_time_str()

    payload = {
        "countryCode": f"+{country_code}",
        "phoneNumber": phone_number,
        "callbackData": "anjali_callback_request_notification",
        "type": "Template",
        "template": {
            "name": settings.INTERAKT_CALLBACK_TEMPLATE_NAME,
            "languageCode": "en",
            "headerValues": [caller_number],   # Header {{1}}
            "bodyValues": [
                caller_number,       # {{1}} Phone Number
                callback_time_str,   # {{2}} Preferred Callback Time
                received_at,         # {{3}} Request Received At
            ],
        },
    }

    await _send_interakt(payload, label="callback_request")