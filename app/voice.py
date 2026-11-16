"""Real-time Bidirectional Conversational Voice Engine using Google ADK Live."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.genai import types

from app import config
from app.agent import create_voice_agent

logger = logging.getLogger(__name__)


async def _distill_voice_memory(
    session_service: Any,
    memory_service: Any,
    app_name: str,
    user_id: str,
    session_id: str,
) -> None:
    """Distill completed voice session turns into NeonMemoryService in the background."""
    try:
        session = await session_service.get_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )
        if session and session.events:
            await memory_service.add_session_to_memory(session)
    except Exception as exc:
        logger.warning("Background voice memory distillation skipped: %s", exc)


async def handle_voice_websocket(
    websocket: WebSocket,
    user: dict[str, Any],
    session_id: str,
    app_name: str,
    session_service: Any,
    memory_service: Any,
) -> None:
    """Manage a bidirectional Gemini Live audio session over WebSocket."""
    user_id = user.get("user_id") or user["id"]

    # Ensure session exists in NeonSessionService
    existing = await session_service.get_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    if existing is None:
        await session_service.create_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )

    voice_agent = create_voice_agent()
    runner = Runner(
        agent=voice_agent,
        app_name=app_name,
        session_service=session_service,
        memory_service=memory_service,
    )

    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=[types.Modality.AUDIO],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=config.VOICE_NAME or "Aoede"
                )
            )
        ),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                silence_duration_ms=450,
                prefix_padding_ms=150,
            )
        ),
    )

    live_request_queue = LiveRequestQueue()

    await websocket.send_json(
        {
            "type": "ready",
            "session_id": session_id,
            "model": config.VOICE_MODEL,
            "voice": config.VOICE_NAME,
        }
    )

    async def upstream_task() -> None:
        """Read 16 kHz PCM audio bytes or JSON control messages from the browser."""
        try:
            while True:
                message = await websocket.receive()
                if message.get("type") == "websocket.disconnect":
                    break

                raw_bytes = message.get("bytes")
                if raw_bytes:
                    live_request_queue.send_realtime(
                        types.Blob(data=raw_bytes, mime_type="audio/pcm;rate=16000")
                    )
                    continue

                raw_text = message.get("text")
                if raw_text:
                    try:
                        payload = json.loads(raw_text)
                    except json.JSONDecodeError:
                        payload = {"type": "text", "text": raw_text}

                    msg_type = payload.get("type")
                    if msg_type == "text" and payload.get("text"):
                        live_request_queue.send_content(
                            types.Content(
                                role="user",
                                parts=[types.Part(text=str(payload["text"]))],
                            )
                        )
                    elif msg_type == "close":
                        break
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            logger.debug("Voice upstream stopped: %s", exc)
        finally:
            live_request_queue.close()

    async def downstream_task() -> None:
        """Stream Gemini Live audio, transcriptions, and tool events back to the browser."""
        try:
            async for event in runner.run_live(
                user_id=user_id,
                session_id=session_id,
                live_request_queue=live_request_queue,
                run_config=run_config,
            ):
                # Input / Output live transcriptions
                in_tr = getattr(event, "input_transcription", None)
                if in_tr and getattr(in_tr, "text", None):
                    await websocket.send_json(
                        {
                            "type": "input_transcript",
                            "text": in_tr.text,
                            "finished": bool(getattr(in_tr, "finished", False)),
                        }
                    )

                out_tr = getattr(event, "output_transcription", None)
                if out_tr and getattr(out_tr, "text", None):
                    await websocket.send_json(
                        {
                            "type": "output_transcript",
                            "text": out_tr.text,
                            "finished": bool(getattr(out_tr, "finished", False)),
                        }
                    )

                # Barge-in / interruption signal
                if getattr(event, "interrupted", False):
                    await websocket.send_json({"type": "interrupted"})

                # Audio chunks & tool calls inside event.content
                content = getattr(event, "content", None)
                if content and getattr(content, "parts", None):
                    for part in content.parts:
                        inline = getattr(part, "inline_data", None)
                        if inline and getattr(inline, "data", None):
                            mime = getattr(inline, "mime_type", "") or ""
                            if "audio" in mime or isinstance(inline.data, (bytes, bytearray)):
                                await websocket.send_bytes(bytes(inline.data))

                        fc = getattr(part, "function_call", None)
                        if fc and getattr(fc, "name", None):
                            await websocket.send_json(
                                {"type": "tool_call", "name": fc.name}
                            )

                if getattr(event, "turn_complete", False):
                    await websocket.send_json({"type": "turn_complete"})
                    asyncio.create_task(
                        _distill_voice_memory(
                            session_service,
                            memory_service,
                            app_name,
                            user_id,
                            session_id,
                        )
                    )
        except WebSocketDisconnect:
            pass
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("Voice downstream error: %s", exc, exc_info=True)
            try:
                await websocket.send_json({"type": "error", "detail": str(exc)})
            except Exception:
                pass

    up = asyncio.create_task(upstream_task())
    down = asyncio.create_task(downstream_task())
    try:
        done, pending = await asyncio.wait(
            {up, down}, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        for task in done:
            task.exception()
    finally:
        live_request_queue.close()
        asyncio.create_task(
            _distill_voice_memory(
                session_service, memory_service, app_name, user_id, session_id
            )
        )
