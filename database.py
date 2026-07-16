import sqlite3
import hashlib
from datetime import datetime

DB_FILE = "akilli_butce_v2.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    # Tabloyu baştan oluşturma riskini almamak için var olanı korur
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        trial_start_date TEXT
    )
    """)
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, full_name, password, email, phone):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Tarihi gün ve saat olarak ekliyoruz
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO users (username, full_name, password, email, phone, trial_start_date) VALUES (?,?,?,?,?,?)",
                       (username, full_name, hash_password(password), email, phone, now))
        conn.commit()
        return True
    except Exception as e:
        # Eğer hata alırsan Streamlit arayüzünde hatayı göreceksin
        st.error(f"Veritabanı Hatası: {e}")
        return False
    finally:
        conn.close()

def verify_user(username, password):
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hash_password(password))).fetchone()
    conn.close()
    return user
