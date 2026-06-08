# Abhishek AI Agent — Vereda Digital Technologies

**AI Business Development Executive** for Vereda Digital Technologies.

Stack: **FreJun Teler** (telephony) → **Deepgram Nova-3** (STT) → **OpenAI GPT-4o-mini** (LLM) → **Sarvam Bulbul-v2** (TTS)

---

## What is Abhishek?

Abhishek is a Hinglish-speaking AI voice agent that behaves like an experienced Business Development Executive. He handles inbound calls for Vereda Digital Technologies — qualifying leads, booking demos, scheduling callbacks, and registering requirements across all service verticals.

**Language**: 70% Hindi + 30% English (Hinglish) — natural, professional, not robotic.

---

## TTS Upgrade (vs original Anaya agent)

| Setting | Old (Anaya) | New (Abhishek) |
|---|---|---|
| Model | `bulbul:v3` | `bulbul:v2` — better Hinglish clarity |
| Speaker | `anushka` (female) | `abhilash` (male — matches Abhishek) |
| Pace | 1.0 | 0.95 — slightly slower, professional |
| Loudness | 1.4 | 1.5 — clearer on telephony |

## STT Upgrade

| Setting | Old | New |
|---|---|---|
| Language | `hi` | `hi-en` — code-mix Hinglish |

---

## Function Calls (10 tools)

| Function | Trigger |
|---|---|
| `register_contact` | General inquiry / "team se milna hai" |
| `book_demo` | "Demo dekhna hai" / Hot lead |
| `schedule_callback` | Caller is busy / "Baad mein call karo" |
| `register_ai_agent_requirement` | AI Agent requirement discussion |
| `register_development_requirement` | App / Website / SaaS development |
| `job_inquiry` | Job or internship interest |
| `partnership_request` | Agency / company collaboration |
| `flutter_training_inquiry` | Flutter course interest |
| `escalate_to_human` | Enterprise / legal / angry customer |
| `hangup_call` | Farewell detected |

---

## Setup

```bash
cp .env.example .env
# Fill in your API keys in .env
pip install -r requirements.txt
python run.py
```

## Company Info (embedded in agent knowledge base)

- **Company**: Vereda Digital Technologies Private Limited
- **Website**: vedronix.com
- **Phone**: 9934601244
- **Founders/CEO**: Himanshu Kumar & Khusdhanshu Kumar (B.Tech ECE, 2016)
- **Team**: 50+ professionals
- **Experience**: 12+ years
- **Services**: AI Agent Development, App Development, Web Development, SaaS/CRM, Flutter Training
# anjali-ai-agent
