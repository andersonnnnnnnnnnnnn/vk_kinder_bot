import sqlite3

def create_database():
    conn = sqlite3.connect('vk_bot.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS shown_users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER UNIQUE
                     )''')
    conn.commit()
    conn.close()

def add_shown_user(user_id):
    conn = sqlite3.connect('vk_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO shown_users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def was_user_shown(user_id):
    conn = sqlite3.connect('vk_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM shown_users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None