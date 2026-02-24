import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import re
import getpass

class BulkEmailSender:
    def __init__(self):
        self.smtp_server = ""
        self.smtp_port = 0
        self.email_user = ""
        self.email_pass = ""
        self.subject = ""
        self.body = ""
        self.recipients = []
        self.delay = 3

    def setup_smtp(self):
        print("\n=== SMTP Server Configuration ===")
        self.smtp_server = input("SMTP Server (e.g., smtp.gmail.com): ").strip() or "smtp.gmail.com"
        port_input = input("Port (default 587): ").strip()
        self.smtp_port = int(port_input) if port_input else 587
        
        print("\n=== Your Credentials ===")
        self.email_user = input("Your Email Address: ").strip()
        self.email_pass = getpass.getpass("Password (or App Password): ")
        
        print("\n✓ SMTP configuration saved")

    def add_recipients(self):
        print("\n=== Add Recipients ===")
        print("Enter recipients in format: email, Name")
        print("One per line. Press Enter twice when done.\n")
        
        lines = []
        while True:
            line = input().strip()
            if not line:
                break
            lines.append(line)
        
        self.recipients = self.parse_recipients("\n".join(lines))
        print(f"\n✓ Added {len(self.recipients)} valid recipients")

    def parse_recipients(self, raw_data):
        results = []
        seen = set()
        for line in raw_data.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(',', 1)
            email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', parts[0])
            if not email_match:
                continue
            email = email_match.group()
            name = parts[1].strip() if len(parts) > 1 else email
            if email not in seen:
                seen.add(email)
                results.append((email, name))
        return results

    def compose_email(self):
        print("\n=== Compose Email ===")
        self.subject = input("Subject: ").strip()
        
        print("\nMessage Body (use {name} for personalization):")
        print("Type your message. Press Enter twice when done.\n")
        
        body_lines = []
        empty_count = 0
        while empty_count < 2:
            line = input()
            if not line:
                empty_count += 1
            else:
                empty_count = 0
            body_lines.append(line)
        
        self.body = "\n".join(body_lines[:-2])  # Remove the two empty lines at end
        
        delay_input = input("\nDelay between emails in seconds (default 3): ").strip()
        self.delay = int(delay_input) if delay_input else 3
        
        print("\n✓ Email composed")

    def send_emails(self):
        if not self.recipients:
            print("\n✗ No recipients added!")
            return
        
        print(f"\n=== Ready to Send ===")
        print(f"Recipients: {len(self.recipients)}")
        print(f"Subject: {self.subject}")
        confirm = input("\nSend emails? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("Cancelled.")
            return

        context = ssl.create_default_context()

        try:
            print(f"\nConnecting to {self.smtp_server}...")
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls(context=context)
            server.login(self.email_user, self.email_pass)
            print("✓ Login successful\n")

            count = 0
            total = len(self.recipients)

            for email_to, name in self.recipients:
                personalized_body = self.body.replace("{name}", name)

                msg = MIMEMultipart()
                msg['From'] = self.email_user
                msg['To'] = email_to
                msg['Subject'] = self.subject
                msg.attach(MIMEText(personalized_body, 'plain'))

                try:
                    server.sendmail(self.email_user, email_to, msg.as_string())
                    count += 1
                    print(f"[{count}/{total}] ✓ Sent to: {email_to} ({name})")
                except Exception as e:
                    print(f"[{count}/{total}] ✗ Failed to send to {email_to}: {e}")

                time.sleep(self.delay)

            print(f"\n=== Complete ===")
            print(f"Successfully sent {count}/{total} emails")
            server.quit()

        except Exception as e:
            print(f"\n✗ ERROR: {e}")

    def run(self):
        print("=" * 50)
        print("     BULK EMAIL SENDER")
        print("=" * 50)
        
        while True:
            print("\n--- Main Menu ---")
            print("1. Configure SMTP Server")
            print("2. Add Recipients")
            print("3. Compose Email")
            print("4. Send Emails")
            print("5. Exit")
            
            choice = input("\nSelect option (1-5): ").strip()
            
            if choice == '1':
                self.setup_smtp()
            elif choice == '2':
                self.add_recipients()
            elif choice == '3':
                self.compose_email()
            elif choice == '4':
                self.send_emails()
            elif choice == '5':
                print("\nGoodbye!")
                break
            else:
                print("\n✗ Invalid option")

if __name__ == "__main__":
    sender = BulkEmailSender()
    sender.run()
