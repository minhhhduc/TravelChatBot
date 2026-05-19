"""TravelChatBot coordinator implementation.

This package hosts the actual Chatbot orchestration logic so the public
module can stay thin and the pipeline can be split into smaller units.
"""
from __future__ import annotations

from typing import Optional
from dotenv import load_dotenv
import os
import unicodedata

from ..genai_client import GeminiClient
from ..chromadb import db_manager
from .. import config


TRAVEL_RELATED_KEYWORDS = {
    "du lich",
    "du ngoan",
    "lich trinh",
    "hanh trinh",
    "di dau",
    "di choi",
    "tham quan",
    "kham pha",
    "check in",
    "dia diem",
    "diem den",
    "danh lam",
    "khu vui choi",
    "vinwonders",
    "vinpearl",
    "bai bien",
    "bien dao",
    "dao",
    "nui",
    "thac",
    "hang dong",
    "chua",
    "den",
    "pho co",
    "bao tang",
    "cho dem",
    "am thuc",
    "dac san",
    "mon an",
    "an gi",
    "quan an",
    "nha hang",
    "cafe",
    "ca phe",
    "khach san",
    "resort",
    "homestay",
    "luu tru",
    "nghi duong",
    "ve may bay",
    "tau",
    "xe khach",
    "di chuyen",
    "phuong tien",
    "gia ve",
    "ve vao cong",
    "chi phi",
    "thoi tiet",
    "mua nao",
    "nen di",
    "travel",
    "trip",
    "tourism",
    "tourist",
    "itinerary",
    "destination",
    "hotel",
    "resort",
    "restaurant",
    "food",
    "flight",
    "transport",
    "ticket",
    "weather",
}

TRAVEL_DESTINATION_KEYWORDS = {
    "viet nam",
    "vietnam",
    "ha noi",
    "sai gon",
    "ho chi minh",
    "da nang",
    "hoi an",
    "hue",
    "nha trang",
    "da lat",
    "phu quoc",
    "ha long",
    "sapa",
    "sa pa",
    "ninh binh",
    "quy nhon",
    "phan thiet",
    "mui ne",
    "con dao",
    "vung tau",
    "can tho",
    "an giang",
    "kien giang",
    "quang ninh",
    "binh dinh",
    "khanh hoa",
    "lam dong",
}

TRAVEL_UNRELATED_RESPONSE_VI = (
    "Mình chỉ hỗ trợ các câu hỏi liên quan đến du lịch như gợi ý điểm đến, "
    "lịch trình, ăn uống, khách sạn, phương tiện di chuyển, chi phí hoặc kinh nghiệm đi chơi. "
    "Bạn có thể hỏi ví dụ: \"Đi Nha Trang 3 ngày nên đi đâu?\" hoặc "
    "\"Ở Đà Nẵng nên ăn gì và di chuyển thế nào?\""
)


def _normalize_for_scope_check(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def _is_travel_related_query(text: str) -> bool:
    normalized = _normalize_for_scope_check(text)
    return any(keyword in normalized for keyword in TRAVEL_RELATED_KEYWORDS | TRAVEL_DESTINATION_KEYWORDS)


class Chatbot:
    """CoordinatorAgent for the 6-agent TravelChatBot architecture."""

    def __init__(self):
        from pathlib import Path

        load_dotenv()
        local_env = Path(__file__).resolve().parent.parent / ".env"
        legacy_env = config.BASE_DIR / "backend" / "ai_module" / "models" / ".env"
        for env_path in (local_env, legacy_env):
            if env_path.exists():
                load_dotenv(dotenv_path=env_path)

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY or API_KEY not found in environment variables.")

        self.gemini_client = GeminiClient(api_key=api_key)
        self.db_manager = db_manager

        from ..agents import VisionAgent, SpeechAgent, FusionAgent, RetrievalAgent, RecommendationAgent

        self.vision_agent = VisionAgent(self.gemini_client)
        self.speech_agent = SpeechAgent(self.gemini_client)
        self.fusion_agent = FusionAgent(self.gemini_client)
        self.retrieval_agent = RetrievalAgent(self.db_manager)
        self.recommendation_agent = RecommendationAgent(self.gemini_client)

        self._initialize_collection()
        self.conversation_buffer = []

    def _initialize_collection(self) -> None:
        collection = self.db_manager.get_or_create_collection(config.CHROMA_COLLECTION_NAME)
        if collection.count() == 0:
            print(f"INFO: Collection '{config.CHROMA_COLLECTION_NAME}' is empty. Ingesting dataset...")
            added = self.db_manager.add_travel_guides_to_collection(config.CHROMA_COLLECTION_NAME)
            print(f"SUCCESS: Added {added} documents to ChromaDB collection '{config.CHROMA_COLLECTION_NAME}'.")
        else:
            print(f"INFO: Collection '{config.CHROMA_COLLECTION_NAME}' already contains {collection.count()} documents.")

    def get_response(
        self,
        user_query: str,
        image_path: Optional[str] = None,
        audio_path: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> str:
        print(f"User: {user_query}")

        if config.APP_MODE != "travel":
            raise NotImplementedError("Only APP_MODE=travel is supported in this workspace.")

        resolved_query = user_query
        if user_query and self.conversation_buffer:
            resolved_query = self.gemini_client.rewrite_query_with_context(user_query, self.conversation_buffer)

        image_description_vi = self.vision_agent.describe_image(image_path) if image_path else ""
        speech_text_raw = self.speech_agent.transcribe_audio(audio_path) if audio_path else ""

        user_text_for_lang = (resolved_query or speech_text_raw or "").strip()
        query_base_vi, user_lang = self.gemini_client.to_vietnamese(user_text_for_lang)

        speech_text_vi = ""
        if speech_text_raw:
            speech_text_vi, _speech_lang = self.gemini_client.to_vietnamese(speech_text_raw)

        fused_query_vi = self.fusion_agent.fuse_inputs(query_base_vi, image_description_vi, speech_text_vi)

        if not _is_travel_related_query(fused_query_vi):
            print("INFO: Query is outside travel scope. Skipping retrieval.")
            response = self.gemini_client.from_vietnamese(TRAVEL_UNRELATED_RESPONSE_VI, target_language=user_lang)
            self.conversation_buffer.append({"role": "user", "text": user_query or speech_text_raw or "(multimodal request)"})
            self.conversation_buffer.append({"role": "assistant", "text": response})
            if len(self.conversation_buffer) > 20:
                self.conversation_buffer = self.conversation_buffer[-20:]
            return response

        rag_context = self.retrieval_agent.retrieve_context(
            prompt=fused_query_vi,
            limit=5,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        response_vi = self.recommendation_agent.generate_recommendations(
            prompt=fused_query_vi,
            context=rag_context.get("context", ""),
        )

        response = self.gemini_client.from_vietnamese(response_vi, target_language=user_lang)

        self.conversation_buffer.append({"role": "user", "text": user_query or speech_text_raw or "(multimodal request)"})
        self.conversation_buffer.append({"role": "assistant", "text": response})
        if len(self.conversation_buffer) > 20:
            self.conversation_buffer = self.conversation_buffer[-20:]

        return response

    def reset_conversation(self):
        self.gemini_client.reset_chat_session()
        self.conversation_buffer = []
        print("💬 Conversation reset")

    def start_chat(self):
        print("Chatbot initialized. Type 'quit' to exit.")
        while True:
            user_input = input("You: ")
            if user_input.lower() == 'quit':
                print("Exiting chat.")
                break
            self.get_response(user_input)


def main():
    chatbot = Chatbot()
    chatbot.start_chat()
