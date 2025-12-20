import sqlite3

DB_NAME = "users.db"
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
cursor = conn.cursor()

# User jadvali
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    phone TEXT,
    ref_by INTEGER,
    score INTEGER DEFAULT 0,
    joined INTEGER DEFAULT 0
)
"""
)
conn.commit()


# User bor-yo'qligini tekshirish
def user_exists(user_id):
    cursor.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None


# Ball olish
def get_score(user_id):
    cursor.execute("SELECT score FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    return res[0] if res else 0


# Ball qo'shish
def add_score(user_id):
    cursor.execute("UPDATE users SET score = score + 1 WHERE user_id=?", (user_id,))
    conn.commit()


# Yangi user qo'shish
def add_user(user_id, phone=None, ref_by=None):
    cursor.execute(
        """
        INSERT OR IGNORE INTO users (user_id, phone, ref_by)
        VALUES (?, ?, ?)
    """,
        (user_id, phone, ref_by),
    )
    conn.commit()


# User balli berilganini belgilash
def mark_joined(user_id):
    cursor.execute("UPDATE users SET joined=1 WHERE user_id=?", (user_id,))
    conn.commit()


# User allaqachon ball olganmi?
def has_joined(user_id):
    cursor.execute("SELECT joined FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row and row[0] == 1
