#!/usr/bin/env python
"""
Manage user accounts - view, create, reset passwords
"""

from app_production import app, db
from models.user import User
from werkzeug.security import generate_password_hash

def list_users():
    with app.app_context():
        users = User.query.all()
        
        print("\n" + "="*70)
        print("ALL USER ACCOUNTS")
        print("="*70)
        
        if not users:
            print("No users found")
            return
        
        for user in users:
            print(f"\nID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Name: {user.name}")
            print(f"Send Limit: {user.send_limit}/day")
            print(f"Daily Sent: {user.daily_send_count}")
            print(f"Created: {user.created_at}")
            print("-"*70)

def create_user():
    with app.app_context():
        print("\n" + "="*70)
        print("CREATE NEW USER")
        print("="*70)
        
        email = input("Email: ").strip()
        password = input("Password: ").strip()
        name = input("Name (optional): ").strip() or email.split('@')[0]
        
        if not email or not password:
            print("❌ Email and password required")
            return
        
        existing = User.query.filter_by(email=email).first()
        if existing:
            print(f"❌ User with email {email} already exists")
            return
        
        user = User(
            email=email,
            name=name,
            google_id=generate_password_hash(password),
            send_limit=1000
        )
        db.session.add(user)
        db.session.commit()
        
        print(f"\n✅ User created successfully!")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   ID: {user.id}")

def reset_password():
    with app.app_context():
        print("\n" + "="*70)
        print("RESET PASSWORD")
        print("="*70)
        
        email = input("User email: ").strip()
        new_password = input("New password: ").strip()
        
        if not email or not new_password:
            print("❌ Email and password required")
            return
        
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"❌ User with email {email} not found")
            return
        
        user.google_id = generate_password_hash(new_password)
        db.session.commit()
        
        print(f"\n✅ Password reset successfully!")
        print(f"   Email: {email}")
        print(f"   New Password: {new_password}")

def main():
    print("\n" + "="*70)
    print("USER MANAGEMENT")
    print("="*70)
    print("\n1. List all users")
    print("2. Create new user")
    print("3. Reset password")
    print("4. Exit")
    
    choice = input("\nChoice (1-4): ").strip()
    
    if choice == '1':
        list_users()
    elif choice == '2':
        create_user()
    elif choice == '3':
        reset_password()
    elif choice == '4':
        print("Goodbye!")
        return
    else:
        print("Invalid choice")

if __name__ == '__main__':
    main()
