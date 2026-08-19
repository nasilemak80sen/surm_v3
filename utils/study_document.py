"""Canonical, versioned representation of a SURM study."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


STUDY_KEYS = (
    "project_name", "field_name", "project_phase", "study_owner", "team_members",
    "uncertainties", "key_decisions", "impact_assessment",
    "key_uncertainties", "resolution_list", "resolution_planner",
    "risk_register", "pra_output", "study_lifecycle", "study_revision",
    "study_change_log",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


@dataclass
class StudyDocument:
    """Durable study state independent of Streamlit widget state."""

    study_id: str = field(default_factory=lambda: str(uuid4()))
    schema_version: str = "2.0"
    project_name: str = ""
    field_name: str = ""
    project_phase: str = ""
    study_owner: str = "local-user"
    team_members: list[dict[str, Any]] = field(default_factory=list)
    uncertainties: list[dict[str, Any]] = field(default_factory=list)
    key_decisions: list[dict[str, Any]] = field(default_factory=list)
    impact_assessment: list[dict[str, Any]] = field(default_factory=list)
    key_uncertainties: list[dict[str, Any]] = field(default_factory=list)
    resolution_list: dict[str, Any] = field(default_factory=dict)
    resolution_planner: list[dict[str, Any]] = field(default_factory=list)
    risk_register: list[dict[str, Any]] = field(default_factory=list)
    pra_output: list[dict[str, Any]] = field(default_factory=list)
    study_lifecycle: str = "Draft"
    study_revision: int = 0
    study_change_log: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_session(cls, session: dict[str, Any]) -> "StudyDocument":
        defaults = {
            "project_name": "", "field_name": "", "project_phase": "",
            "study_owner": "local-user",
            "team_members": [], "uncertainties": [], "key_decisions": [],
            "impact_assessment": [], "key_uncertainties": [], "resolution_list": {},
            "resolution_planner": [], "risk_register": [], "pra_output": [],
            "study_lifecycle": "Draft", "study_revision": 0,
            "study_change_log": [],
        }
        values = {key: deepcopy(session.get(key, defaults[key])) for key in STUDY_KEYS}
        values["study_id"] = _text(session.get("study_id")) or str(uuid4())
        values["project_name"] = _text(values["project_name"])
        values["field_name"] = _text(values["field_name"])
        values["project_phase"] = _text(values["project_phase"])
        values["study_lifecycle"] = _text(values.get("study_lifecycle")) or "Draft"
        try:
            values["study_revision"] = int(values.get("study_revision") or 0)
        except (TypeError, ValueError):
            values["study_revision"] = 0
        return cls(**values)

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "StudyDocument":
        session = dict(record.get("session", {}))
        meta = record.get("meta", {})
        for key in ("project_name", "field_name", "project_phase", "study_id", "study_lifecycle", "study_revision"):
            session.setdefault(key, meta.get(key))
        return cls.from_session(session)

    def to_dict(self) -> dict[str, Any]:
        return {key: deepcopy(getattr(self, key)) for key in STUDY_KEYS} | {
            "study_id": self.study_id,
            "schema_version": self.schema_version,
        }

    def apply_to_session(self, session: Any, *, keys: set[str] | None = None) -> None:
        values = self.to_dict()
        for key, value in values.items():
            if keys is not None and key not in keys:
                continue
            session[key] = deepcopy(value)


def normalize_study_record(record: dict[str, Any]) -> StudyDocument:
    """Normalize current and legacy records into one canonical document."""

    return StudyDocument.from_record(record)