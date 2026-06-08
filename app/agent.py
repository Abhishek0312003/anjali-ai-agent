"""
Anjali — Vereda Digital Technologies AI Business Development Executive.
LLM brain — OpenAI GPT-4o-mini, function calls, lead registration.
Prompt lives in prompt.py — edit persona/language there.
"""
import json
import logging
import time

import httpx
from openai import AsyncOpenAI

from app.config import settings
from app.prompt import SYSTEM_PROMPT, HANGUP_KEYWORDS
from app.notifier import send_callback_notification

logger = logging.getLogger("abhishek.agent")


class AbhishekAgent:
    def __init__(self, call_id: str, call_state: dict):
        self.call_id = call_id
        self.call_state = call_state
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._history: list[dict] = []

        self._tools = [
            {
                "type": "function",
                "function": {
                    "name": "register_contact",
                    "description": "Register caller contact details for general inquiry or to connect with Vereda team.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "phone": {"type": "string"},
                            "city": {"type": "string"},
                            "reason": {"type": "string"},
                            "company": {"type": "string"},
                        },
                        "required": ["name", "phone", "city", "reason"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "book_demo",
                    "description": "Book a live product demo when prospect wants to see it.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "phone": {"type": "string"},
                            "company": {"type": "string"},
                            "product_interest": {"type": "string", "description": "AI Agent / App Development / Website / SaaS / Flutter Training"},
                            "preferred_date": {"type": "string"},
                            "preferred_time": {"type": "string"},
                        },
                        "required": ["name", "phone", "product_interest"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "schedule_callback",
                    # ── KEY CHANGE: fire as soon as callback intent is detected.
                    # preferred_time and preferred_date are now OPTIONAL so the
                    # function call fires immediately — even before the caller
                    # specifies a time. The WhatsApp notification will show
                    # "To be confirmed" if no time was given.
                    "description": (
                        "Schedule a callback when caller expresses any intent to be called back — "
                        "e.g. 'callback karo', 'baad mein baat karte hain', 'I am busy', "
                        "'call me later', 'call arrange kijiye'. "
                        "Call this function IMMEDIATELY on callback intent. "
                        "Do NOT wait to collect preferred_time first."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "phone": {"type": "string"},
                            "preferred_date": {"type": "string", "description": "Date caller wants callback — optional, collect if mentioned"},
                            "preferred_time": {"type": "string", "description": "Time caller wants callback — optional, collect if mentioned"},
                            "notes": {"type": "string"},
                        },
                        "required": ["name", "phone"],   # ← only name+phone required now
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "register_ai_agent_requirement",
                    "description": "Register detailed AI Agent requirement when caller wants to build one.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "phone": {"type": "string"},
                            "company": {"type": "string"},
                            "industry": {"type": "string"},
                            "agent_type": {"type": "string", "description": "Inbound / Outbound / Both"},
                            "channel": {"type": "string", "description": "Voice / Chat / Both"},
                            "language": {"type": "string"},
                            "whatsapp_integration": {"type": "boolean"},
                            "crm_integration": {"type": "boolean"},
                            "daily_call_volume": {"type": "string"},
                            "budget_range": {"type": "string"},
                        },
                        "required": ["name", "phone", "industry", "agent_type"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "register_development_requirement",
                    "description": "Register app or website development requirement.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "phone": {"type": "string"},
                            "company": {"type": "string"},
                            "dev_type": {"type": "string", "description": "Mobile App / Website / SaaS / CRM / Other"},
                            "platform": {"type": "string", "description": "Android / iOS / Both / Web"},
                            "features_summary": {"type": "string"},
                            "timeline": {"type": "string"},
                            "budget_range": {"type": "string"},
                        },
                        "required": ["name", "phone", "dev_type"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "job_inquiry",
                    "description": "Register job or internship candidate details.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "phone": {"type": "string"},
                            "qualification": {"type": "string"},
                            "experience_years": {"type": "string"},
                            "role_interest": {"type": "string"},
                            "city": {"type": "string"},
                        },
                        "required": ["name", "phone", "qualification"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "partnership_request",
                    "description": "Register agency or company partnership inquiry.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "contact_person": {"type": "string"},
                            "company_name": {"type": "string"},
                            "phone": {"type": "string"},
                            "business_type": {"type": "string"},
                            "collaboration_purpose": {"type": "string"},
                        },
                        "required": ["contact_person", "company_name", "phone"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "flutter_training_inquiry",
                    "description": "Register Flutter training course interest.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "phone": {"type": "string"},
                            "student_or_professional": {"type": "string"},
                            "experience_level": {"type": "string", "description": "Beginner / Intermediate / Advanced"},
                            "preferred_mode": {"type": "string", "description": "Online / Offline"},
                            "city": {"type": "string"},
                        },
                        "required": ["name", "phone", "student_or_professional"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "escalate_to_human",
                    "description": "Connect to human for enterprise deal, legal concern, or angry customer.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {"type": "string"},
                            "caller_name": {"type": "string"},
                            "caller_phone": {"type": "string"},
                            "priority": {"type": "string", "description": "High / Medium"},
                        },
                        "required": ["reason"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "hangup_call",
                    "description": "End the call when caller has said farewell.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

    def greeting(self) -> str:
        return (
            "Namaskar ji! I am Anjali calling from Vereda Digital Technologies. "
            "How are you doing today?"
        )

    async def process(self, user_text: str) -> tuple[str, bool]:
        lower = user_text.lower()
        if any(k in lower for k in HANGUP_KEYWORDS):
            return (
                "Thank you so much for your time ji! "
                "For any requirement, please call us directly at "
                "nine nine three four six zero one two four four "
                "or visit vedronix dot com. Have a wonderful day, namaskar ji!"
            ), True

        self._history.append({"role": "user", "content": user_text})

        try:
            response = await self._client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + self._history,
                tools=self._tools,
                tool_choice="auto",
                temperature=0.35,
                max_tokens=220,
            )
        except Exception as e:
            logger.error(f"[{self.call_id}] OpenAI error: {e}")
            return (
                "I am sorry, there was a small technical issue. "
                "Please try again or call us at nine nine three four six zero one two four four."
            ), False

        message = response.choices[0].message
        should_hangup = False
        reply_text = message.content or ""

        if message.tool_calls:
            tool_results = []
            for tc in message.tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments or "{}")

                if fn_name == "hangup_call":
                    should_hangup = True
                    result = {"status": "hangup_requested"}

                elif fn_name == "escalate_to_human":
                    result = {"status": "escalated"}
                    logger.warning(f"[{self.call_id}] ESCALATION: {fn_args}")

                elif fn_name == "schedule_callback":
                    result = await self._save_lead(fn_name, fn_args)

                    # ── WhatsApp callback notification to admin ──────
                    caller_number = (
                        fn_args.get("phone")
                        or self.call_state.get("from_number")
                        or self.call_state.get("to_number", "Unknown")
                    )
                    await send_callback_notification(
                        caller_number=caller_number,
                        preferred_time=fn_args.get("preferred_time", "To be confirmed"),
                        preferred_date=fn_args.get("preferred_date", ""),
                    )

                elif fn_name in (
                    "register_contact", "book_demo",
                    "register_ai_agent_requirement", "register_development_requirement",
                    "job_inquiry", "partnership_request", "flutter_training_inquiry",
                ):
                    result = await self._save_lead(fn_name, fn_args)

                else:
                    result = {"status": "unknown_function"}

                tool_results.append({
                    "tool_call_id": tc.id,
                    "role": "tool",
                    "content": json.dumps(result),
                })

            self._history.append(message.model_dump())
            self._history.extend(tool_results)

            followup = await self._client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + self._history,
                temperature=0.35,
                max_tokens=180,
            )
            reply_text = followup.choices[0].message.content or reply_text
            self._history.append({"role": "assistant", "content": reply_text})
        else:
            self._history.append({"role": "assistant", "content": reply_text})

        if len(self._history) > 40:
            self._history = self._history[-40:]

        return reply_text, should_hangup

    async def _save_lead(self, lead_type: str, data: dict) -> dict:
        self.call_state.setdefault("leads", []).append({
            "type": lead_type,
            "data": data,
            "timestamp": time.time(),
        })
        self.call_state["registered"] = True
        logger.info(f"[{self.call_id}] Lead saved [{lead_type}]: {data}")

        if settings.CRM_WEBHOOK_URL:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    await client.post(
                        settings.CRM_WEBHOOK_URL,
                        json={
                            "call_id": self.call_id,
                            "lead_type": lead_type,
                            "timestamp": time.time(),
                            "source": "anjali_ai_agent",
                            **data,
                        },
                    )
            except Exception as e:
                logger.warning(f"[{self.call_id}] CRM webhook failed: {e}")

        return {"status": "registered", "lead_type": lead_type}