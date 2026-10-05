"""SQLite store for operator-desk tables (users, audit, archive index).

Never assumes the producer's ``documents`` table exists. Env is read on
each call so tests can point at a temp file after import.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import sqlite3
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("mailroom.operator.db")

ROLES = frozenset({"admin", "reviewer", "viewer"})
PIPELINE_BINS = ("inbox", "processing", "classified", "review", "failed")


def base_dir() -> Path:
    return Path(os.environ.get("MAILROOM_BASE_DIR", "data")).expanduser()


def db_path() -> Path:
    explicit = os.environ.get("MAILROOM_OPERATOR_DB", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    url = os.environ.get("DATABASE_URL", "").strip()
    if url.startswith("sqlite:///"):
        return Path(url[len("sqlite:///") :]).expanduser()
    if url.startswith("sqlite://"):
        return Path(url[len("sqlite://") :]).expanduser()
    return base_dir() / "operator.db"


def archive_dir() -> Path:
    return base_dir() / "archive"


def pipeline_dir() -> Path:
    return base_dir() / "pipeline"


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str) -> str:
    try:
        import bcrypt

        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")
    except ImportError:
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("ascii"), 200_000
        ).hex()
        return f"pbkdf2${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    if not stored:
        return False
    if stored.startswith("$2"):
        try:
            import bcrypt
        except ImportError:
            return False
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored.encode("ascii"))
        except ValueError:
            return False
    if stored.startswith("pbkdf2$"):
        parts = stored.split("$", 2)
        if len(parts) != 3:
            return False
        _, salt, digest = parts
        check = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("ascii"), 200_000
        ).hex()
        return hmac.compare_digest(check, digest)
    return False


def ensure_bins() -> None:
    root = pipeline_dir()
    for name in PIPELINE_BINS:
        (root / name).mkdir(parents=True, exist_ok=True)
    archive_dir().mkdir(parents=True, exist_ok=True)


def migrate() -> Path:
    """Create operator tables and seed the default admin when the store is empty."""
    path = db_path()
    conn = connect()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS ui_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT CHECK(role IN ('admin', 'reviewer', 'viewer')) DEFAULT 'viewer',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS ui_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES ui_users(id),
                action TEXT NOT NULL,
                target_doc_id TEXT,
                target_matter_id TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS archive_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT UNIQUE NOT NULL,
                matter_id TEXT NOT NULL,
                doc_type TEXT NOT NULL,
                archive_path TEXT NOT NULL,
                file_size_bytes INTEGER,
                checksum_sha256 TEXT,
                archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_archive_matter ON archive_index(matter_id);
            CREATE INDEX IF NOT EXISTS idx_ui_audit_user ON ui_audit(user_id);
            CREATE INDEX IF NOT EXISTS idx_ui_audit_doc ON ui_audit(target_doc_id);
            """
        )
        existing = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='documents'"
        ).fetchone()
        if existing:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_status ON documents(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_matter ON documents(matter_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_type ON documents(doc_type)")
        if conn.execute("SELECT COUNT(*) FROM ui_users").fetchone()[0] == 0:
            username = os.environ.get("MAILROOM_OPERATOR_ADMIN_USER", "admin").strip() or "admin"
            password = os.environ.get("MAILROOM_OPERATOR_ADMIN_PASSWORD", "changeme")
            conn.execute(
                "INSERT INTO ui_users (username, password_hash, role) VALUES (?, ?, 'admin')",
                (username, hash_password(password)),
            )
            log.info("seeded operator admin user %s", username)
        conn.commit()
    finally:
        conn.close()
    return path


def write_audit(
    *,
    action: str,
    user_id: Optional[int] = None,
    target_doc_id: Optional[str] = None,
    target_matter_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO ui_audit (user_id, action, target_doc_id, target_matter_id, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                action,
                target_doc_id,
                target_matter_id,
                json.dumps(metadata) if metadata is not None else None,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def lookup_user(username: str) -> Optional[sqlite3.Row]:
    conn = connect()
    try:
        return conn.execute(
            "SELECT id, username, password_hash, role FROM ui_users WHERE username = ?",
            (username,),
        ).fetchone()
    finally:
        conn.close()


def upsert_archive_entry(
    *,
    doc_id: str,
    matter_id: str,
    doc_type: str,
    archive_path: str,
    file_size_bytes: Optional[int] = None,
    checksum_sha256: Optional[str] = None,
) -> None:
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO archive_index
                (doc_id, matter_id, doc_type, archive_path, file_size_bytes, checksum_sha256)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(doc_id) DO UPDATE SET
                matter_id = excluded.matter_id,
                doc_type = excluded.doc_type,
                archive_path = excluded.archive_path,
                file_size_bytes = excluded.file_size_bytes,
                checksum_sha256 = excluded.checksum_sha256,
                archived_at = CURRENT_TIMESTAMP
            """,
            (doc_id, matter_id, doc_type, archive_path, file_size_bytes, checksum_sha256),
        )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ensure_bins()
    path = migrate()
    print(f"Migrations applied to {path}")
