#!/usr/bin/env python
"""
Test Purelymail SMTP connection
"""

from providers.smtp import SMTPProvider

def test_purelymail():
    print("="*60)
    print("PURELYMAIL SMTP TEST")
    print("="*60)
    
    # Get credentials from user
    print("\nEnter your Purelymail credentials:")
    email = input("Email: ").strip()
    password = input("Password: ").strip()
    
    if not email or not password:
        print("❌ Email and password required")
        return
    
    credentials = {
        'host': 'smtp.purelymail.com',
        'port': 587,
        'username': email,
        'password': password
    }
    
    print("\n🔄 Testing connection to smtp.purelymail.com:587...")
    
    try:
        provider = SMTPProvider(credentials)
        result = provider.verify()
        
        if result['success']:
            print("✅ SUCCESS! Purelymail SMTP connection verified")
            print(f"   Authenticated as: {email}")
            
            # Ask if they want to send a test email
            send_test = input("\nSend a test email? (y/n): ").strip().lower()
            if send_test == 'y':
                to_email = input("Send to (email): ").strip()
                if to_email:
                    print(f"\n📧 Sending test email to {to_email}...")
                    result = provider.send(
                        from_email=email,
                        to_email=to_email,
                        subject="Test Email from Lapslie Email Platform",
                        html_body="<h1>Success!</h1><p>Your Purelymail SMTP is working correctly.</p>",
                        text_body="Success! Your Purelymail SMTP is working correctly."
                    )
                    
                    if result['success']:
                        print("✅ Test email sent successfully!")
                    else:
                        print(f"❌ Failed to send: {result.get('error')}")
        else:
            print(f"❌ FAILED: {result.get('error')}")
            print("\nTroubleshooting:")
            print("  1. Check your email and password")
            print("  2. Ensure SMTP is enabled in Purelymail")
            print("  3. Try an app-specific password if available")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == '__main__':
    test_purelymail()
