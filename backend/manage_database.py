"""Database management utility and interactive CLI for TravelChatBot.

This module provides admin functions and a command-line interface to
initialize the database, register users with hashed passwords, reset
passwords, list users, and delete user profiles.

Author: TravelChatBot Team
Version: 1.0.0
"""
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import os
import argparse
from pathlib import Path
from sqlalchemy.orm import Session

# Add project root to sys.path to allow absolute imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.database import engine, get_db_ctx as get_db
from backend.models import Base, User, UserPreference, ChatSession, ChatMessage


def init_db() -> None:
    """Creates all database tables defined in the schema."""
    print("⏳ Starting database initialization...")
    try:
        # Create all tables in metadata
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully inside 'backend/database.db'!")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")


def create_user(username: str, password: str, email: str = None, role: str = "user") -> bool:
    """Registers a new user profile with secure password hashing and default preferences."""
    print(f"⏳ Creating user '{username}'...")
    
    with get_db() as db:
        # Check if user already exists
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"❌ Error: Username '{username}' already exists.")
            return False
            
        if email:
            existing_email = db.query(User).filter(User.email == email).first()
            if existing_email:
                print(f"❌ Error: Email '{email}' is already registered.")
                return False

        try:
            # Create user instance
            new_user = User(
                username=username,
                email=email,
                role=role,
                is_active=True
            )
            new_user.set_password(password)
            db.add(new_user)
            db.flush() # Flush to populate ID

            # Create default empty user preferences
            prefs = UserPreference(
                user_id=new_user.id,
                dietary_goals=[],
                preferred_ingredients=[],
                avoided_ingredients=[],
                cuisine_types=[],
                destinations=[]
            )
            db.add(prefs)
            
            print(f"✅ User '{username}' successfully registered with role '{role}' (ID: {new_user.id})!")
            return True
        except Exception as e:
            print(f"❌ Failed to create user: {e}")
            return False


def list_users() -> None:
    """Lists all user profiles currently registered in the database."""
    print("\n" + "=" * 70)
    print(f"{'ID':<5} | {'Username':<15} | {'Email':<25} | {'Role':<10} | {'Status':<8}")
    print("=" * 70)
    
    with get_db() as db:
        users = db.query(User).all()
        if not users:
            print("No users found.")
        for u in users:
            status = "Active" if u.is_active else "Inactive"
            email = u.email if u.email else "N/A"
            print(f"{u.id:<5} | {u.username:<15} | {email:<25} | {u.role:<10} | {status:<8}")
    print("=" * 70 + "\n")


def reset_password(username: str, new_password: str) -> bool:
    """Resets the password of an existing user securely."""
    print(f"⏳ Resetting password for user '{username}'...")
    
    with get_db() as db:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"❌ Error: User '{username}' not found.")
            return False
            
        try:
            user.set_password(new_password)
            print(f"✅ Password for user '{username}' updated successfully!")
            return True
        except Exception as e:
            print(f"❌ Failed to update password: {e}")
            return False


def delete_user(username: str) -> bool:
    """Deletes a user profile and all cascading relations (preferences, sessions)."""
    print(f"⏳ Deleting user '{username}'...")
    
    with get_db() as db:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"❌ Error: User '{username}' not found.")
            return False
            
        try:
            db.delete(user)
            print(f"✅ User '{username}' and all cascading chat history deleted successfully!")
            return True
        except Exception as e:
            print(f"❌ Failed to delete user: {e}")
            return False


def interactive_menu() -> None:
    """Starts the premium interactive command line management interface."""
    while True:
        print("\n" + "=" * 50)
        print("          TRAVELCHATBOT DATABASE MANAGER          ")
        print("=" * 50)
        print("1. Khởi tạo Cơ sở Dữ liệu (Create all tables)")
        print("2. Tạo Người dùng mới (Create User)")
        print("3. Hiển thị danh sách Người dùng (List Users)")
        print("4. Đổi mật khẩu Người dùng (Reset Password)")
        print("5. Xóa Người dùng (Delete User)")
        print("6. Thoát (Exit)")
        print("=" * 50)
        
        choice = input("Nhập lựa chọn của bạn (1-6): ").strip()
        
        if choice == "1":
            init_db()
        elif choice == "2":
            username = input("Username: ").strip()
            password = input("Password: ").strip()
            email = input("Email (optional, Enter to skip): ").strip()
            role = input("Role (user/admin, default 'user'): ").strip()
            
            if not username or not password:
                print("❌ Username and Password cannot be empty.")
                continue
                
            email_val = email if email else None
            role_val = role if role in ["user", "admin"] else "user"
            
            create_user(username, password, email_val, role_val)
        elif choice == "3":
            list_users()
        elif choice == "4":
            username = input("Username: ").strip()
            password = input("New Password: ").strip()
            if not username or not password:
                print("❌ Username and Password cannot be empty.")
                continue
            reset_password(username, password)
        elif choice == "5":
            username = input("Username to delete: ").strip()
            if not username:
                print("❌ Username cannot be empty.")
                continue
            confirm = input(f"⚠️  Are you sure you want to delete user '{username}'? This cannot be undone! (y/N): ").strip().lower()
            if confirm == "y":
                delete_user(username)
            else:
                print("Cancelled.")
        elif choice == "6":
            print("Tạm biệt!")
            break
        else:
            print("❌ Lựa chọn không hợp lệ. Vui lòng nhập từ 1 đến 6.")


def main() -> None:
    """Main routing function for argparse and command-line execution."""
    parser = argparse.ArgumentParser(description="TravelChatBot Database Management Tool")
    parser.add_argument("--init", action="store_true", help="Initialize database tables")
    parser.add_argument("--create-user", nargs=2, metavar=("USERNAME", "PASSWORD"), help="Create a standard user")
    parser.add_argument("--create-admin", nargs=2, metavar=("USERNAME", "PASSWORD"), help="Create an admin user")
    parser.add_argument("--list-users", action="store_true", help="List all users")
    parser.add_argument("--reset-password", nargs=2, metavar=("USERNAME", "NEW_PASSWORD"), help="Reset user password")
    parser.add_argument("--delete-user", metavar="USERNAME", help="Delete a user profile")
    
    args = parser.parse_args()
    
    # If arguments are passed, perform CLI action, otherwise launch interactive menu
    if any(vars(args).values()):
        if args.init:
            init_db()
        elif args.create_user:
            create_user(args.create_user[0], args.create_user[1], role="user")
        elif args.create_admin:
            create_user(args.create_admin[0], args.create_admin[1], role="admin")
        elif args.list_users:
            list_users()
        elif args.reset_password:
            reset_password(args.reset_password[0], args.reset_password[1])
        elif args.delete_user:
            delete_user(args.delete_user)
    else:
        interactive_menu()


if __name__ == "__main__":
    main()
