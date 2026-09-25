"""
utils/db.py
Database abstraction for session persistence.
Supports SQLite (local) and PostgreSQL (Streamlit Cloud).
"""

from __future__ import annotations

import json
import os
import sqlite3
from abc import ABC, abstractmethod
from typing import Any

import streamlit as st


DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_POSTGRESQL = DATABASE_URL.startswith("postgresql")
SQLITE_TIMEOUT_SECONDS = 30


def _sqlite_connect(path: str) -> sqlite3.Connection:
    """Open a SQLite connection with a bounded lock wait."""
    conn = sqlite3.connect(path, timeout=SQLITE_TIMEOUT_SECONDS)
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _session_revision(payload: dict[str, Any]) -> int:
    try:
        return int(payload.get("study_revision", 0) or 0)
    except (TypeError, ValueError):
        return 0


class SessionDB(ABC):
    """Abstract session database."""

    @abstractmethod
    def init(self) -> None:
        pass

    @abstractmethod
    def save(self, project_name: str, field_name: str, session_data: dict) -> bool:
        pass

    @abstractmethod
    def load(self, project_name: str, field_name: str) -> dict:
        pass

    @abstractmethod
    def list_all(self) -> list:
        pass

    @abstractmethod
    def delete(self, project_name: str, field_name: str) -> bool:
        pass

    def save_version(
        self,
        project_name: str,
        field_name: str,
        revision: int,
        session_data: dict,
    ) -> bool:
        return False

    def list_versions(self, project_name: str, field_name: str) -> list:
        return []

    def load_version(
        self,
        project_name: str,
        field_name: str,
        revision: int,
    ) -> dict:
        return {}

    def list_all_records(self) -> list:
        return []

    def save_bundle(
        self,
        project_name: str,
        field_name: str,
        revision: int,
        session_data: dict,
        expected_previous_revision: int | None = None,
    ) -> bool:
        """Persist current state + immutable revision atomically.

        expected_previous_revision prevents a stale editor from silently
        overwriting a newer saved study.
        """
        return self.save(project_name, field_name, session_data) and self.save_version(
            project_name,
            field_name,
            revision,
            session_data,
        )


class SQLiteDB(SessionDB):
    """Local SQLite database for development and single-node deployment."""

    def __init__(self):
        self.db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "sessions.db",
        )
        self.init()

    def init(self):
        try:
            conn = _sqlite_connect(self.db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    phase TEXT,
                    session_json TEXT NOT NULL,
                    completion_pct INTEGER DEFAULT 0,
                    auto_saved BOOLEAN DEFAULT 0,
                    study_id TEXT,
                    study_owner TEXT,
                    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(project_name, field_name)
                )
                """
            )
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(sessions)")
            }
            if "study_id" not in columns:
                conn.execute("ALTER TABLE sessions ADD COLUMN study_id TEXT")
            if "study_owner" not in columns:
                conn.execute("ALTER TABLE sessions ADD COLUMN study_owner TEXT")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS study_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    session_json TEXT NOT NULL,
                    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(project_name, field_name, revision)
                )
                """
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            st.warning(f"SQLite init: {exc}")

    def save(self, project_name: str, field_name: str, session_data: dict) -> bool:
        try:
            conn = _sqlite_connect(self.db_path)
            meta = session_data["meta"]
            session_json = json.dumps(session_data["session"], ensure_ascii=False)
            conn.execute(
                """
                INSERT INTO sessions (
                    project_name, field_name, phase, session_json,
                    completion_pct, auto_saved, study_id, study_owner, saved_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_name, field_name) DO UPDATE SET
                    phase=excluded.phase,
                    session_json=excluded.session_json,
                    completion_pct=excluded.completion_pct,
                    auto_saved=excluded.auto_saved,
                    study_id=excluded.study_id,
                    study_owner=excluded.study_owner,
                    saved_at=excluded.saved_at
                """,
                (
                    project_name,
                    field_name,
                    meta.get("project_phase", ""),
                    session_json,
                    meta.get("completion", 0),
                    int(meta.get("auto_saved", False)),
                    meta.get("study_id", ""),
                    meta.get("study_owner", ""),
                    meta.get("saved_at", ""),
                ),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as exc:
            st.warning(f"SQLite save: {exc}")
            return False

    def save_bundle(
        self,
        project_name: str,
        field_name: str,
        revision: int,
        session_data: dict,
        expected_previous_revision: int | None = None,
    ) -> bool:
        conn = _sqlite_connect(self.db_path)
        try:
            meta = session_data["meta"]
            payload = session_data["session"]
            session_json = json.dumps(payload, ensure_ascii=False)

            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT session_json FROM sessions WHERE project_name = ? AND field_name = ?",
                (project_name, field_name),
            ).fetchone()

            if expected_previous_revision is not None:
                current_revision = None
                if existing:
                    current_revision = _session_revision(
                        json.loads(existing[0] or "{}")
                    )
                expected = int(expected_previous_revision)
                if (existing is None and expected != 0) or (
                    existing is not None and current_revision != expected
                ):
                    conn.rollback()
                    st.warning(
                        "Save conflict detected: this study changed after it was loaded. "
                        "Reload the latest study before saving again."
                    )
                    return False

            conn.execute(
                """
                INSERT INTO sessions (
                    project_name, field_name, phase, session_json,
                    completion_pct, auto_saved, study_id, study_owner, saved_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_name, field_name) DO UPDATE SET
                    phase=excluded.phase,
                    session_json=excluded.session_json,
                    completion_pct=excluded.completion_pct,
                    auto_saved=excluded.auto_saved,
                    study_id=excluded.study_id,
                    study_owner=excluded.study_owner,
                    saved_at=excluded.saved_at
                """,
                (
                    project_name,
                    field_name,
                    meta.get("project_phase", ""),
                    session_json,
                    meta.get("completion", 0),
                    int(meta.get("auto_saved", False)),
                    meta.get("study_id", ""),
                    meta.get("study_owner", ""),
                    meta.get("saved_at", ""),
                ),
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO study_versions
                    (project_name, field_name, revision, session_json, saved_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    project_name,
                    field_name,
                    revision,
                    session_json,
                    meta.get("saved_at", ""),
                ),
            )
            conn.commit()
            return True
        except Exception as exc:
            try:
                conn.rollback()
            except Exception:
                pass
            st.warning(f"SQLite bundle save: {exc}")
            return False
        finally:
            conn.close()

    def save_version(
        self,
        project_name: str,
        field_name: str,
        revision: int,
        session_data: dict,
    ) -> bool:
        try:
            conn = _sqlite_connect(self.db_path)
            conn.execute(
                """
                INSERT OR IGNORE INTO study_versions
                    (project_name, field_name, revision, session_json, saved_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    project_name,
                    field_name,
                    revision,
                    json.dumps(session_data["session"], ensure_ascii=False),
                    session_data["meta"].get("saved_at", ""),
                ),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as exc:
            st.warning(f"SQLite version save: {exc}")
            return False

    def list_versions(self, project_name: str, field_name: str) -> list:
        try:
            conn = _sqlite_connect(self.db_path)
            rows = conn.execute(
                """
                SELECT revision, saved_at
                FROM study_versions
                WHERE project_name = ? AND field_name = ?
                ORDER BY revision DESC
                """,
                (project_name, field_name),
            ).fetchall()
            conn.close()
            return [{"revision": row[0], "saved_at": row[1]} for row in rows]
        except Exception as exc:
            st.warning(f"SQLite version list: {exc}")
            return []

    def load_version(
        self,
        project_name: str,
        field_name: str,
        revision: int,
    ) -> dict:
        try:
            conn = _sqlite_connect(self.db_path)
            row = conn.execute(
                """
                SELECT session_json, saved_at
                FROM study_versions
                WHERE project_name = ? AND field_name = ? AND revision = ?
                """,
                (project_name, field_name, revision),
            ).fetchone()
            conn.close()
            if not row:
                return {}
            return {
                "session": json.loads(row[0] or "{}"),
                "meta": {
                    "project_name": project_name,
                    "field_name": field_name,
                    "saved_at": row[1],
                    "study_revision": revision,
                },
            }
        except Exception as exc:
            st.warning(f"SQLite version load: {exc}")
            return {}

    def list_all_records(self) -> list:
        try:
            conn = _sqlite_connect(self.db_path)
            rows = conn.execute(
                """
                SELECT project_name, field_name, phase, session_json,
                       completion_pct, auto_saved, saved_at
                FROM sessions
                ORDER BY saved_at DESC
                """
            ).fetchall()
            conn.close()
            return [
                {
                    "session": json.loads(row[3] or "{}"),
                    "meta": {
                        "project_name": row[0],
                        "field_name": row[1],
                        "project_phase": row[2] or "",
                        "completion": row[4],
                        "auto_saved": bool(row[5]),
                        "saved_at": row[6],
                    },
                }
                for row in rows
            ]
        except Exception as exc:
            st.warning(f"SQLite record list: {exc}")
            return []

    def load(self, project_name: str, field_name: str) -> dict:
        try:
            conn = _sqlite_connect(self.db_path)
            row = conn.execute(
                """
                SELECT session_json, phase, saved_at, auto_saved,
                       study_id, study_owner
                FROM sessions
                WHERE project_name = ? AND field_name = ?
                """,
                (project_name, field_name),
            ).fetchone()
            conn.close()
            if not row:
                return {}
            session_json, phase, saved_at, auto_saved, study_id, study_owner = row
            return {
                "session": json.loads(session_json),
                "meta": {
                    "project_name": project_name,
                    "field_name": field_name,
                    "project_phase": phase or "",
                    "study_id": study_id or "",
                    "study_owner": study_owner or "",
                    "saved_at": saved_at,
                    "auto_saved": bool(auto_saved),
                },
            }
        except Exception as exc:
            st.warning(f"SQLite load: {exc}")
            return {}

    def list_all(self) -> list:
        try:
            conn = _sqlite_connect(self.db_path)
            rows = conn.execute(
                """
                SELECT project_name, field_name, phase, completion_pct,
                       auto_saved, saved_at, session_json
                FROM sessions
                ORDER BY saved_at DESC
                """
            ).fetchall()
            conn.close()

            summaries = []
            for row in rows:
                payload = json.loads(row[6] or "{}")
                changes = payload.get("study_change_log", []) or [{}]
                latest = changes[-1]
                summaries.append(
                    {
                        "project_name": row[0],
                        "field_name": row[1],
                        "phase": row[2] or "—",
                        "completion": row[3],
                        "auto_saved": bool(row[4]),
                        "saved_at": row[5],
                        "study_lifecycle": payload.get("study_lifecycle", "Draft"),
                        "study_revision": payload.get("study_revision", 0),
                        "last_edited_by": latest.get("actor", "local-user"),
                        "last_edited_at": latest.get("saved_at", row[5]),
                    }
                )
            return summaries
        except Exception as exc:
            st.warning(f"SQLite list: {exc}")
            return []

    def delete(self, project_name: str, field_name: str) -> bool:
        try:
            conn = _sqlite_connect(self.db_path)
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "DELETE FROM sessions WHERE project_name = ? AND field_name = ?",
                (project_name, field_name),
            )
            conn.execute(
                "DELETE FROM study_versions WHERE project_name = ? AND field_name = ?",
                (project_name, field_name),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as exc:
            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass
            st.warning(f"SQLite delete: {exc}")
            return False


class PostgresDB(SessionDB):
    """PostgreSQL database for Streamlit Cloud and production."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.init()

    def init(self):
        try:
            import psycopg2
            conn = psycopg2.connect(self.db_url)
            conn.autocommit = True
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id SERIAL PRIMARY KEY,
                    project_name VARCHAR(255) NOT NULL,
                    field_name VARCHAR(255) NOT NULL,
                    phase VARCHAR(50),
                    session_json TEXT NOT NULL,
                    completion_pct INTEGER DEFAULT 0,
                    auto_saved BOOLEAN DEFAULT FALSE,
                    study_id VARCHAR(36),
                    study_owner VARCHAR(255),
                    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(project_name, field_name)
                )
                """
            )
            cursor.execute(
                "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS study_id VARCHAR(36)"
            )
            cursor.execute(
                "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS study_owner VARCHAR(255)"
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS study_versions (
                    id SERIAL PRIMARY KEY,
                    project_name VARCHAR(255) NOT NULL,
                    field_name VARCHAR(255) NOT NULL,
                    revision INTEGER NOT NULL,
                    session_json TEXT NOT NULL,
                    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(project_name, field_name, revision)
                )
                """
            )
            cursor.close()
            conn.close()
        except Exception as exc:
            st.warning(f"PostgreSQL init: {exc}")

    def save(self, project_name: str, field_name: str, session_data: dict) -> bool:
        try:
            import psycopg2
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            meta = session_data["meta"]
            cursor.execute(
                """
                INSERT INTO sessions (
                    project_name, field_name, phase, session_json,
                    completion_pct, auto_saved, study_id, study_owner, saved_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(project_name, field_name) DO UPDATE SET
                    phase=EXCLUDED.phase,
                    session_json=EXCLUDED.session_json,
                    completion_pct=EXCLUDED.completion_pct,
                    auto_saved=EXCLUDED.auto_saved,
                    study_id=EXCLUDED.study_id,
                    study_owner=EXCLUDED.study_owner,
                    saved_at=EXCLUDED.saved_at
                """,
                (
                    project_name,
                    field_name,
                    meta.get("project_phase", ""),
                    json.dumps(session_data["session"], ensure_ascii=False),
                    meta.get("completion", 0),
                    meta.get("auto_saved", False),
                    meta.get("study_id", ""),
                    meta.get("study_owner", ""),
                    meta.get("saved_at", ""),
                ),
            )
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as exc:
            st.warning(f"PostgreSQL save: {exc}")
            return False

    def save_bundle(
        self,
        project_name: str,
        field_name: str,
        revision: int,
        session_data: dict,
        expected_previous_revision: int | None = None,
    ) -> bool:
        try:
            import psycopg2
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            meta = session_data["meta"]
            payload = session_data["session"]
            session_json = json.dumps(payload, ensure_ascii=False)

            cursor.execute("BEGIN")
            cursor.execute(
                """
                SELECT session_json
                FROM sessions
                WHERE project_name = %s AND field_name = %s
                FOR UPDATE
                """,
                (project_name, field_name),
            )
            existing = cursor.fetchone()

            if expected_previous_revision is not None:
                current_revision = None
                if existing:
                    current_revision = _session_revision(
                        json.loads(existing[0] or "{}")
                    )
                expected = int(expected_previous_revision)
                if (existing is None and expected != 0) or (
                    existing is not None and current_revision != expected
                ):
                    conn.rollback()
                    st.warning(
                        "Save conflict detected: this study changed after it was loaded. "
                        "Reload the latest study before saving again."
                    )
                    cursor.close()
                    conn.close()
                    return False

            cursor.execute(
                """
                INSERT INTO sessions (
                    project_name, field_name, phase, session_json,
                    completion_pct, auto_saved, study_id, study_owner, saved_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(project_name, field_name) DO UPDATE SET
                    phase=EXCLUDED.phase,
                    session_json=EXCLUDED.session_json,
                    completion_pct=EXCLUDED.completion_pct,
                    auto_saved=EXCLUDED.auto_saved,
                    study_id=EXCLUDED.study_id,
                    study_owner=EXCLUDED.study_owner,
                    saved_at=EXCLUDED.saved_at
                """,
                (
                    project_name,
                    field_name,
                    meta.get("project_phase", ""),
                    session_json,
                    meta.get("completion", 0),
                    meta.get("auto_saved", False),
                    meta.get("study_id", ""),
                    meta.get("study_owner", ""),
                    meta.get("saved_at", ""),
                ),
            )
            cursor.execute(
                """
                INSERT INTO study_versions (
                    project_name, field_name, revision, session_json, saved_at
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (
                    project_name,
                    field_name,
                    revision,
                    session_json,
                    meta.get("saved_at", ""),
                ),
            )
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as exc:
            try:
                conn.rollback()
                cursor.close()
                conn.close()
            except Exception:
                pass
            st.warning(f"PostgreSQL bundle save: {exc}")
            return False

    def save_version(
        self,
        project_name: str,
        field_name: str,
        revision: int,
        session_data: dict,
    ) -> bool:
        try:
            import psycopg2
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO study_versions (
                    project_name, field_name, revision, session_json, saved_at
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (
                    project_name,
                    field_name,
                    revision,
                    json.dumps(session_data["session"], ensure_ascii=False),
                    session_data["meta"].get("saved_at", ""),
                ),
            )
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as exc:
            st.warning(f"PostgreSQL version save: {exc}")
            return False

    def list_versions(self, project_name: str, field_name: str) -> list:
        try:
            import psycopg2
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT revision, saved_at
                FROM study_versions
                WHERE project_name = %s AND field_name = %s
                ORDER BY revision DESC
                """,
                (project_name, field_name),
            )
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return [
                {
                    "revision": row[0],
                    "saved_at": (
                        row[1].isoformat()
                        if hasattr(row[1], "isoformat")
                        else str(row[1])
                    ),
                }
                for row in rows
            ]
        except Exception as exc:
            st.warning(f"PostgreSQL version list: {exc}")
            return []

    def load_version(
        self,
        project_name: str,
        field_name: str,
        revision: int,
    ) -> dict:
        try:
            import psycopg2
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT session_json, saved_at
                FROM study_versions
                WHERE project_name = %s AND field_name = %s AND revision = %s
                """,
                (project_name, field_name, revision),
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if not row:
                return {}
            saved_at = (
                row[1].isoformat()
                if hasattr(row[1], "isoformat")
                else str(row[1])
            )
            return {
                "session": json.loads(row[0] or "{}"),
                "meta": {
                    "project_name": project_name,
                    "field_name": field_name,
                    "saved_at": saved_at,
                    "study_revision": revision,
                },
            }
        except Exception as exc:
            st.warning(f"PostgreSQL version load: {exc}")
            return {}

    def list_all_records(self) -> list:
        try:
            import psycopg2
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT project_name, field_name, phase, session_json,
                       completion_pct, auto_saved, saved_at
                FROM sessions
                ORDER BY saved_at DESC
                """
            )
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            result = []
            for row in rows:
                saved_at = (
                    row[6].isoformat()
                    if hasattr(row[6], "isoformat")
                    else str(row[6])
                )
                result.append(
                    {
                        "session": json.loads(row[3] or "{}"),
                        "meta": {
                            "project_name": row[0],
                            "field_name": row[1],
                            "project_phase": row[2] or "",
                            "completion": row[4],
                            "auto_saved": bool(row[5]),
                            "saved_at": saved_at,
                        },
                    }
                )
            return result
        except Exception as exc:
            st.warning(f"PostgreSQL record list: {exc}")
            return []

    def load(self, project_name: str, field_name: str) -> dict:
        try:
            import psycopg2
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT session_json, phase, saved_at, auto_saved,
                       study_id, study_owner
                FROM sessions
                WHERE project_name = %s AND field_name = %s
                """,
                (project_name, field_name),
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if not row:
                return {}
            session_json, phase, saved_at, auto_saved, study_id, study_owner = row
            return {
                "session": json.loads(session_json),
                "meta": {
                    "project_name": project_name,
                    "field_name": field_name,
                    "project_phase": phase or "",
                    "study_id": study_id or "",
                    "study_owner": study_owner or "",
                    "saved_at": (
                        saved_at.isoformat()
                        if hasattr(saved_at, "isoformat")
                        else str(saved_at)
                    ),
                    "auto_saved": bool(auto_saved),
                },
            }
        except Exception as exc:
            st.warning(f"PostgreSQL load: {exc}")
            return {}

    def list_all(self) -> list:
        try:
            import psycopg2
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT project_name, field_name, phase, completion_pct,
                       auto_saved, saved_at, session_json
                FROM sessions
                ORDER BY saved_at DESC
                """
            )
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            summaries = []
            for row in rows:
                payload = json.loads(row[6] or "{}")
                changes = payload.get("study_change_log", []) or [{}]
                latest = changes[-1]
                saved_at = (
                    row[5].isoformat()
                    if hasattr(row[5], "isoformat")
                    else str(row[5])
                )
                summaries.append(
                    {
                        "project_name": row[0],
                        "field_name": row[1],
                        "phase": row[2] or "—",
                        "completion": row[3],
                        "auto_saved": bool(row[4]),
                        "saved_at": saved_at,
                        "study_lifecycle": payload.get("study_lifecycle", "Draft"),
                        "study_revision": payload.get("study_revision", 0),
                        "last_edited_by": latest.get("actor", "local-user"),
                        "last_edited_at": latest.get("saved_at", saved_at),
                    }
                )
            return summaries
        except Exception as exc:
            st.warning(f"PostgreSQL list: {exc}")
            return []

    def delete(self, project_name: str, field_name: str) -> bool:
        try:
            import psycopg2
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM sessions WHERE project_name = %s AND field_name = %s",
                (project_name, field_name),
            )
            cursor.execute(
                "DELETE FROM study_versions WHERE project_name = %s AND field_name = %s",
                (project_name, field_name),
            )
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as exc:
            st.warning(f"PostgreSQL delete: {exc}")
            return False


@st.cache_resource
def get_db() -> SessionDB:
    return PostgresDB(DATABASE_URL) if USE_POSTGRESQL else SQLiteDB()
