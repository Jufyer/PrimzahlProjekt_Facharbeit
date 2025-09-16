import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE = 'users.db'

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS progress (
                user_id INTEGER,
                total_primes_found INTEGER DEFAULT 0,
                total_batches_completed INTEGER DEFAULT 0,
                total_numbers_processed INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(progress)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'total_numbers_processed' not in columns:
            conn.execute('ALTER TABLE progress ADD COLUMN total_numbers_processed INTEGER DEFAULT 0')

def create_user(username, password):
    password_hash = generate_password_hash(password)
    with sqlite3.connect(DATABASE) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, password_hash))
            user_id = cursor.lastrowid
            cursor.execute('INSERT INTO progress (user_id) VALUES (?)', (user_id,))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def verify_user(username, password):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, password_hash FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        if user and check_password_hash(user[1], password):
            return user[0]
        return None

def get_user_progress(user_id):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT total_primes_found, total_numbers_processed FROM progress WHERE user_id = ?', (user_id,))
        return cursor.fetchone()

def update_user_progress(user_id, primes_found, numbers_processed):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('''
            UPDATE progress 
            SET total_primes_found = total_primes_found + ?,
                total_numbers_processed = total_numbers_processed + ?
            WHERE user_id = ?
        ''', (primes_found, numbers_processed, user_id))
        conn.commit()

def get_leaderboard():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT users.username, 
                   progress.total_numbers_processed,
                   progress.total_primes_found
            FROM progress
            JOIN users ON progress.user_id = users.id
            ORDER BY total_numbers_processed DESC
            LIMIT 10
        ''')
        return cursor.fetchall()

init_db()