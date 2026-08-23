"""
utils/persistence.py
Session persistence — delegates to SQLite or PostgreSQL via db.py
"""
import json
from datetime import datetime
import streamlit as st
from utils.db import get_db
from utils.session import DEFAULT_SESSION_STATE
from utils.study_document import StudyDocument
from utils.workflow import completion_percent
import math

_SKIP_EXACT  = {"_mapping", "_last_saved", "_last_save_auto", "_resume_message", "_resume_attempted"}
_SKIP_PREFIX = ("_", "unc_")


def _completion(session: dict) -> int:
    """Calculate completion using the authoritative workflow engine."""
    return completion_percent(session)


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

    # honor user preference for auto-save
    if auto and not st.session_state.get("_auto_save_enabled", True):
        return False

    payload = {}
    def _sanitize(o):
        """Recursively convert values to JSON-safe types."""
        # primitives
        if o is None:
            return o
        if isinstance(o, (str, bool, int)):
            return o
        if isinstance(o, float):
            if math.isnan(o):
                return ""
            return float(o)
        # lists/tuples
        if isinstance(o, (list, tuple)):
            return [_sanitize(x) for x in o]
        # dicts
        if isinstance(o, dict):
            return {str(k): _sanitize(v) for k, v in o.items()}
        # fallback to string
        try:
            return str(o)
        except Exception:
            return ""

    document = StudyDocument.from_session(dict(st.session_state))
    document.study_revision = int(st.session_state.get("study_revision", 0)) + 1
    document.study_change_log = list(document.study_change_log or []) + [{
        "revision": document.study_revision,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "actor": document.study_owner,
        "action": "save",
    }]
    document_dict = document.to_dict()
    for key, val in document_dict.items():
        safe_val = _sanitize(val)
        json.dumps(safe_val)
        payload[key] = safe_val

    now = datetime.now().isoformat(timespec="seconds")
    revision = document.study_revision
    data = {
        "meta": {
            "project_name":  project,
            "field_name":    field,
            "project_phase": st.session_state.get("project_phase", ""),
            "saved_at":      now,
            "auto_saved":    auto,
            "completion":    _completion(payload),
            "version":       "1.1",
            "study_revision": revision,
            "study_lifecycle": st.session_state.get("study_lifecycle", "Draft"),
            "study_id": document.study_id,
            "study_owner": document.study_owner,
        },
        "session": payload,
    }

    ok = db.save_bundle(project, field, revision, data)
    if ok:
        st.session_state["_last_saved"]     = now
        st.session_state["_last_save_auto"] = auto
        st.session_state["_resume_message"] = ""
        st.session_state["study_revision"] = revision
        st.session_state["study_id"] = document.study_id
        verified = db.load(project, field)
        saved_document = StudyDocument.from_record(verified) if verified else None
        if not saved_document or saved_document.to_dict() != document.to_dict():
            st.warning("The study was saved but could not be verified. Please retry.")
            return False
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


def load_session(project_name: str, field_name: str, phase_name: str = "") -> bool:
def load_session(project_name: str, field_name: str, phase_name: str = "") -> bool:
    """Restore session state from database. Returns True on success."""
    db = get_db()
    data = db.load(project_name, field_name)
    if not data:
        return False
    try:
        mapping = st.session_state.get("_mapping")
        document = StudyDocument.from_record(data)
        saved_keys = set(data.get("session", {}))
        document.apply_to_session(st.session_state, keys=saved_keys)
        if mapping:
            st.session_state["_mapping"] = mapping
        meta = data.get("meta", {})
        # Older saves may contain an empty session payload because durable
        # keys were not registered. The database row still has study identity.
        st.session_state["project_name"] = (
            data.get("session", {}).get("project_name")
            or meta.get("project_name")
            or ""
        )
        st.session_state["field_name"] = (
            data.get("session", {}).get("field_name")
            or meta.get("field_name")
            or ""
        )
        st.session_state["project_phase"] = (
            data.get("session", {}).get("project_phase")
            or meta.get("project_phase")
            or phase_name
            or ""
        )
        # Older saves may contain an empty session payload because durable
        # keys were not registered. The database row still has study identity.
        st.session_state["project_name"] = (
            data.get("session", {}).get("project_name")
            or meta.get("project_name")
            or ""
        )
        st.session_state["field_name"] = (
            data.get("session", {}).get("field_name")
            or meta.get("field_name")
            or ""
        )
        st.session_state["project_phase"] = (
            data.get("session", {}).get("project_phase")
            or meta.get("project_phase")
            or phase_name
            or ""
        )
        st.session_state["_last_saved"] = meta.get("saved_at", "")
        st.session_state["_last_save_auto"] = bool(meta.get("auto_saved", False))
        st.session_state["study_revision"] = int(meta.get("study_revision", data.get("session", {}).get("study_revision", 0)) or 0)
        st.session_state["study_lifecycle"] = meta.get("study_lifecycle", data.get("session", {}).get("study_lifecycle", "Draft"))
        st.session_state["study_id"] = (
            data.get("session", {}).get("study_id")
            or meta.get("study_id")
            or st.session_state.get("study_id", "")
        )
        st.session_state["study_owner"] = (
            data.get("session", {}).get("study_owner")
            or meta.get("study_owner")
            or st.session_state.get("study_owner", "local-user")
        )
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
    phase_name = (session_meta or {}).get("phase", "")
    if phase_name:
        return load_session(project_name, field_name, phase_name)
    phase_name = (session_meta or {}).get("phase", "")
    if phase_name:
        return load_session(project_name, field_name, phase_name)
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
