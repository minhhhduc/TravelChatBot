"""Recommendation agent for TravelChatBot."""

from __future__ import annotations

from google.genai import types

from ..genai_client import GeminiClient
from .. import prompt as prompts


class RecommendationAgent:
    """Agent for synthesizing practical travel suggestions and itineraries with images."""

    def __init__(self, gemini_client: GeminiClient):
        self.client = gemini_client

    def generate_recommendations(self, prompt: str, context: str) -> str:
        """Generates helpful Vietnamese travel suggestions using RAG."""
        try:
            print("✈️  RecommendationAgent: Generating travel suggestions...")
            recommendation_prompt = prompts.get_rag_recommendation_prompt(prompt, context)

            system_instruction = (
                "Bạn là trợ lý gợi ý du lịch của TravelChatBot. Hãy trả lời như một người bạn "
                "am hiểu du lịch: rõ ràng, thực tế, đúng nhu cầu người dùng, không quảng cáo, "
                "không ép mua tour/vé/phòng và không dùng giọng bán hàng."
            )

            response = self.client.client.models.generate_content(
                model=self.client.model,
                contents=recommendation_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                ),
            )
            return response.text.strip()
        except Exception as e:
            print(f"⚠️  RecommendationAgent generation failed: {e}")
            return f"Xin lỗi, tôi gặp lỗi khi xây dựng cẩm nang du lịch: {e}"
