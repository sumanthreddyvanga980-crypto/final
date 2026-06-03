import os
import random
import sys
from flask_mail import Message
from app import mail

def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp_email(user_email, otp):
    try:
        msg = Message(
            subject="StudentHub Email Verification",
            sender=os.getenv("SMTP_USERNAME"),
            recipients=[user_email]
        )

        msg.body = f"""Welcome to StudentHub!

Your OTP verification code is: {otp}

This OTP is valid for 5 minutes.

Do not share this code with anyone.
"""
        mail.send(msg)
        return True
    except Exception as e:
        print("\n" + "="*60, file=sys.stderr)
        print(f"[DEVELOPMENT FALLBACK] Failed to send email to {user_email} via SMTP.", file=sys.stderr)
        print(f"Error detail: {str(e)}", file=sys.stderr)
        print(f"FOR TESTING, YOUR OTP VERIFICATION CODE IS: {otp}", file=sys.stderr)
        print("="*60 + "\n", file=sys.stderr)
        return False
