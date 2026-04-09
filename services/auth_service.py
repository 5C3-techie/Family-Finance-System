import bcrypt
import sqlite3
from datetime import datetime
from database import get_db_connection
from services.otp_service import generate_otp
from utils.email_utils import send_otp_email


def get_registration_role(conn):
    admin = conn.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()
    return 'member' if admin else 'admin'


def get_all_users():
    conn = get_db_connection()
    users = conn.execute(
        "SELECT id, name, email, phone, role FROM users ORDER BY role DESC, name ASC"
    ).fetchall()
    conn.close()
    return users


def update_user_role(user_id, new_role):
    if new_role not in {'admin', 'member'}:
        return False, 'Invalid role selected.'

    conn = get_db_connection()
    user = conn.execute(
        "SELECT id, role, name FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    if not user:
        conn.close()
        return False, 'User not found.'

    if user['role'] == new_role:
        conn.close()
        return False, f"{user['name']} is already a {new_role}."

    if user['role'] == 'admin' and new_role == 'member':
        admin_count = conn.execute(
            "SELECT COUNT(*) FROM users WHERE role='admin'"
        ).fetchone()[0]
        if admin_count <= 1:
            conn.close()
            return False, 'You cannot remove admin access from the last admin.'

    conn.execute("UPDATE users SET role=? WHERE id=?", (new_role, user_id))
    conn.commit()
    conn.close()
    return True, f"{user['name']} is now a {new_role}."


def register_user(name, email, phone, password):
    conn = get_db_connection()

    existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if existing:
        conn.close()
        return False, None

    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode(), salt).decode()
    role = get_registration_role(conn)

    try:
        conn.execute(
            "INSERT INTO users (name,email,phone,password,role) VALUES (?,?,?,?,?)",
            (name, email, phone, hashed_password, role)
        )
        conn.commit()
        return True, role
    except sqlite3.IntegrityError:
        return False, None
    finally:
        conn.close()


def issue_login_otp(user):
    otp, expiry = generate_otp()

    conn = get_db_connection()
    conn.execute(
        "UPDATE users SET otp=?, otp_expiry=? WHERE id=?",
        (otp, expiry, user['id'])
    )
    conn.commit()
    conn.close()

    if not send_otp_email(user['email'], otp):
        return False

    return True


def login_user(email, password):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()

    if user and bcrypt.checkpw(password.encode(), user['password'].encode()):
        if not issue_login_otp(user):
            return None

        return user

    return None


def resend_user_otp(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()

    if not user:
        return False

    return issue_login_otp(user)

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
