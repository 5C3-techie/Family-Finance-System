import smtplib
from email.message import EmailMessage
from config import SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD


def send_otp_email(email, otp):
    """Return True if OTP email was sent, False on failure."""
    msg = EmailMessage()
    msg['Subject'] = "Your Login OTP"
    msg['From'] = SENDER_EMAIL
    msg['To'] = email
    msg.set_content(f"Your OTP is {otp}")

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP authentication failed: {e}")
        return False
    except Exception as e:
        print(f"Failed to send OTP email: {e}")
        return False
    finally:
        print("Using Email:", SENDER_EMAIL)
        # Do not print password for security