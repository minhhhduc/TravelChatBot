"""Speech agent for TravelChatBot."""

from __future__ import annotations

import os

from google.genai import types

from ..genai_client import GeminiClient


class SpeechAgent:
    """Agent for transcribing voice queries or audio reviews."""

    def __init__(self, gemini_client: GeminiClient):
        self.client = gemini_client

    def transcribe_audio(self, audio_path: str) -> str:
        """Transcribes local audio files to text using Gemini's native audio support."""
        if not audio_path or not os.path.exists(audio_path):
            print(f"⚠️  SpeechAgent: Audio file not found at: {audio_path}")
            return ""

        try:
            print(f"🎙️  SpeechAgent: Transcribing audio: {audio_path}...")
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()

            mime_type = "audio/mp3"
            if audio_path.lower().endswith(".wav"):
                mime_type = "audio/wav"
            elif audio_path.lower().endswith(".ogg"):
                mime_type = "audio/ogg"

            audio_part = types.Part.from_bytes(
                data=audio_bytes,
                mime_type=mime_type,
            )

            instruction = (
                "Bạn là Speech Agent. Hãy nghe và ghi lại chính xác từng từ trong đoạn âm thanh này "
                "bằng tiếng Việt (hoặc tiếng Anh nếu người nói dùng tiếng Anh). Trả về duy nhất văn bản "
                "đoạn thoại, không thêm bất kỳ lời dẫn giải nào."
            )

            model = self.client.model
            if "gemma" in model.lower():
                print(f"ℹ️  SpeechAgent: '{model}' is text-only. Falling back to 'models/gemini-2.5-flash' for transcription.")
                model = "models/gemini-2.5-flash"

            response = self.client.client.models.generate_content(
                model=model,
                contents=[audio_part, instruction],
            )
            transcript = response.text.strip()
            print(f"✨ SpeechAgent Transcript: '{transcript}'")
            return transcript
        except Exception as e:
            print(f"⚠️  SpeechAgent failed to transcribe audio: {e}")
            return ""