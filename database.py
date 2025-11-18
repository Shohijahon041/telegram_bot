import sqlite3

DB_FILE = "kino.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS kino(
        id TEXT PRIMARY KEY,
        file_id TEXT,
        name TEXT,
        date TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS channels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS config(
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        date TEXT
    )
    """)
    conn.commit()
    conn.close()

def add_channel(channel_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO channels(channel_id) VALUES(?)", (channel_id,))
    conn.commit()
    conn.close()

def list_channels():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT channel_id FROM channels")
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows

def save_kino(code, file_id, name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO kino(id, file_id, name, date) VALUES(?,?,?,datetime('now'))", (code, file_id, name))
    conn.commit()
    conn.close()

def get_kino(code):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT file_id, name FROM kino WHERE id=?", (code,))
    row = c.fetchone()
    conn.close()
    return row

def record_log(user_id, action):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO logs(user_id, action, date) VALUES(?,?,datetime('now'))", (user_id, action))
    conn.commit()
    conn.close()
