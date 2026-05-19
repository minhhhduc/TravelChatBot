"""Vision agent for TravelChatBot."""

from __future__ import annotations

import os

from google.genai import types

from ..genai_client import GeminiClient


class VisionAgent:
    """Agent for extracting semantic descriptions from tourist/travel images."""

    def __init__(self, gemini_client: GeminiClient):
        self.client = gemini_client

    def describe_image(self, image_path: str) -> str:
        """Translates a local image into a detailed semantic description using Gemini."""
        if not image_path or not os.path.exists(image_path):
            print(f"⚠️  VisionAgent: Image file not found at: {image_path}")
            return ""

        try:
            print(f"🖼️  VisionAgent: Analyzing image: {image_path}...")
            with open(image_path, "rb") as f:
                image_bytes = f.read()

            image_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg" if image_path.lower().endswith((".jpg", ".jpeg")) else "image/png",
            )

            instruction = (
                "Bạn là Vision Agent. Hãy mô tả chi tiết địa danh, phong cảnh, món ăn, hoạt động du lịch "
                "hoặc nội dung có trong bức ảnh này bằng tiếng Việt. Tập trung vào các chi tiết hữu ích "
                "cho việc gợi ý hành trình hoặc thông tin du lịch."
            )

            model = self.client.model
            if "gemma" in model.lower():
                print(f"ℹ️  VisionAgent: '{model}' is text-only. Falling back to 'models/gemini-2.5-flash' for vision analysis.")
                model = "models/gemini-2.5-flash"

            response = self.client.client.models.generate_content(
                model=model,
                contents=[image_part, instruction],
            )
            description = response.text.strip()
            print(f"✨ VisionAgent Description: '{description[:100]}...'")
            return description
        except Exception as e:
            print(f"⚠️  VisionAgent failed to analyze image: {e}")
            return ""