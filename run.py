"""
Entry point — Abhishek AI Agent (Vereda Digital Technologies)
Run with: python run.py
Tests all API keys on startup before launching the server.
"""
import asyncio
import httpx
import uvicorn
from app.config import settings


def check(label: str, ok: bool, detail: str = ""):
    status = "✅" if ok else "❌"
    print(f"  {status}  {label}" + (f"  →  {detail}" if detail else ""))
    return ok


async def test_all_keys():
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  Abhishek AI Agent — Vereda Digital Technologies")
    print("  API Key Health Check")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    all_ok = True

    async with httpx.AsyncClient(timeout=10) as client:

        # ── 1. FreJun / Teler ────────────────────────────────────────────
        try:
            r = await client.get("https://api.frejun.ai/redoc")
            ok = r.status_code == 200
            all_ok &= check("FreJun Teler", ok, "API reachable — key validated at call time")
        except Exception as e:
            all_ok &= check("FreJun Teler", False, str(e)[:60])

        # ── 2. Deepgram ──────────────────────────────────────────────────
        try:
            r = await client.get(
                "https://api.deepgram.com/v1/projects",
                headers={"Authorization": f"Token {settings.DEEPGRAM_API_KEY}"},
            )
            ok = r.status_code == 200
            all_ok &= check("Deepgram STT (nova-3, hi-en)", ok, f"HTTP {r.status_code}")
        except Exception as e:
            all_ok &= check("Deepgram STT", False, str(e)[:60])

        # ── 3. OpenAI ────────────────────────────────────────────────────
        try:
            r = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            )
            ok = r.status_code == 200
            all_ok &= check("OpenAI GPT-4o-mini", ok, f"HTTP {r.status_code}")
        except Exception as e:
            all_ok &= check("OpenAI GPT-4o-mini", False, str(e)[:60])

        # ── 4. Sarvam AI (bulbul:v2 / arjun) ────────────────────────────
        try:
            r = await client.post(
                "https://api.sarvam.ai/text-to-speech",
                headers={"api-subscription-key": settings.SARVAM_API_KEY},
                json={
                    "inputs": ["Namaskar ji, main Abhishek bol raha hoon Vereda Digital Technologies se."],
                    "target_language_code": "hi-IN",
                    "speaker": settings.SARVAM_SPEAKER,     # arjun
                    "model": settings.SARVAM_TTS_MODEL,     # bulbul:v2
                    "speech_sample_rate": 8000,
                },
            )
            body = r.text[:120]
            if r.status_code == 200:
                all_ok &= check(f"Sarvam AI ({settings.SARVAM_TTS_MODEL} / {settings.SARVAM_SPEAKER})", True, "HTTP 200 ✓")
            elif "allowlist" in body.lower():
                all_ok &= check(f"Sarvam AI ({settings.SARVAM_TTS_MODEL} / {settings.SARVAM_SPEAKER})", True, "Key valid — server IP not in allowlist (normal for local dev)")
            elif r.status_code == 401:
                all_ok &= check(f"Sarvam AI", False, "401 — invalid API key")
            else:
                all_ok &= check(f"Sarvam AI", False, f"HTTP {r.status_code} — {body}")
        except Exception as e:
            all_ok &= check("Sarvam AI", False, str(e)[:60])

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if all_ok:
        print("  All keys valid — starting Abhishek agent...\n")
    else:
        print("  ⚠️  Some keys failed — server will start but affected features won't work.\n")


if __name__ == "__main__":
    asyncio.run(test_all_keys())
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=False,
        log_level="info",
    )
