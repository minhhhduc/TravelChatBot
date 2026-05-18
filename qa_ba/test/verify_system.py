"""Scratch script to verify the 6-Agent TravelChatBot system, database indexing, and query sorting.
"""
import sys
from pathlib import Path

# Force stdout to UTF-8 to prevent CP1252 encoding crashes on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
PROJECT_ROOT = Path("d:/unknown/projects/TravelChatBot")
sys.path.append(str(PROJECT_ROOT))

from ai_module.models.chatbot import Chatbot

def test_system():
    print("====== TRAVELCHATBOT SYSTEM VERIFICATION ======")
    
    # 1. Initialize Chatbot (will trigger database loading and indexing if empty)
    print("Initializing Chatbot coordinator and agents...")
    bot = Chatbot()
    
    # 2. Check Database Size
    count = bot.db_manager.get_or_create_collection("recipes").count()
    print(f"\n[DB] ChromaDB Collection Spot Count: {count}")
    
    if count == 0:
        print("[FAIL] Error: ChromaDB contains 0 spots. Check raw.jsonl path and format.")
        return
        
    # 3. Test Text-Only Query
    print("\n--------------------------------------------------")
    print("Test 1: Standard Semantic Search Query")
    print("--------------------------------------------------")
    query = "VinWonders Nha Trang có gì hấp dẫn và giá vé bao nhiêu"
    response = bot.get_response(user_query=query)
    print(f"\n[RESPONSE]:\n{response}")
    
    # 4. Test Sorting by Time (Newest First)
    print("\n--------------------------------------------------")
    print("Test 2: Semantic Search sorted by published TIME")
    print("--------------------------------------------------")
    query = "địa điểm du lịch biển Nha Trang mới nhất"
    response = bot.get_response(user_query=query, sort_by="time", sort_order="desc")
    print(f"\n[RESPONSE]:\n{response}")
    
    # 5. Test Sorting by Rating (Highest Mean Rating First)
    print("\n--------------------------------------------------")
    print("Test 3: Semantic Search sorted by Mean RATING (evaluate_mean)")
    print("--------------------------------------------------")
    query = "khách sạn resort cao cấp hoặc điểm vui chơi được đánh giá tốt nhất Nha Trang"
    response = bot.get_response(user_query=query, sort_by="evaluate_mean", sort_order="desc")
    print(f"\n[RESPONSE]:\n{response}")
    
    # 6. Test Sorting by Review Count (Most Reviewed First)
    print("\n--------------------------------------------------")
    print("Test 4: Semantic Search sorted by REVIEW COUNT (evaluate_count)")
    print("--------------------------------------------------")
    query = "điểm tham quan ăn uống được review và quan tâm nhiều nhất Nha Trang"
    response = bot.get_response(user_query=query, sort_by="evaluate_count", sort_order="desc")
    print(f"\n[RESPONSE]:\n{response}")

if __name__ == "__main__":
    test_system()
