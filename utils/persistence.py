"""
utils/persistence.py
Session persistence — delegates to SQLite or PostgreSQL via db.py
"""
import json
import streamlit as st
from utils.db import get_db

_SKIP_EXACT  = {"_mapping", "_last_saved", "_last_save_auto"}
_SKIP_PREFIX = ("si_", "FormSubmitter:", "_", "unc_")


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

    from datetime import datetime
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
    return ok


def list_sessions() -> list:
    """Return all saved sessions as a list of dicts, newest first."""
    db = get_db()
    return db.list_all()


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
        return True
    except Exception:
        return False


def delete_session(project_name: str, field_name: str) -> bool:
    """Delete a session from database."""
    db = get_db()
    return db.delete(project_name, field_name)
