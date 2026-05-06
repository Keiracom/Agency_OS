"""Elliot Voice — Pipecat voice agent for investor calls.

Pipeline: Daily.co WebRTC → Deepgram STT → Anthropic Opus → ElevenLabs TTS

Spec: docs/voice/elliot_voice_build_spec_v1.md
"""

from __future__ import annotations

import logging
import os

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import EndFrame, LLMMessagesFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.anthropic import AnthropicLLMService
from pipecat.services.deepgram import DeepgramSTTService
from pipecat.services.elevenlabs import ElevenLabsTTSService
from pipecat.transports.services.daily import DailyParams, DailyTransport

from src.voice.kill_switch import KillSwitch
from src.voice.system_prompt import build_system_prompt

logger = logging.getLogger(__name__)


async def create_voice_agent(
    *,
    room_url: str,
    room_token: str | None = None,
    investor_briefing: str | None = None,
) -> PipelineTask:
    """Create and configure the Elliot Voice pipeline.

    Args:
        room_url: Daily.co room URL to join.
        room_token: Optional Daily.co token for authenticated rooms.
        investor_briefing: Optional per-call investor briefing text.

    Returns:
        Configured PipelineTask ready to run.
    """
    # ── Transport: Daily.co WebRTC (audio only) ──────────────────────────────
    transport = DailyTransport(
        room_url,
        room_token,
        "Elliot",
        DailyParams(
            audio_out_enabled=True,
            audio_in_enabled=True,
            camera_out_enabled=False,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
        ),
    )

    # ── STT: Deepgram Nova-3 (streaming, AU English) ─────────────────────────
    stt = DeepgramSTTService(
        api_key=os.environ.get("DEEPGRAM_API_KEY", ""),
        params=DeepgramSTTService.InputParams(
            model="nova-3",
            language="en-AU",
        ),
    )

    # ── LLM: Anthropic Opus (streaming, no extended thinking) ────────────────
    llm = AnthropicLLMService(
        api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        model="claude-opus-4-6",
        params=AnthropicLLMService.InputParams(
            enable_prompt_caching_beta=True,
        ),
    )

    # ── TTS: ElevenLabs (streaming, AU voice) ────────────────────────────────
    tts = ElevenLabsTTSService(
        api_key=os.environ.get("ELEVENLABS_API_KEY", ""),
        voice_id=os.environ.get("ELEVENLABS_VOICE_ID", ""),
        params=ElevenLabsTTSService.InputParams(
            stability=0.5,
            similarity_boost=0.75,
        ),
    )

    # ── System prompt + conversation context ─────────────────────────────────
    system_prompt = build_system_prompt(investor_briefing)
    messages = [
        {"role": "system", "content": system_prompt},
    ]

    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    # ── Kill switch ──────────────────────────────────────────────────────────
    KillSwitch()

    # ── Pipeline assembly ────────────────────────────────────────────────────
    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
        ),
    )

    # ── Event handlers ───────────────────────────────────────────────────────

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        """Greet with recording consent when first participant joins."""
        logger.info("Participant joined: %s", participant.get("id", "unknown"))
        # Send the recording consent as the first utterance
        consent_msg = (
            "For transparency, this conversation is being recorded for "
            "post-call summary generation — is that OK with you?"
        )
        messages.append({"role": "assistant", "content": consent_msg})
        await task.queue_frames([LLMMessagesFrame(messages)])

    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        """Clean shutdown when all participants leave."""
        logger.info("Participant left: %s (reason: %s)", participant.get("id"), reason)
        await task.queue_frames([EndFrame()])

    @transport.event_handler("on_call_state_updated")
    async def on_call_state_updated(transport, state):
        """Log call state changes."""
        logger.info("Call state: %s", state)

    return task


async def run_voice_agent(
    *,
    room_url: str,
    room_token: str | None = None,
    investor_briefing: str | None = None,
) -> None:
    """Run the Elliot Voice agent until the call ends.

    Args:
        room_url: Daily.co room URL.
        room_token: Optional authentication token.
        investor_briefing: Optional per-call briefing text.
    """
    task = await create_voice_agent(
        room_url=room_url,
        room_token=room_token,
        investor_briefing=investor_briefing,
    )
    runner = PipelineRunner()
    await runner.run(task)
