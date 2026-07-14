# database.py
import sqlite3
import hashlib
from datetime import datetime, timedelta

DB_FILE = "akilli_butce.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Kullanıcılar Tablosu (Üyelik ve Ödeme Kontrol Alanları Dahil)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOUTINCREMENT,
        username TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        trial_start_date TEXT NOT NULL,
        is_premium INTEGER DEFAULT 0,
        last_payment_date TEXT,
        status TEXT DEFAULT 'active' -- active, warning, suspended
    )
    """)
    
    # Kişiye Özel Bütçe Verileri Tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS budget_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        category TEXT NOT NULL,
        amount REAL NOT NULL,
        description TEXT,
        type TEXT NOT NULL, -- 'Gelir' veya 'Gider'
        FOREIGN KEY (user_id) REFERENCES users(id)
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
