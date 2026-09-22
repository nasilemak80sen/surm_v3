"""Canonical, versioned representation of a SURM study.

The StudyDocument is the durable study model. Streamlit session state is the
interactive UI layer; persistence and exports should round-trip through this
document so governance metadata cannot disappear between sessions.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


STUDY_KEYS = (
    "project_name",
    "field_name",
    "project_phase",
    "study_owner",
    "methodology_version",
    "team_members",
    "uncertainties",
    "key_decisions",
    "impact_assessment",
    "key_uncertainties",
    "resolution_list",
    "resolution_planner",
    "risk_register",
    "pra_output",
    # Governance / sign-off fields
    "prep_name",
    "prep_role",
    "prep_date",
    "rev_gg_name",
    "rev_gg_role",
    "rev_gg_date",
    "rev_re_name",
    "rev_re_role",
    "rev_re_date",
    "rev_pp_name",
    "rev_pp_role",
    "rev_pp_date",
    "endorsed_name",
    "endorsed_role",
    "endorsed_date",
    "study_lifecycle",
    "study_revision",
    "study_change_log",
    "workflow_revisions",
    "workflow_snapshots",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


@dataclass
class StudyDocument:
    """Durable study state independent of Streamlit widget state."""

    study_id: str = field(default_factory=lambda: str(uuid4()))
    schema_version: str = "2.1"

    project_name: str = ""
    field_name: str = ""
    project_phase: str = ""
    study_owner: str = "local-user"
    methodology_version: str = "SURM-2026.01"

    team_members: list[dict[str, Any]] = field(default_factory=list)
    uncertainties: list[dict[str, Any]] = field(default_factory=list)
    key_decisions: list[dict[str, Any]] = field(default_factory=list)
    impact_assessment: list[dict[str, Any]] = field(default_factory=list)
    key_uncertainties: list[dict[str, Any]] = field(default_factory=list)
    resolution_list: dict[str, Any] = field(default_factory=dict)
    resolution_planner: list[dict[str, Any]] = field(default_factory=list)
    risk_register: list[dict[str, Any]] = field(default_factory=list)
    pra_output: list[dict[str, Any]] = field(default_factory=list)

    # Governance / sign-off
    prep_name: str = ""
    prep_role: str = ""
    prep_date: str = ""
    rev_gg_name: str = ""
    rev_gg_role: str = ""
    rev_gg_date: str = ""
    rev_re_name: str = ""
    rev_re_role: str = ""
    rev_re_date: str = ""
    rev_pp_name: str = ""
    rev_pp_role: str = ""
    rev_pp_date: str = ""
    endorsed_name: str = ""
    endorsed_role: str = ""
    endorsed_date: str = ""

    study_lifecycle: str = "Draft"
    study_revision: int = 0
    study_change_log: list[dict[str, Any]] = field(default_factory=list)
    workflow_revisions: dict[str, int] = field(default_factory=dict)
    workflow_snapshots: dict[str, dict[str, int]] = field(default_factory=dict)

    @classmethod
    def from_session(cls, session: dict[str, Any]) -> "StudyDocument":
        defaults = {
            "project_name": "",
            "field_name": "",
            "project_phase": "",
            "study_owner": "local-user",
            "methodology_version": "SURM-2026.01",
            "team_members": [],
            "uncertainties": [],
            "key_decisions": [],
            "impact_assessment": [],
            "key_uncertainties": [],
            "resolution_list": {},
            "resolution_planner": [],
            "risk_register": [],
            "pra_output": [],
            "prep_name": "",
            "prep_role": "",
            "prep_date": "",
            "rev_gg_name": "",
            "rev_gg_role": "",
            "rev_gg_date": "",
            "rev_re_name": "",
            "rev_re_role": "",
            "rev_re_date": "",
            "rev_pp_name": "",
            "rev_pp_role": "",
            "rev_pp_date": "",
            "endorsed_name": "",
            "endorsed_role": "",
            "endorsed_date": "",
            "study_lifecycle": "Draft",
            "study_revision": 0,
            "study_change_log": [],
            "workflow_revisions": {},
            "workflow_snapshots": {},
        }

        values = {
            key: deepcopy(session.get(key, defaults[key]))
            for key in STUDY_KEYS
        }

        values["study_id"] = _text(session.get("study_id")) or str(uuid4())
        values["project_name"] = _text(values["project_name"])
        values["field_name"] = _text(values["field_name"])
        values["project_phase"] = _text(values["project_phase"])
        values["study_owner"] = _text(values.get("study_owner")) or "local-user"
        values["methodology_version"] = (
            _text(values.get("methodology_version")) or "SURM-2026.01"
        )
        values["study_lifecycle"] = (
            _text(values.get("study_lifecycle")) or "Draft"
        )

        try:
            values["study_revision"] = int(values.get("study_revision") or 0)
        except (TypeError, ValueError):
            values["study_revision"] = 0

        return cls(**values)

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "StudyDocument":
        session = dict(record.get("session", {}))
        meta = record.get("meta", {})

        for key in (
            "project_name",
            "field_name",
            "project_phase",
            "study_id",
            "study_lifecycle",
            "study_revision",
            "study_owner",
            "methodology_version",
        ):
            session.setdefault(key, meta.get(key))

        return cls.from_session(session)

    def to_dict(self) -> dict[str, Any]:
        return {
            key: deepcopy(getattr(self, key))
            for key in STUDY_KEYS
        } | {
            "study_id": self.study_id,
            "schema_version": self.schema_version,
        }

    def apply_to_session(
        self,
        session: Any,
        *,
        keys: set[str] | None = None,
    ) -> None:
        """Apply durable study values back into the interactive session."""
        values = self.to_dict()
        for key, value in values.items():
            if keys is not None and key not in keys:
                continue
            session[key] = deepcopy(value)


def normalize_study_record(record: dict[str, Any]) -> StudyDocument:
    """Normalize current and legacy records into one canonical document."""
    return StudyDocument.from_record(record)
