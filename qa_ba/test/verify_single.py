import sys
from pathlib import Path

# Force stdout to UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path("d:/unknown/projects/TravelChatBot")
sys.path.append(str(PROJECT_ROOT))

from ai_module.models.chatbot import Chatbot

def test_single():
    print("====== TRAVELCHATBOT SINGLE QUERY TEST ======")
    bot = Chatbot()
    
    query = "VinWonders Nha Trang có gì hấp dẫn"
    print(f"\nQuerying chatbot: '{query}'...")
    response = bot.get_response(user_query=query)
    print("\n[RESPONSE]:\n", response)

if __name__ == "__main__":
    test_single()
