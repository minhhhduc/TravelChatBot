"""Fusion agent for TravelChatBot."""

from __future__ import annotations

from ..genai_client import GeminiClient
from .. import prompt as prompts


class FusionAgent:
    """Agent for blending text query, image semantics, and speech transcriptions."""

    def __init__(self, gemini_client: GeminiClient):
        self.client = gemini_client

    def fuse_inputs(self, text_query: str, image_description: str, speech_text: str) -> str:
        """Combines multiple user modalities into a single comprehensive Vietnamese search prompt."""
        if not image_description and not speech_text:
            return text_query

        try:
            print("🔀 FusionAgent: Blending multimodal inputs...")
            prompt = prompts.get_fusion_prompt(text_query, image_description, speech_text)
            response = self.client.client.models.generate_content(
                model=self.client.model,
                contents=prompt,
            )
            fused_query = response.text.strip()
            print(f"✨ FusionAgent Result: '{fused_query}'")
            return fused_query
        except Exception as e:
            print(f"⚠️  FusionAgent failed to fuse inputs: {e}")
            parts = [text_query]
            if speech_text:
                parts.append(speech_text)
            if image_description:
                parts.append(f"Mô tả hình ảnh: {image_description}")
            return " ".join([p for p in parts if p])