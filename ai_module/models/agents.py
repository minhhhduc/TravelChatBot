"""Specialized helper agents for TravelChatBot.

This module contains the five sub-agents under the CoordinatorAgent:
1. VisionAgent: Multimodal image understanding
2. SpeechAgent: Voice/Audio transcription
3. FusionAgent: Input blending (Multimodal Fusion)
4. RetrievalAgent: Semantic DB search & sorting
5. RecommendationAgent: Travel recommendation generator

Author: TravelChatBot Team
Version: 2.0.0
"""
from typing import Optional, Dict, Any
import os
from google.genai import types

from .genai_client import GeminiClient
from .chromadb import ChromaDBManager
from . import prompt as prompts


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
            # Load raw image bytes
            with open(image_path, "rb") as f:
                image_bytes = f.read()

            image_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg" if image_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
            )

            instruction = (
                "Bạn là Vision Agent. Hãy mô tả chi tiết địa danh, phong cảnh, món ăn, hoạt động du lịch "
                "hoặc nội dung có trong bức ảnh này bằng tiếng Việt. Tập trung vào các chi tiết hữu ích "
                "cho việc gợi ý hành trình hoặc thông tin du lịch."
            )

            response = self.client.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[image_part, instruction]
            )
            description = response.text.strip()
            print(f"✨ VisionAgent Description: '{description[:100]}...'")
            return description
        except Exception as e:
            print(f"⚠️  VisionAgent failed to analyze image: {e}")
            return ""


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

            # Determine mime type
            mime_type = "audio/mp3"
            if audio_path.lower().endswith(".wav"):
                mime_type = "audio/wav"
            elif audio_path.lower().endswith(".ogg"):
                mime_type = "audio/ogg"

            audio_part = types.Part.from_bytes(
                data=audio_bytes,
                mime_type=mime_type
            )

            instruction = (
                "Bạn là Speech Agent. Hãy nghe và ghi lại chính xác từng từ trong đoạn âm thanh này "
                "bằng tiếng Việt (hoặc tiếng Anh nếu người nói dùng tiếng Anh). Trả về duy nhất văn bản "
                "đoạn thoại, không thêm bất kỳ lời dẫn giải nào."
            )

            response = self.client.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[audio_part, instruction]
            )
            transcript = response.text.strip()
            print(f"✨ SpeechAgent Transcript: '{transcript}'")
            return transcript
        except Exception as e:
            print(f"⚠️  SpeechAgent failed to transcribe audio: {e}")
            return ""


class FusionAgent:
    """Agent for blending text query, image semantics, and speech transcriptions."""

    def __init__(self, gemini_client: GeminiClient):
        self.client = gemini_client

    def fuse_inputs(self, text_query: str, image_description: str, speech_text: str) -> str:
        """Combines multiple user modalities into a single comprehensive Vietnamese search prompt."""
        # If there's only text and no other modalities, keep it simple
        if not image_description and not speech_text:
            return text_query

        try:
            print("🔀 FusionAgent: Blending multimodal inputs...")
            prompt = prompts.get_fusion_prompt(text_query, image_description, speech_text)
            response = self.client.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            fused_query = response.text.strip()
            print(f"✨ FusionAgent Result: '{fused_query}'")
            return fused_query
        except Exception as e:
            print(f"⚠️  FusionAgent failed to fuse inputs: {e}")
            # Fallback to simple concatenation
            parts = [text_query]
            if speech_text:
                parts.append(speech_text)
            if image_description:
                parts.append(f"Mô tả hình ảnh: {image_description}")
            return " ".join([p for p in parts if p])


class RetrievalAgent:
    """Agent for querying the ChromaDB vector database with custom sorting support."""

    def __init__(self, db_manager: ChromaDBManager):
        self.db_manager = db_manager

    def retrieve_context(
        self, 
        prompt: str, 
        limit: int = 5, 
        sort_by: Optional[str] = None, 
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """Queries the vector database and performs programmatic post-retrieval metadata sorting."""
        try:
            print(f"🔍 RetrievalAgent: Querying ChromaDB for '{prompt}'...")
            
            # Map sort field to metadata keys
            sort_field = None
            if sort_by == "time":
                sort_field = "time"
            elif sort_by == "evaluate_mean":
                sort_field = "evaluate_mean"
            elif sort_by == "evaluate_count":
                sort_field = "evaluate_count"

            rag_context = self.db_manager.prepare_rag_context(
                collection_name="recipes",
                query_text=prompt,
                sort_by=sort_field,
                sort_order=sort_order,
                limit=limit
            )
            print(f"✨ RetrievalAgent: Found {rag_context.get('documents_found', 0)} matching documents.")
            return rag_context
        except Exception as e:
            print(f"⚠️  RetrievalAgent query failed: {e}")
            return {"context": "Error retrieving travel guides.", "sources": [], "documents_found": 0}


class RecommendationAgent:
    """Agent for synthesizing rich, premium travel guides and itineraries with images."""

    def __init__(self, gemini_client: GeminiClient):
        self.client = gemini_client

    def generate_recommendations(self, prompt: str, context: str) -> str:
        """Generates detailed, visually stunning Vietnamese travel recommendations using RAG."""
        try:
            print("✈️  RecommendationAgent: Generating premium travel itinerary...")
            recommendation_prompt = prompts.get_rag_recommendation_prompt(prompt, context)
            
            # Create a professional persona instructions
            system_instruction = (
                "Bạn là một travel concierge cao cấp. Hãy lập kế hoạch, giới thiệu hành trình "
                "hoặc điểm đến một cách lôi cuốn, giàu hình ảnh minh họa bằng markdown, và "
                "luôn nhiệt thành hỗ trợ."
            )
            
            response = self.client.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=recommendation_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7
                )
            )
            return response.text.strip()
        except Exception as e:
            print(f"⚠️  RecommendationAgent generation failed: {e}")
            return f"Xin lỗi, tôi gặp lỗi khi xây dựng cẩm nang du lịch: {e}"
