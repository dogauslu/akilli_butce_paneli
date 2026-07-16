import sqlite3
import hashlib
import os
from datetime import datetime, timedelta

DB_FILE = "akilli_butce_v2.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        trial_start_date TEXT NOT NULL,
        is_premium INTEGER DEFAULT 0,
        last_payment_date TEXT,
        status TEXT DEFAULT 'active'
    )
    """)
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, full_name, password, email, phone):
    conn = get_connection()
    cursor = conn.cursor()
    hashed = hash_password(password)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cursor.execute("""
        INSERT INTO users (username, full_name, password, email, phone, trial_start_date)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (username, full_name, hashed, email, phone, now_str))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    hashed = hash_password(password)
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed))
    user = cursor.fetchone()
    conn.close()
    return user

def check_email_exists(email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return user is not None

def update_password(email, new_password):
    conn = get_connection()
    cursor = conn.cursor()
    hashed = hash_password(new_password)
    cursor.execute("UPDATE users SET password = ? WHERE email = ?", (hashed, email))
    conn.commit()
    conn.close()
    return True

def cleanup_inactive_accounts():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, trial_start_date FROM users WHERE is_premium = 0")
    users = cursor.fetchall()
    
    now = datetime.now()
    for u in users:
        try:
            trial_start = datetime.strptime(u["trial_start_date"], "%Y-%m-%d %H:%M:%S")
            if (now - trial_start).days >= 365:
                user_id = u["id"]
                file_name = f"akilli_butce_verileri_{user_id}.csv"
                if os.path.exists(file_name):
                    os.remove(file_name)
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        except Exception:
            pass
            
    conn.commit()
    conn.close()

def check_username_exists(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return user is not None
