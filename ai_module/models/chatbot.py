"""Compatibility shim for the packaged TravelChatBot coordinator."""

from .chatbot_pipeline import Chatbot, main

__all__ = ["Chatbot", "main"]


if __name__ == "__main__":
    main()