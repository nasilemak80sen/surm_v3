"""
utils/persistence.py
Session persistence — delegates to SQLite or PostgreSQL via db.py
"""
import json
from datetime import datetime
import streamlit as st
from utils.db import get_db

_SKIP_EXACT  = {"_mapping", "_last_saved", "_last_save_auto", "_resume_message", "_resume_attempted"}
_SKIP_PREFIX = ("_", "unc_")


def _completion(session: dict) -> int:
    """Calculate completion percentage."""
    checks = [
        bool(session.get("project_name", "")),
        any(u.get("selected") for u in session.get("uncertainties", [])),
        bool(session.get("key_decisions", [])),
        bool(session.get("impact_assessment", [])),
        bool(session.get("key_uncertainties", [])),
        bool(session.get("resolution_list", {})),
        bool(session.get("resolution_planner", [])),
        bool(session.get("risk_register", [])),
    ]
    return int(sum(checks) / len(checks) * 100)


def save_session(auto: bool = False) -> bool:
    """
    Persist current session to database (SQLite or PostgreSQL).
    Overwrites if session for this project/field already exists.
    Returns True on success.
    """
    db = get_db()
    project = st.session_state.get("project_name", "").strip()
    field   = st.session_state.get("field_name", "").strip()

    if not project:
        return False

    payload = {}
    for key, val in st.session_state.items():
        if key in _SKIP_EXACT:
            continue
        if any(key.startswith(p) for p in _SKIP_PREFIX):
            continue
        try:
            json.dumps(val)
            payload[key] = val
        except (TypeError, ValueError):
            pass

    now = datetime.now().isoformat(timespec="seconds")
    data = {
        "meta": {
            "project_name":  project,
            "field_name":    field,
            "project_phase": st.session_state.get("project_phase", ""),
            "saved_at":      now,
            "auto_saved":    auto,
            "completion":    _completion(payload),
            "version":       "1.1",
        },
        "session": payload,
    }

    ok = db.save(project, field, data)
    if ok:
        st.session_state["_last_saved"]     = now
        st.session_state["_last_save_auto"] = auto
        st.session_state["_resume_message"] = ""
    return ok


def list_sessions() -> list:
    """Return all saved sessions as a list of dicts, newest first."""
    db = get_db()
    return db.list_all()


def _has_user_progress(session: dict) -> bool:
    """Return True when there is meaningful user work already in session state."""
    if session.get("project_name", "").strip() or session.get("field_name", "").strip() or session.get("project_phase", "").strip():
        return True
    if any(u.get("selected") for u in session.get("uncertainties", [])):
        return True
    if session.get("impact_assessment"):
        return True
    if session.get("key_uncertainties"):
        return True
    if session.get("resolution_planner"):
        return True
    if session.get("risk_register"):
        return True
    if any((member.get("Name") or "").strip() for member in session.get("team_members", [])):
        return True
    return False


def load_session(project_name: str, field_name: str) -> bool:
    """Restore session state from database. Returns True on success."""
    db = get_db()
    data = db.load(project_name, field_name)
    if not data:
        return False
    try:
        mapping = st.session_state.get("_mapping")
        for key, val in data.get("session", {}).items():
            st.session_state[key] = val
        if mapping:
            st.session_state["_mapping"] = mapping
        meta = data.get("meta", {})
        st.session_state["_last_saved"] = meta.get("saved_at", "")
        st.session_state["_last_save_auto"] = bool(meta.get("auto_saved", False))
        st.session_state["_resume_message"] = f"Resumed saved session: {project_name}"
        return True
    except Exception:
        return False


def load_session_record(session_meta: dict) -> bool:
    """Load a saved session using the metadata from the session list."""
    project_name = (session_meta or {}).get("project_name", "").strip()
    field_name = (session_meta or {}).get("field_name", "").strip()
    if not project_name or not field_name:
        return False
    return load_session(project_name, field_name)


def get_latest_session() -> dict:
    """Return the most recently saved session, if any."""
    sessions = list_sessions()
    return sessions[0] if sessions else {}


def resume_latest_session() -> bool:
    """Auto-restore the most recent saved session when the user opens a fresh app."""
    if st.session_state.get("_resume_attempted"):
        return False
    if _has_user_progress(st.session_state):
        return False
    latest = get_latest_session()
    if not latest:
        return False
    ok = load_session_record(latest)
    if ok:
        st.session_state["_resume_attempted"] = True
    return ok


def delete_session(project_name: str, field_name: str) -> bool:
    """Delete a session from database."""
    db = get_db()
    return db.delete(project_name, field_name)
