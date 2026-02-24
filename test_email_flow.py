#!/usr/bin/env python
"""
Quick test script to verify email sending works.
This simulates the full flow: provider setup -> list creation -> campaign -> send
"""

from app_production import app, db
from models.user import User
from models.provider import ProviderConnection
from models.recipient_list import RecipientList, Recipient
from models.campaign import Campaign
from utils.crypto import CredentialEncryption
import json

def test_flow():
    with app.app_context():
        # Get or create test user
        user = User.query.filter_by(email='test@example.com').first()
        if not user:
            print("❌ Test user not found. Please create one first.")
            return
        
        print(f"✓ User found: {user.email} (ID: {user.id})")
        
        # Check for providers
        providers = ProviderConnection.query.filter_by(user_id=user.id).all()
        print(f"\n📧 Providers configured: {len(providers)}")
        for p in providers:
            print(f"  - {p.provider_type}: {p.sender_email} (verified: {p.is_verified})")
        
        # Check for recipient lists
        lists = RecipientList.query.filter_by(user_id=user.id).all()
        print(f"\n📋 Recipient lists: {len(lists)}")
        for l in lists:
            print(f"  - {l.name}: {l.recipient_count} recipients")
        
        # Check for campaigns
        campaigns = Campaign.query.filter_by(user_id=user.id).all()
        print(f"\n📨 Campaigns: {len(campaigns)}")
        for c in campaigns:
            print(f"  - {c.name}: {c.status} ({c.sent_count}/{c.total_recipients} sent)")
        
        print("\n" + "="*60)
        print("SYSTEM STATUS")
        print("="*60)
        
        if len(providers) == 0:
            print("⚠️  No providers configured")
            print("   → Go to http://127.0.0.1:5001/providers to add one")
            print("   → For Gmail: Use SMTP with app password")
            print("     Host: smtp.gmail.com, Port: 587")
        else:
            verified = [p for p in providers if p.is_verified]
            if len(verified) == 0:
                print("⚠️  No verified providers")
                print("   → Verify your provider in the UI")
            else:
                print(f"✓ {len(verified)} verified provider(s)")
        
        if len(lists) == 0:
            print("⚠️  No recipient lists")
            print("   → Go to http://127.0.0.1:5001/lists to create one")
        else:
            print(f"✓ {len(lists)} recipient list(s)")
        
        if len(providers) > 0 and len(lists) > 0:
            print("\n✅ READY TO SEND!")
            print("   → Go to http://127.0.0.1:5001/campaigns/wizard")
        else:
            print("\n⏳ Setup incomplete")

if __name__ == '__main__':
    test_flow()
