from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3

from .database import connect

_ITERATIONS = 310_000
MIN_PASSWORD_LENGTH = 8


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256": return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)).hex()
        return hmac.compare_digest(candidate, digest_hex)
    except (ValueError, TypeError): return False


def _ensure_table(connection: sqlite3.Connection) -> None:
    connection.execute("""CREATE TABLE IF NOT EXISTS dashboard_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'admin',
        created_at TEXT NOT NULL,
        last_login_at TEXT
    )""")
    connection.commit()


def user_count(database_url: str) -> int:
    connection = connect(database_url)
    try:
        _ensure_table(connection)
        return int(connection.execute("SELECT COUNT(*) FROM dashboard_users").fetchone()[0])
    finally: connection.close()


def create_admin(database_url: str, username: str, password: str) -> bool:
    username = username.strip()
    if not username or len(username) > 128 or len(password) < MIN_PASSWORD_LENGTH or len(password) > 256:
        return False
    connection = connect(database_url)
    try:
        _ensure_table(connection)
        if connection.execute("SELECT 1 FROM dashboard_users LIMIT 1").fetchone(): return False
        from datetime import datetime, timezone
        connection.execute("INSERT INTO dashboard_users (username,password_hash,role,created_at) VALUES (?,?,?,?)", (username, _hash_password(password), "admin", datetime.now(timezone.utc).isoformat()))
        connection.commit()
        return True
    except sqlite3.IntegrityError: return False
    finally: connection.close()


def authenticate(database_url: str, username: str, password: str) -> bool:
    connection = connect(database_url)
    try:
        _ensure_table(connection)
        row = connection.execute("SELECT id,password_hash FROM dashboard_users WHERE username=? COLLATE NOCASE", (username.strip(),)).fetchone()
        if row is None or not _verify_password(password, row["password_hash"]): return False
        from datetime import datetime, timezone
        connection.execute("UPDATE dashboard_users SET last_login_at=? WHERE id=?", (datetime.now(timezone.utc).isoformat(), row["id"]))
        connection.commit()
        return True
    finally: connection.close()


def has_users(database_url: str) -> bool:
    return user_count(database_url) > 0
