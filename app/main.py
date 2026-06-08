"""
Anjali — Vereda Digital Technologies AI Agent
Stack: FreJun Teler → Deepgram Nova-3 (STT) → OpenAI GPT-4o-mini (LLM) → Sarvam Bulbul-v3 (TTS)
"""
import asyncio
import base64
import json
import logging
import time
import uuid

import httpx
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from teler import CallFlow

from app.config import settings
from app.agent import AbhishekAgent
from app.notifier import send_call_notification
from app.stt import DeepgramSTT
from app.tts import SarvamTTS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
logger = logging.getLogger("abhishek.main")

app = FastAPI(title="Anjali AI Agent — Vereda Digital Technologies", version="3.1.0")

active_calls: dict[str, dict] = {}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Anjali AI Agent", "company": "Vereda Digital Technologies"}


@app.post("/flow")
async def call_flow(request: Request):
    body = await request.json()
    call_id     = body.get("call_id", "unknown")
    direction   = body.get("direction", "outbound")
    from_number = body.get("from_number", "")
    to_number   = body.get("to_number", "")

    logger.info(f"[{call_id}] New {direction} call  from={from_number}  to={to_number}")

    active_calls[call_id] = {
        "call_id":     call_id,
        "direction":   direction,
        "from_number": from_number,
        "to_number":   to_number,
        "started_at":  time.time(),
        "leads":       [],
        "registered":  False,
        "notified":    False,   # guard against double WhatsApp send
    }

    ws_url = f"wss://{settings.PUBLIC_HOST}/media-stream?call_id={call_id}"
    flow = CallFlow.stream(ws_url=ws_url, chunk_size=500, record=True)
    return JSONResponse(flow)


@app.post("/webhook")
async def call_webhook(request: Request):
    body       = await request.json()
    event_type = body.get("type", "unknown")
    call_id    = body.get("call_id", "")
    logger.info(f"[{call_id}] Teler event: {event_type}")

    if event_type == "call.completed" and call_id in active_calls:
        call_data     = active_calls.pop(call_id, {})
        duration      = round(time.time() - call_data.get("started_at", time.time()), 1)
        caller_number = call_data.get("from_number") or call_data.get("to_number", "Unknown")
        logger.info(f"[{call_id}] Call completed. Duration={duration}s  leads={call_data.get('leads')}")

        # ── WhatsApp admin notification (primary path via Teler webhook) ──
        if not call_data.get("notified"):
            call_data["notified"] = True
            await send_call_notification(
                caller_number=caller_number,
                duration_seconds=duration,
            )

    if event_type == "recording.completed":
        logger.info(f"[{call_id}] Recording ready: {body.get('recording_url', '')}")

    return {"status": "ok"}


@app.post("/initiate-call")
async def initiate_call(request: Request):
    body      = await request.json()
    to_number = body.get("to_number")
    if not to_number:
        return JSONResponse({"error": "to_number required"}, status_code=400)

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "https://api.frejun.ai/api/v1/calls/initiate",
            headers={"Authorization": f"Bearer {settings.TELER_API_KEY}"},
            json={
                "from_number":         settings.TELER_FROM_NUMBER,
                "to_number":           to_number,
                "flow_url":            f"https://{settings.PUBLIC_HOST}/flow",
                "status_callback_url": f"https://{settings.PUBLIC_HOST}/webhook",
                "record":              True,
            },
        )

    if resp.status_code == 200:
        data = resp.json()
        logger.info(f"Outbound call initiated: call_id={data.get('call_id')}")
        return {"status": "initiated", "call_id": data.get("call_id")}
    else:
        logger.error(f"Teler initiate failed: {resp.status_code} {resp.text}")
        return JSONResponse({"error": resp.text}, status_code=resp.status_code)


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    await websocket.accept()
    call_id = websocket.query_params.get("call_id", str(uuid.uuid4()))
    logger.info(f"[{call_id}] WebSocket connected")

    call_state = active_calls.get(call_id, {
        "call_id": call_id, "leads": [], "registered": False, "notified": False
    })
    call_state.setdefault("started_at", time.time())
    call_state.setdefault("notified", False)

    agent = AbhishekAgent(call_id=call_id, call_state=call_state)
    stt   = DeepgramSTT()
    tts   = SarvamTTS()

    chunk_id_counter = 0
    ws_closed        = False
    is_speaking      = False
    barge_in_event   = asyncio.Event()

    async def send_audio(audio_b64: str):
        nonlocal chunk_id_counter
        if ws_closed:
            return
        chunk_id_counter += 1
        await websocket.send_text(json.dumps({
            "type":     "audio",
            "audio_b64": audio_b64,
            "chunk_id": chunk_id_counter,
        }))

    async def clear_buffer():
        if ws_closed:
            return
        await websocket.send_text(json.dumps({"type": "clear"}))

    async def teler_ping_loop():
        try:
            while not ws_closed:
                await asyncio.sleep(20)
                if ws_closed:
                    break
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                    logger.debug(f"[{call_id}] Teler ping sent")
                except Exception:
                    break
        except asyncio.CancelledError:
            pass

    async def stream_tts(text: str):
        """Stream TTS audio — stops immediately on barge-in."""
        nonlocal is_speaking
        is_speaking = True
        barge_in_event.clear()
        try:
            async for audio_chunk_b64 in tts.synthesise_stream(text):
                if barge_in_event.is_set():
                    logger.info(f"[{call_id}] Barge-in — TTS stopped")
                    await clear_buffer()
                    break
                await send_audio(audio_chunk_b64)
        finally:
            is_speaking = False

    async def on_transcript(text: str):
        if not text.strip():
            return
        logger.info(f"[{call_id}] USER: {text}")
        reply, should_hangup = await agent.process(text)
        logger.info(f"[{call_id}] ANJALI: {reply}")
        await stream_tts(reply)
        if should_hangup:
            logger.info(f"[{call_id}] Hangup requested — closing")
            await websocket.close()

    async def on_barge_in():
        if is_speaking:
            logger.info(f"[{call_id}] Barge-in detected")
            barge_in_event.set()
            await clear_buffer()

    ping_task = asyncio.create_task(teler_ping_loop())

    try:
        async with stt.connect(on_transcript=on_transcript, on_barge_in=on_barge_in) as dg_session:
            greeting_sent = False
            async for message in websocket.iter_text():
                try:
                    msg = json.loads(message)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type")

                if msg_type == "start":
                    logger.info(f"[{call_id}] Stream started: {msg.get('data', {})}")
                    if not greeting_sent:
                        greeting_sent = True
                        greeting = agent.greeting()
                        logger.info(f"[{call_id}] ANJALI (greeting): {greeting}")
                        await stream_tts(greeting)

                elif msg_type == "audio":
                    audio_b64 = msg.get("data", {}).get("audio_b64", "")
                    if audio_b64:
                        raw_pcm = base64.b64decode(audio_b64)
                        await dg_session.send(raw_pcm)

    except WebSocketDisconnect:
        logger.info(f"[{call_id}] WebSocket disconnected")
    except Exception as e:
        logger.exception(f"[{call_id}] Unhandled error: {e}")
    finally:
        ws_closed = True
        ping_task.cancel()
        duration      = round(time.time() - call_state.get("started_at", time.time()), 1)
        caller_number = call_state.get("from_number") or call_state.get("to_number", "Unknown")
        logger.info(f"[{call_id}] Bridge closed. Duration={duration}s  Leads: {call_state.get('leads')}")

        # ── WhatsApp notification fallback (if Teler webhook fired before WS closed) ──
        # Only sends if /webhook hasn't already notified (notified flag guards double-send)
        if call_id in active_calls and not call_state.get("notified"):
            call_state["notified"] = True
            active_calls.pop(call_id, None)
            await send_call_notification(
                caller_number=caller_number,
                duration_seconds=duration,
            )