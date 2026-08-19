"""
utils/db.py
Database abstraction for session persistence.
Supports: SQLite (local), PostgreSQL (Streamlit Cloud).
Auto-detects environment and uses appropriate backend.
"""
import os, json
from abc import ABC, abstractmethod
import streamlit as st

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_POSTGRESQL = DATABASE_URL.startswith("postgresql")


class SessionDB(ABC):
    """Abstract session database."""

    @abstractmethod
    def init(self) -> None:
        """Initialize database schema."""
        pass

    @abstractmethod
    def save(self, project_name: str, field_name: str, session_data: dict) -> bool:
        """Save or overwrite session. Returns True on success."""
        pass

    @abstractmethod
    def load(self, project_name: str, field_name: str) -> dict:
        """Load session. Returns {} if not found."""
        pass

    @abstractmethod
    def list_all(self) -> list:
        """List all sessions, newest first."""
        pass

    @abstractmethod
    def delete(self, project_name: str, field_name: str) -> bool:
        """Delete session. Returns True on success."""
        pass

    def save_version(self, project_name: str, field_name: str, revision: int, session_data: dict) -> bool:
        """Persist an immutable study snapshot when supported by the backend."""
        return False

    def list_versions(self, project_name: str, field_name: str) -> list:
        """Return immutable study revisions, newest first."""
        return []


class SQLiteDB(SessionDB):
    """Local SQLite database for development."""

    def __init__(self):
        self.db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "sessions.db"
        )
        self.init()

    def init(self):
        """Create sessions table if it doesn't exist."""
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    phase TEXT,
                    session_json TEXT NOT NULL,
                    completion_pct INTEGER DEFAULT 0,
                    auto_saved BOOLEAN DEFAULT 0,
                    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(project_name, field_name)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS study_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    session_json TEXT NOT NULL,
                    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(project_name, field_name, revision)
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            st.warning(f"SQLite init: {e}")

    def save(self, project_name: str, field_name: str, session_data: dict) -> bool:
        """Save session (overwrite if exists)."""
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_path)
            session_json = json.dumps(session_data["session"], ensure_ascii=False)
            meta = session_data["meta"]
            conn.execute("""
                INSERT INTO sessions (project_name, field_name, phase, session_json, completion_pct, auto_saved, saved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_name, field_name) DO UPDATE SET
                    phase = excluded.phase,
                    session_json = excluded.session_json,
                    completion_pct = excluded.completion_pct,
                    auto_saved = excluded.auto_saved,
                    saved_at = excluded.saved_at
            """, (project_name, field_name, meta.get("project_phase",""), session_json,
                  meta.get("completion",0), int(meta.get("auto_saved",False)), meta.get("saved_at","")))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            st.warning(f"SQLite save: {e}")
            return False

    def save_version(self, project_name: str, field_name: str, revision: int, session_data: dict) -> bool:
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "INSERT OR IGNORE INTO study_versions (project_name, field_name, revision, session_json, saved_at) VALUES (?, ?, ?, ?, ?)",
                (project_name, field_name, revision, json.dumps(session_data["session"], ensure_ascii=False), session_data["meta"].get("saved_at", "")),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            st.warning(f"SQLite version save: {e}")
            return False

    def list_versions(self, project_name: str, field_name: str) -> list:
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute(
                "SELECT revision, saved_at FROM study_versions WHERE project_name = ? AND field_name = ? ORDER BY revision DESC",
                (project_name, field_name),
            ).fetchall()
            conn.close()
            return [{"revision": row[0], "saved_at": row[1]} for row in rows]
        except Exception as e:
            st.warning(f"SQLite version list: {e}")
            return []

    def load(self, project_name: str, field_name: str) -> dict:
        """Load session by project/field name."""
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(
                "SELECT session_json, phase, saved_at, auto_saved FROM sessions WHERE project_name = ? AND field_name = ?",
                (project_name, field_name)
            )
            row = cursor.fetchone()
            conn.close()
            if not row:
                return {}
            session_json, phase, saved_at, auto_saved = row
            return {
                "session": json.loads(session_json),
                "meta": {"project_name": project_name, "field_name": field_name,
                         "project_phase": phase or "",
                         "saved_at": saved_at, "auto_saved": bool(auto_saved)}
            }
        except Exception as e:
            st.warning(f"SQLite load: {e}")
            return {}

    def list_all(self) -> list:
        """List all sessions, newest first."""
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("""
                SELECT project_name, field_name, phase, completion_pct, auto_saved, saved_at
                FROM sessions ORDER BY saved_at DESC
            """)
            rows = cursor.fetchall()
            conn.close()
            return [{
                "project_name": r[0], "field_name": r[1], "phase": r[2] or "—",
                "completion": r[3], "auto_saved": bool(r[4]), "saved_at": r[5],
            } for r in rows]
        except Exception as e:
            st.warning(f"SQLite list: {e}")
            return []

    def delete(self, project_name: str, field_name: str) -> bool:
        """Delete session by project/field name."""
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "DELETE FROM sessions WHERE project_name = ? AND field_name = ?",
                (project_name, field_name)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            st.warning(f"SQLite delete: {e}")
            return False


class PostgresDB(SessionDB):
    """PostgreSQL database for Streamlit Cloud and production."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.init()

    def init(self):
        """Create sessions table if it doesn't exist."""
        try:
            import psycopg2
            conn = psycopg2.connect(self.db_url)
            conn.autocommit = True
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id SERIAL PRIMARY KEY,
                    project_name VARCHAR(255) NOT NULL,
                    field_name VARCHAR(255) NOT NULL,
                    phase VARCHAR(50),
                    session_json TEXT NOT NULL,
                    completion_pct INTEGER DEFAULT 0,
                    auto_saved BOOLEAN DEFAULT FALSE,
                    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(project_name, field_name)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS study_versions (
                    id SERIAL PRIMARY KEY,
                    project_name VARCHAR(255) NOT NULL,
                    field_name VARCHAR(255) NOT NULL,
                    revision INTEGER NOT NULL,
                    session_json TEXT NOT NULL,
                    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(project_name, field_name, revision)
                )
            """)
            cursor.close()
            conn.close()
        except Exception as e:
            st.warning(f"PostgreSQL init: {e}")

    def save(self, project_name: str, field_name: str, session_data: dict) -> bool:
        """Save session (overwrite if exists)."""
        try:
            import psycopg2
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            session_json = json.dumps(session_data["session"], ensure_ascii=False)
            meta = session_data["meta"]
            cursor.execute("""
                INSERT INTO sessions (project_name, field_name, phase, session_json, completion_pct, auto_saved, saved_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(project_name, field_name) DO UPDATE SET
                    phase = EXCLUDED.phase, session_json = EXCLUDED.session_json,
                    completion_pct = EXCLUDED.completion_pct, auto_saved = EXCLUDED.auto_saved,
                    saved_at = EXCLUDED.saved_at
            """, (project_name, field_name, meta.get("project_phase",""), session_json,
                  meta.get("completion",0), meta.get("auto_saved",False), meta.get("saved_at","")))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            st.warning(f"PostgreSQL save: {e}")
            return False

    def save_version(self, project_name: str, field_name: str, revision: int, session_data: dict) -> bool:
        try:
            import psycopg2
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO study_versions (project_name, field_name, revision, session_json, saved_at) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (project_name, field_name, revision, json.dumps(session_data["session"], ensure_ascii=False), session_data["meta"].get("saved_at", "")),
            )
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            st.warning(f"PostgreSQL version save: {e}")
            return False

    def list_versions(self, project_name: str, field_name: str) -> list:
        try:
            import psycopg2
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT revision, saved_at FROM study_versions WHERE project_name = %s AND field_name = %s ORDER BY revision DESC",
                (project_name, field_name),
            )
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return [{"revision": row[0], "saved_at": row[1].isoformat() if hasattr(row[1], "isoformat") else str(row[1])} for row in rows]
        except Exception as e:
            st.warning(f"PostgreSQL version list: {e}")
            return []

    def load(self, project_name: str, field_name: str) -> dict:
        """Load session by project/field name."""
        try:
            import psycopg2
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT session_json, phase, saved_at, auto_saved FROM sessions WHERE project_name = %s AND field_name = %s",
                (project_name, field_name)
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if not row:
                return {}
            session_json, phase, saved_at, auto_saved = row
            return {
                "session": json.loads(session_json),
                "meta": {"project_name": project_name, "field_name": field_name,
                         "project_phase": phase or "",
                         "saved_at": saved_at.isoformat() if hasattr(saved_at, 'isoformat') else str(saved_at),
                         "auto_saved": bool(auto_saved)}
            }
        except Exception as e:
            st.warning(f"PostgreSQL load: {e}")
            return {}

    def list_all(self) -> list:
        """List all sessions, newest first."""
        try:
            import psycopg2
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT project_name, field_name, phase, completion_pct, auto_saved, saved_at
                FROM sessions ORDER BY saved_at DESC
            """)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return [{
                "project_name": r[0], "field_name": r[1], "phase": r[2] or "—",
                "completion": r[3], "auto_saved": bool(r[4]),
                "saved_at": r[5].isoformat() if hasattr(r[5], 'isoformat') else str(r[5]),
            } for r in rows]
        except Exception as e:
            st.warning(f"PostgreSQL list: {e}")
            return []

    def delete(self, project_name: str, field_name: str) -> bool:
        """Delete session by project/field name."""
        try:
            import psycopg2
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM sessions WHERE project_name = %s AND field_name = %s",
                (project_name, field_name)
            )
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            st.warning(f"PostgreSQL delete: {e}")
            return False


@st.cache_resource
def get_db() -> SessionDB:
    """Get the appropriate database instance (SQLite or PostgreSQL)."""
    if USE_POSTGRESQL:
        return PostgresDB(DATABASE_URL)
    else:
        return SQLiteDB()
