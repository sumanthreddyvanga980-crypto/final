import os
import random
from flask_mail import Message
from app import mail


def generate_otp():
    return str(random.randint(100000, 999999))


def send_otp_email(user_email, otp):
    try:
        sender_email = os.getenv("MAIL_USERNAME")

        if not sender_email:
            print("ERROR: MAIL_USERNAME is not configured.")
            return False

        msg = Message(
            subject="StudentHub Email Verification",
            sender=sender_email,
            recipients=[user_email]
        )

        msg.body = f"""Welcome to StudentHub!

Your OTP verification code is: {otp}

This OTP is valid for 5 minutes.

Do not share this code with anyone.

Regards,
StudentHub Team
"""

        mail.send(msg)

        print(f"OTP email successfully sent to {user_email}")
        return True

    except Exception as e:
        print(f"Failed to send OTP email: {str(e)}")
        return False
