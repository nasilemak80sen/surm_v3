"""Deployment-aware identity and authorization helpers for SURM.

The local workflow remains usable without an authentication provider. In a
secured deployment, SURM_AUTH_REQUIRED=1 must be enabled and the Streamlit
identity plus SURM_ROLE_MAP provide the authorization boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any

import streamlit as st


ROLE_NAMES = ("Viewer", "Author", "Reviewer", "Approver", "Admin")


@dataclass(frozen=True)
class Identity:
    subject: str
    email: str
    name: str
    roles: frozenset[str]
    authenticated: bool
    source: str

    @property
    def label(self) -> str:
        return self.email or self.name or self.subject or "local-user"


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def auth_required() -> bool:
    return _truthy(os.environ.get("SURM_AUTH_REQUIRED", ""))


def _configured_role_map() -> dict[str, set[str]]:
    raw = os.environ.get("SURM_ROLE_MAP", "").strip()
    if not raw:
        try:
            raw = str(st.secrets.get("SURM_ROLE_MAP", "")).strip()
        except Exception:
            raw = ""
    if not raw:
        return {}

    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        return {}

    if not isinstance(payload, dict):
        return {}

    result: dict[str, set[str]] = {}
    for identity, roles in payload.items():
        if isinstance(roles, str):
            roles = [roles]
        if not isinstance(roles, (list, tuple, set)):
            continue
        result[str(identity).strip().lower()] = {
            str(role).strip()
            for role in roles
            if str(role).strip() in ROLE_NAMES
        }
    return result


def _streamlit_identity() -> Identity | None:
    user = getattr(st, "user", None)
    if user is None:
        return None

    authenticated = bool(getattr(user, "is_logged_in", False))
    email = str(getattr(user, "email", "") or "").strip()
    name = str(getattr(user, "name", "") or "").strip()
    subject = str(
        getattr(user, "sub", "")
        or getattr(user, "id", "")
        or email
        or name
    ).strip()

    if not authenticated and not any((email, name, subject)):
        return None

    lookup = (email or subject or name).lower()
    roles = frozenset(_configured_role_map().get(lookup, set()))

    return Identity(
        subject=subject,
        email=email,
        name=name,
        roles=roles,
        authenticated=authenticated,
        source="streamlit.user",
    )


def resolve_identity() -> Identity:
    """Resolve deployment identity without inventing authentication."""
    identity = _streamlit_identity()
    if identity is not None:
        return identity

    if auth_required():
        return Identity(
            subject="",
            email="",
            name="",
            roles=frozenset(),
            authenticated=False,
            source="unauthenticated",
        )

    return Identity(
        subject="local-user",
        email="",
        name="Local User",
        roles=frozenset(ROLE_NAMES),
        authenticated=False,
        source="local-development",
    )


def current_user_label() -> str:
    return resolve_identity().label


def current_user_roles() -> frozenset[str]:
    return resolve_identity().roles


def _owner_matches(session: dict[str, Any], identity: Identity) -> bool:
    owner = str(session.get("study_owner", "") or "").strip().lower()
    if not owner or owner == "local-user":
        return True
    candidates = {
        identity.subject.lower(),
        identity.email.lower(),
        identity.name.lower(),
        identity.label.lower(),
    }
    return owner in {item for item in candidates if item}


def can_perform(
    session: dict[str, Any],
    required_role: str = "Author",
) -> tuple[bool, str]:
    """Return whether the active identity may perform a study mutation."""
    if not auth_required():
        return True, ""

    identity = resolve_identity()
    if not identity.authenticated:
        return False, "Authenticated identity is required for this deployment."

    if required_role not in ROLE_NAMES:
        return False, f"Unknown authorization role: {required_role}."

    if "Admin" not in identity.roles and required_role not in identity.roles:
        return False, (
            f'Your authenticated identity is not assigned the "{required_role}" role.'
        )

    if (
        required_role != "Viewer"
        and not _owner_matches(session, identity)
        and "Admin" not in identity.roles
    ):
        return False, "This study is owned by a different authenticated identity."

    return True, ""


def can_edit_study(session: dict[str, Any]) -> tuple[bool, str]:
    role = str(session.get("study_role", "Author") or "Author")
    if role == "Viewer":
        return False, "Viewer role is read-only."
    return can_perform(session, role if role in ROLE_NAMES else "Author")


def can_delete_study() -> tuple[bool, str]:
    if not auth_required():
        return True, ""
    identity = resolve_identity()
    if not identity.authenticated:
        return False, "Authenticated identity is required to delete studies."
    if "Admin" not in identity.roles:
        return False, "Only an authenticated Admin may delete saved studies."
    return True, ""


def role_is_granted(session: dict[str, Any]) -> tuple[bool, str]:
    role = str(session.get("study_role", "Author") or "Author")
    if not auth_required():
        return True, ""
    identity = resolve_identity()
    if not identity.authenticated:
        return False, "Authenticated identity is required for lifecycle actions."
    if role not in identity.roles and "Admin" not in identity.roles:
        return False, f'Your authenticated identity is not granted the "{role}" study role.'
    return True, ""
