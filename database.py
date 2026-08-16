import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE = "chat_memory.db"


def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            memory TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


def create_user(username, password):
    conn = get_connection()

    try:
        hashed_password = generate_password_hash(password)

        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hashed_password)
        )

        conn.commit()
        return True

    except sqlite3.IntegrityError:
        return False

    finally:
        conn.close()


def authenticate_user(username, password):
    conn = get_connection()

    user = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    conn.close()

    if user and check_password_hash(user["password"], password):
        return user

    return None


def save_message(user_id, role, content):
    conn = get_connection()

    conn.execute(
        """
        INSERT INTO messages (user_id, role, content)
        VALUES (?, ?, ?)
        """,
        (user_id, role, content)
    )

    conn.commit()
    conn.close()


def get_messages(user_id, limit=30):
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT role, content, created_at
        FROM messages
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (user_id, limit)
    ).fetchall()

    conn.close()

    return list(reversed(rows))


def clear_messages(user_id):
    conn = get_connection()

    conn.execute(
        "DELETE FROM messages WHERE user_id = ?",
        (user_id,)
    )

    conn.commit()
    conn.close()


def save_memory(user_id, memory):
    conn = get_connection()

    conn.execute(
        """
        INSERT INTO memories (user_id, memory)
        VALUES (?, ?)
        """,
        (user_id, memory)
    )

    conn.commit()
    conn.close()


def get_memories(user_id):
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT id, memory, created_at
        FROM memories
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 20
        """,
        (user_id,)
    ).fetchall()

    conn.close()

    return rows


def clear_memories(user_id):
    conn = get_connection()

    conn.execute(
        "DELETE FROM memories WHERE user_id = ?",
        (user_id,)
    )

    conn.commit()
    conn.close()


def save_document(user_id, filename, content):
    conn = get_connection()

    conn.execute(
        """
        INSERT INTO documents (user_id, filename, content)
        VALUES (?, ?, ?)
        """,
        (user_id, filename, content)
    )

    conn.commit()
    conn.close()


def get_latest_document(user_id):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT filename, content
        FROM documents
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    ).fetchone()

    conn.close()

    return row


def clear_documents(user_id):
    conn = get_connection()

    conn.execute(
        "DELETE FROM documents WHERE user_id = ?",
        (user_id,)
    )

    conn.commit()
    conn.close()