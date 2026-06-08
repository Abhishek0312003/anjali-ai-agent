"""
Deepgram Nova-3 STT — real-time streaming over WebSocket.

STRATEGY:
- Accumulate is_final chunks into pending_transcript
- Only fire on_transcript when UtteranceEnd arrives (user truly finished speaking)
- speech_final is IGNORED — it fires on natural mid-sentence pauses
- KeepAlive sent every 8s to prevent Deepgram 10s idle timeout
- on_barge_in fires on SpeechStarted (kept for future use, currently disabled in main.py)
"""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Callable, Awaitable

import websockets

from app.config import settings

logger = logging.getLogger("abhishek.stt")

KEEPALIVE_INTERVAL = 8


def _build_deepgram_url() -> str:
    return (
        "wss://api.deepgram.com/v1/listen"
        f"?model={settings.DEEPGRAM_MODEL}"
        f"&language={settings.DEEPGRAM_LANGUAGE}"
        "&encoding=linear16"
        "&sample_rate=8000"
        "&channels=1"
        "&punctuate=true"
        "&smart_format=true"
        "&interim_results=true"
        "&utterance_end_ms=2000"
        "&vad_events=true"
    )


class DeepgramSession:
    def __init__(self, ws, on_transcript: Callable, on_barge_in: Callable):
        self._ws = ws
        self._on_transcript = on_transcript
        self._on_barge_in = on_barge_in
        self._receiver_task: asyncio.Task | None = None
        self._keepalive_task: asyncio.Task | None = None
        self._speaking = False
        self._closed = False
        self._pending = ""    # accumulates is_final chunks until UtteranceEnd

    async def send(self, pcm_bytes: bytes):
        if self._closed:
            return
        try:
            await self._ws.send(pcm_bytes)
        except websockets.ConnectionClosed:
            if not self._closed:
                logger.info("Deepgram WS closed — stopping audio forwarding")
            self._closed = True

    async def _keepalive_loop(self):
        try:
            while not self._closed:
                await asyncio.sleep(KEEPALIVE_INTERVAL)
                if self._closed:
                    break
                try:
                    await self._ws.send(json.dumps({"type": "KeepAlive"}))
                    logger.debug("Deepgram: KeepAlive sent")
                except websockets.ConnectionClosed:
                    break
        except asyncio.CancelledError:
            pass

    async def _receive_loop(self):
        try:
            async for raw in self._ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type")

                if msg_type == "SpeechStarted":
                    if not self._speaking:
                        self._speaking = True
                        logger.debug("Deepgram: SpeechStarted → barge-in signal")
                        await self._on_barge_in()

                elif msg_type == "Results":
                    is_final = msg.get("is_final", False)
                    speech_final = msg.get("speech_final", False)
                    alt = msg.get("channel", {}).get("alternatives", [{}])[0]
                    transcript = alt.get("transcript", "")
                    confidence = alt.get("confidence", 0)

                    if transcript:
                        logger.debug(
                            f"Deepgram Results: is_final={is_final} "
                            f"speech_final={speech_final} "
                            f"confidence={confidence:.2f} "
                            f"text='{transcript}'"
                        )

                    # Accumulate confirmed final chunks
                    # Do NOT process on speech_final — it fires on natural pauses mid-sentence
                    if is_final and transcript:
                        self._pending = (self._pending + " " + transcript).strip()
                        logger.info(
                            f"Deepgram: chunk confirmed — "
                            f"accumulated='{self._pending}'"
                        )

                elif msg_type == "UtteranceEnd":
                    # User has truly stopped speaking — fire transcript now
                    final_text = self._pending.strip()
                    self._pending = ""
                    self._speaking = False
                    logger.info(f"Deepgram: UtteranceEnd — firing transcript='{final_text}'")
                    if final_text:
                        await self._on_transcript(final_text)
                    else:
                        logger.debug("Deepgram: UtteranceEnd with empty transcript — skipping")

                elif msg_type == "Metadata":
                    logger.info(f"Deepgram Metadata: {msg}")

                elif msg_type == "Error":
                    logger.error(f"Deepgram server Error: {msg}")

                else:
                    logger.debug(f"Deepgram unknown msg type='{msg_type}': {msg}")

        except websockets.ConnectionClosed as e:
            logger.info(f"Deepgram WS closed: code={e.code} reason={e.reason}")
            # Fire any pending transcript before closing
            if self._pending.strip():
                logger.info(f"Deepgram: WS closed with pending='{self._pending}' — firing")
                try:
                    await self._on_transcript(self._pending.strip())
                except Exception:
                    pass
        except Exception as e:
            logger.exception(f"Deepgram receive loop error: {e}")
        finally:
            self._closed = True

    def start(self):
        self._receiver_task = asyncio.create_task(self._receive_loop())
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())

    async def close(self):
        self._closed = True
        if self._keepalive_task:
            self._keepalive_task.cancel()
        if self._receiver_task:
            self._receiver_task.cancel()
        try:
            await self._ws.close()
        except Exception:
            pass


class DeepgramSTT:
    @asynccontextmanager
    async def connect(
        self,
        on_transcript: Callable[[str], Awaitable[None]],
        on_barge_in: Callable[[], Awaitable[None]],
    ):
        url = _build_deepgram_url()
        headers = {"Authorization": f"Token {settings.DEEPGRAM_API_KEY}"}

        key_preview = (settings.DEEPGRAM_API_KEY[:6] + "...") if settings.DEEPGRAM_API_KEY else "MISSING"
        logger.info(f"Deepgram connecting → {url}")
        logger.info(f"Deepgram key: {key_preview} (len={len(settings.DEEPGRAM_API_KEY)})")

        try:
            async with websockets.connect(url, extra_headers=headers) as ws:
                logger.info("Deepgram WS connected ✓")
                session = DeepgramSession(ws, on_transcript, on_barge_in)
                session.start()
                try:
                    yield session
                finally:
                    await session.close()

        except websockets.exceptions.InvalidStatusCode as e:
            logger.error(
                f"Deepgram rejected WS: HTTP {e.status_code} | "
                f"key_len={len(settings.DEEPGRAM_API_KEY)} | "
                f"url={url}"
            )
            raise
        except Exception as e:
            logger.error(f"Deepgram connect failed: {type(e).__name__}: {e}")
            raise