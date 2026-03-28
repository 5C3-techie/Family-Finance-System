import bcrypt
import sqlite3
from datetime import datetime
from database import get_db_connection
from services.otp_service import generate_otp
from utils.email_utils import send_otp_email

def register_user(name, email, password, role):
    conn = get_db_connection()

    existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if existing:
        conn.close()
        return False

    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode(), salt).decode()

    try:
        conn.execute(
            "INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
            (name, email, hashed_password, role)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(email, password):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()

    if user and bcrypt.checkpw(password.encode(), user['password'].encode()):
        otp, expiry = generate_otp()

        conn = get_db_connection()
        conn.execute(
            "UPDATE users SET otp=?, otp_expiry=? WHERE id=?",
            (otp, expiry, user['id'])
        )
        conn.commit()
        conn.close()

        if not send_otp_email(user['email'], otp):
            return None

        return user

    return None

def verify_user_otp(user_id, entered_otp):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

    if not user:
        conn.close()
        return None

    if user['otp'] != entered_otp:
        conn.close()
        return None

    if user['otp_expiry']:
        try:
            otp_expiry = datetime.strptime(user['otp_expiry'], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            otp_expiry = None

        if otp_expiry and otp_expiry < datetime.now():
            conn.close()
            return None

    conn.execute("UPDATE users SET otp=NULL, otp_expiry=NULL WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

    return user