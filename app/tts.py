import asyncio
import base64
import logging
from typing import AsyncGenerator

from sarvamai import AsyncSarvamAI

from app.config import settings

logger = logging.getLogger("abhishek.tts")

CHUNK_BYTES = 8000
CHUNK_SLEEP = 0.48


class SarvamTTS:

    async def synthesise_stream(self, text: str) -> AsyncGenerator[str, None]:
        if not text.strip():
            return

        try:
            client = AsyncSarvamAI(api_subscription_key=settings.SARVAM_API_KEY)

            response = await client.text_to_speech.convert(
                text=text,
                target_language_code="en-IN",      # English-Indian — far better pronunciation, less robotic
                speaker=settings.SARVAM_SPEAKER,
                model=settings.SARVAM_TTS_MODEL,
                speech_sample_rate=settings.SARVAM_SAMPLE_RATE,
                output_audio_codec="linear16",
                pace=0.88,                          # slower = more natural, less robotic
            )

            for audio_b64 in response.audios:
                pcm_bytes = base64.b64decode(audio_b64)
                total_chunks = (len(pcm_bytes) + CHUNK_BYTES - 1) // CHUNK_BYTES

                logger.info(
                    f"TTS: pcm={len(pcm_bytes)}B chunks={total_chunks} "
                    f"duration={len(pcm_bytes)/16000:.1f}s"
                )

                for i, offset in enumerate(range(0, len(pcm_bytes), CHUNK_BYTES)):
                    chunk = pcm_bytes[offset:offset + CHUNK_BYTES]
                    yield base64.b64encode(chunk).decode()
                    if i < total_chunks - 1:
                        await asyncio.sleep(CHUNK_SLEEP)

        except Exception as e:
            logger.exception(f"Sarvam TTS error: {e}")

    async def synthesise_bytes(self, text: str) -> bytes:
        chunks = []
        async for chunk_b64 in self.synthesise_stream(text):
            chunks.append(base64.b64decode(chunk_b64))
        return b"".join(chunks)