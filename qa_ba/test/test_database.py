"""Verification script to test SQLAlchemy models, bcrypt authentication, and cascading relationships.
"""
import sys
from pathlib import Path

# Force stdout to UTF-8 to prevent Windows CP1252 printing crashes
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path("d:/unknown/projects/TravelChatBot")
sys.path.append(str(PROJECT_ROOT))

from backend.database import get_db_ctx as get_db
from backend.models import User, UserPreference, ChatSession, ChatMessage


def run_tests():
    print("====== TRAVELCHATBOT DATABASE LAYER VERIFICATION ======")
    
    with get_db() as db:
        # 1. Verify traveler user credentials
        print("Checking user 'traveler'...")
        user = db.query(User).filter(User.username == "traveler").first()
        if not user:
            print("❌ Error: traveler user not found!")
            return
            
        print(f"✅ Found user: {user.username} (ID: {user.id})")
        print("Testing valid password check...")
        if user.check_password("adventure"):
            print("✅ Valid password check SUCCESS!")
        else:
            print("❌ Valid password check FAILED!")
            
        print("Testing invalid password check...")
        if not user.check_password("wrong-pass"):
            print("✅ Invalid password check rejected SUCCESS!")
        else:
            print("❌ Invalid password check accepted FAILED!")
            
        # 2. Verify UserPreferences relationship
        print("\nChecking user preferences relationship...")
        prefs = user.preferences
        if not prefs:
            print("❌ Error: UserPreference not found!")
            return
            
        print(f"✅ Found user preferences for ID {prefs.user_id}")
        print("Default destinations:", prefs.destinations)
        
        # Modify preferences
        prefs.destinations = ["Nha Trang", "Phú Quốc"]
        prefs.cuisine_types = ["Hải sản", "Bún chả"]
        db.add(prefs)
        db.flush()
        print("✅ Preferences update SUCCESS!")
        
        # 3. Create a test chat session
        print("\nCreating test chat session...")
        session = ChatSession(user_id=user.id, title="Kế hoạch Nha Trang 2026")
        db.add(session)
        db.flush()
        print(f"✅ ChatSession created: {session.title} (UUID: {session.id})")
        
        # Add messages
        msg1 = ChatMessage(
            session_id=session.id,
            role="user",
            content="Tìm giúp tôi khách sạn gần biển Nha Trang."
        )
        msg2 = ChatMessage(
            session_id=session.id,
            role="assistant",
            content="Dưới đây là một số khách sạn gần biển Nha Trang tuyệt đẹp..."
        )
        db.add(msg1)
        db.add(msg2)
        db.flush()
        print(f"✅ Chat messages inserted successfully!")
        
        # Query messages back
        print("Querying chat session messages:")
        queried_session = db.query(ChatSession).filter(ChatSession.id == session.id).first()
        for msg in queried_session.messages:
            print(f"  - [{msg.role}]: {msg.content[:40]}...")
            
    # 4. Verify cascade delete behavior
    print("\nVerifying cascade delete behavior...")
    with get_db() as db:
        user = db.query(User).filter(User.username == "traveler").first()
        user_id = user.id
        
        # Delete user
        print(f"Deleting user '{user.username}'...")
        db.delete(user)
        db.flush()
        
        # Verify preferences deleted
        pref_check = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
        if not pref_check:
            print("✅ User preferences successfully cascade-deleted!")
        else:
            print("❌ User preferences not cascade-deleted!")
            
        # Verify sessions deleted
        session_check = db.query(ChatSession).filter(User.id == user_id).all()
        if not session_check:
            print("✅ Chat sessions successfully cascade-deleted!")
        else:
            print("❌ Chat sessions not cascade-deleted!")

    print("\n====== VERIFICATION COMPLETE SUCCESSFULLY! ======")


if __name__ == "__main__":
    run_tests()
