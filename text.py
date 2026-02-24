import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import time
import re

class BulkEmailSenderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Bulk Email Dispatcher")
        self.root.geometry("700x650")
        self.root.configure(bg="#f0f2f5")

        # Variables
        self.smtp_server = tk.StringVar(value="smtp.gmail.com")
        self.smtp_port = tk.StringVar(value="587")
        self.email_user = tk.StringVar()
        self.email_pass = tk.StringVar()
        self.subject = tk.StringVar()
        self.delay = tk.IntVar(value=3) # Delay in seconds
        self.is_sending = False

        # Styles
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabel", background="#f0f2f5", font=("Arial", 10))
        style.configure("TButton", font=("Arial", 10, "bold"))
        style.configure("Header.TLabel", font=("Arial", 14, "bold"), foreground="#333")

        self.create_widgets()

    def create_widgets(self):
        # --- Header ---
        header_frame = ttk.Frame(self.root, padding="10")
        header_frame.pack(fill=tk.X)
        ttk.Label(header_frame, text="Bulk Email System", style="Header.TLabel").pack()
        ttk.Label(header_frame, text="Manage and send mass emails efficiently.", style="TLabel").pack()

        # --- Main Container (Notebook/Tabs) ---
        notebook = ttk.Notebook(self.root)
        notebook.pack(expand=True, fill="both", padx=10, pady=5)

        # Tab 1: Configuration
        self.config_frame = ttk.Frame(notebook, padding="20")
        notebook.add(self.config_frame, text="1. Server Settings")
        self.build_config_tab()

        # Tab 2: Recipients
        self.recipients_frame = ttk.Frame(notebook, padding="20")
        notebook.add(self.recipients_frame, text="2. Recipients")
        self.build_recipients_tab()

        # Tab 3: Compose
        self.compose_frame = ttk.Frame(notebook, padding="20")
        notebook.add(self.compose_frame, text="3. Compose & Send")
        self.build_compose_tab()

        # --- Status Bar ---
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=5)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def build_config_tab(self):
        grid_opts = {'padx': 5, 'pady': 5, 'sticky': tk.W}
        
        ttk.Label(self.config_frame, text="SMTP Server Provider:", font=("Arial", 11, "bold")).grid(row=0, column=0, **grid_opts)
        
        ttk.Label(self.config_frame, text="Server Address (e.g., smtp.gmail.com):").grid(row=1, column=0, **grid_opts)
        ttk.Entry(self.config_frame, textvariable=self.smtp_server, width=30).grid(row=1, column=1, **grid_opts)

        ttk.Label(self.config_frame, text="Port (usually 587 or 465):").grid(row=2, column=0, **grid_opts)
        ttk.Entry(self.config_frame, textvariable=self.smtp_port, width=10).grid(row=2, column=1, **grid_opts)

        ttk.Separator(self.config_frame, orient='horizontal').grid(row=3, column=0, columnspan=2, sticky="ew", pady=15)

        ttk.Label(self.config_frame, text="Your Credentials:", font=("Arial", 11, "bold")).grid(row=4, column=0, **grid_opts)

        ttk.Label(self.config_frame, text="Your Email Address:").grid(row=5, column=0, **grid_opts)
        ttk.Entry(self.config_frame, textvariable=self.email_user, width=30).grid(row=5, column=1, **grid_opts)

        ttk.Label(self.config_frame, text="Password (or App Password):").grid(row=6, column=0, **grid_opts)
        self.pass_entry = ttk.Entry(self.config_frame, textvariable=self.email_pass, width=30, show="*")
        self.pass_entry.grid(row=6, column=1, **grid_opts)
        
        # Show password checkbox
        self.show_pass = tk.BooleanVar()
        ttk.Checkbutton(self.config_frame, text="Show Password", variable=self.show_pass, command=self.toggle_password).grid(row=7, column=1, sticky=tk.W)

        ttk.Label(self.config_frame, text="Note: If using Gmail, you likely need to generate an \n'App Password' in your Google Account Security settings.", foreground="gray").grid(row=8, column=0, columnspan=2, pady=20, sticky=tk.W)

    def build_recipients_tab(self):
        ttk.Label(self.recipients_frame, text="Enter Recipients (One per line):", font=("Arial", 10, "bold")).pack(anchor=tk.W)

        self.recipients_text = scrolledtext.ScrolledText(self.recipients_frame, height=15, width=60)
        self.recipients_text.pack(pady=10, fill=tk.BOTH, expand=True)

        ttk.Label(self.recipients_frame, text="Format: email, Name  (e.g. admissions@mit.edu, MIT)").pack(anchor=tk.W)

        # Example button to clean list
        ttk.Button(self.recipients_frame, text="Clean & Validate List", command=self.validate_emails).pack(pady=5, anchor=tk.E)

    def build_compose_tab(self):
        ttk.Label(self.compose_frame, text="Subject:").pack(anchor=tk.W)
        ttk.Entry(self.compose_frame, textvariable=self.subject, width=60).pack(fill=tk.X, pady=(0, 10))

        ttk.Label(self.compose_frame, text="Message Body (use {name} for the university name):").pack(anchor=tk.W)
        self.body_text = scrolledtext.ScrolledText(self.compose_frame, height=10)
        self.body_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        controls_frame = ttk.Frame(self.compose_frame)
        controls_frame.pack(fill=tk.X)

        ttk.Label(controls_frame, text="Delay between emails (seconds):").pack(side=tk.LEFT)
        ttk.Entry(controls_frame, textvariable=self.delay, width=5).pack(side=tk.LEFT, padx=5)

        self.send_btn = ttk.Button(controls_frame, text="SEND ALL EMAILS", command=self.start_sending_thread)
        self.send_btn.pack(side=tk.RIGHT)

        # Log area
        ttk.Label(self.compose_frame, text="Transmission Log:", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(10, 0))
        self.log_text = scrolledtext.ScrolledText(self.compose_frame, height=6, state='disabled', font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, pady=(5, 0))

    def toggle_password(self):
        if self.show_pass.get():
            self.pass_entry.config(show="")
        else:
            self.pass_entry.config(show="*")

    def log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def parse_recipients(self, raw_data):
        """Parse lines of 'email, Name' or just 'email'. Returns list of (email, name) tuples."""
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

    def validate_emails(self):
        raw_data = self.recipients_text.get("1.0", tk.END)
        recipients = self.parse_recipients(raw_data)

        self.recipients_text.delete("1.0", tk.END)
        self.recipients_text.insert(tk.END, "\n".join(f"{email}, {name}" for email, name in recipients))
        self.status_var.set(f"List cleaned. Found {len(recipients)} unique valid emails.")

    def start_sending_thread(self):
        if self.is_sending:
            return
        
        # Validation
        if not self.email_user.get() or not self.email_pass.get():
            messagebox.showerror("Error", "Please enter your credentials in the Settings tab.")
            return
        
        recipients_raw = self.recipients_text.get("1.0", tk.END).strip()
        if not recipients_raw:
            messagebox.showerror("Error", "Please add recipients.")
            return

        recipients = self.parse_recipients(recipients_raw)

        if not messagebox.askyesno("Confirm", f"Are you sure you want to send this email to {len(recipients)} recipients?"):
            return

        self.is_sending = True
        self.send_btn.config(state='disabled')
        self.log("--- Starting Batch Process ---")
        
        # Start thread
        threading.Thread(target=self.send_emails, args=(recipients,), daemon=True).start()

    def send_emails(self, recipients):
        smtp_server = self.smtp_server.get()
        smtp_port = int(self.smtp_port.get())
        sender_email = self.email_user.get()
        password = self.email_pass.get()
        subject = self.subject.get()
        body = self.body_text.get("1.0", tk.END)
        delay = self.delay.get()

        context = ssl.create_default_context()

        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls(context=context)
            self.log(f"Connecting to {smtp_server}...")
            server.login(sender_email, password)
            self.log("Login Successful.")

            count = 0
            total = len(recipients)

            for email_to, name in recipients:
                if not self.is_sending: break # Safety break if needed

                personalized_body = body.replace("{name}", name)

                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = email_to
                msg['Subject'] = subject
                msg.attach(MIMEText(personalized_body, 'plain'))

                try:
                    server.sendmail(sender_email, email_to, msg.as_string())
                    count += 1
                    self.log(f"[{count}/{total}] Sent to: {email_to} ({name})")
                    self.status_var.set(f"Progress: {count}/{total} sent")
                except Exception as e:
                    self.log(f"[ERROR] Failed to send to {email_to}: {e}")

                # Rate limiting pause
                time.sleep(delay)

            self.log("--- Batch Complete ---")
            server.quit()

        except Exception as e:
            self.log(f"CRITICAL ERROR: {e}")
            messagebox.showerror("Connection Error", str(e))

        self.is_sending = False
        self.root.after(0, lambda: self.send_btn.config(state='normal'))
        self.root.after(0, lambda: self.status_var.set("Ready"))

if __name__ == "__main__":
    root = tk.Tk()
    app = BulkEmailSenderApp(root)
    root.mainloop()