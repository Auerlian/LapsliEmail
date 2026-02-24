#!/usr/bin/env python
"""
Show all users and their login credentials
"""

from app_production import app, db
from models.user import User

def show_users():
    with app.app_context():
        users = User.query.all()
        
        print("="*70)
        print("USER ACCOUNTS")
        print("="*70)
        
        if not users:
            print("No users found")
            return
        
        for user in users:
            print(f"\nUser ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Password Hash: {user.password_hash[:50]}...")
            print(f"Send Limit: {user.send_limit}/day")
            print(f"Daily Sent: {user.daily_send_count}")
            print(f"Created: {user.created_at}")
            print("-"*70)
        
        print("\n" + "="*70)
        print("NOTE: Passwords are hashed with bcrypt for security")
        print("="*70)
        print("\nKNOWN TEST ACCOUNTS:")
        print("  Email: test@example.com")
        print("  Password: password123")
        print("\nTo reset a password, use: python reset_password.py")

if __name__ == '__main__':
    show_users()
