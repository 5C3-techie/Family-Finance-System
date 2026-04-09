import os
import sqlite3
from config import DB_FILE


def get_db_path():
    if os.path.isabs(DB_FILE):
        return DB_FILE

    project_dir = os.path.dirname(os.path.abspath(__file__))
    candidate_paths = [
        os.path.join(project_dir, DB_FILE),
        os.path.join(os.path.dirname(project_dir), DB_FILE),
    ]

    for path in candidate_paths:
        if not os.path.exists(path):
            continue

        conn = None
        try:
            conn = sqlite3.connect(path, timeout=5)
            conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone()
            return path
        except sqlite3.Error:
            continue
        finally:
            if conn is not None:
                conn.close()

    return candidate_paths[0]


def get_db_connection():
    conn = sqlite3.connect(get_db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    conn = get_db_connection()

    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            phone TEXT,
            password TEXT,
            role TEXT,
            otp TEXT,
            otp_expiry TEXT
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            uploaded_by INTEGER,
            assigned_member INTEGER,
            filename TEXT,
            filepath TEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    try:
        conn.execute('ALTER TABLE users ADD COLUMN phone TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        conn.execute('ALTER TABLE documents ADD COLUMN uploaded_by INTEGER')
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        conn.execute('ALTER TABLE documents ADD COLUMN assigned_member INTEGER')
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        conn.execute('ALTER TABLE documents ADD COLUMN description TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Preserve older records by mapping the old user_id to the new document fields.
    try:
        conn.execute('''
            UPDATE documents
            SET uploaded_by = COALESCE(uploaded_by, user_id),
                assigned_member = COALESCE(assigned_member, user_id)
        ''')
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()
