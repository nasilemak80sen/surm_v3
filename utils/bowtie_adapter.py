"""SURM ↔ Bowtie document adapter.

The Bowtie document follows the public gahoward/bowtie-diagram concepts:
stable node identities, separate visual placements, explicit line topology,
and one persisted document per risk. SURM remains authoritative for risk
assessment; this module only maps existing SURM data into Bowtie structure.
"""

from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from typing import Any


BOWTIE_SCHEMA_VERSION = "SURM-BOWTIE-1"


def _items(value: object) -> list[str]:
    raw = str(value or "")
    return [
        item.strip().lstrip("0123456789. -•")
        for item in re.split(r"[\n;]+", raw)
        if item.strip()
    ]


def _stable_id(prefix: str, text: str) -> str:
    digest = hashlib.sha1(text.strip().encode("utf-8")).hexdigest()[:10].upper()
    return f"{prefix}-{digest}"


def _source_signature(risk_row: dict[str, Any]) -> str:
    parts = [
        str(risk_row.get("risk_id", "")),
        str(risk_row.get("Risk", "")),
        str(risk_row.get("Uncertainty/Causes", "")),
        str(risk_row.get("Resolution Plan", "")),
        str(risk_row.get("Contingency Plan", "")),
        str(risk_row.get("Impact/Consequence", "")),
    ]
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()


def _find_uncertainty(name: str, uncertainties: list[dict[str, Any]]) -> dict[str, Any]:
    target = name.strip()
    for item in uncertainties:
        if str(item.get("name", "")).strip() == target:
            return item
    return {}


def build_bowtie_document(
    risk_row: dict[str, Any],
    *,
    uncertainties: list[dict[str, Any]],
    resolution_list: dict[str, Any],
    resolution_planner: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create one Bowtie document skeleton from a SURM risk row.

    The adapter deliberately does not invent engineering relationships:
    upstream SURM uncertainty → resolution associations seed the preventive
    side; consequences and mitigative barriers only appear when recorded in
    the risk row.
    """
    risk_id = str(risk_row.get("risk_id", "")).strip() or _stable_id(
        "RSK", str(risk_row.get("Risk", "Risk"))
    )
    risk_name = str(risk_row.get("Risk", "Risk Event")).strip()

    cause_names = _items(risk_row.get("Uncertainty/Causes"))
    consequence_names = _items(risk_row.get("Impact/Consequence"))
    mitigative_names = _items(risk_row.get("Contingency Plan"))

    library = {
        "cause": [],
        "outcome": [],
        "preventativeBarrier": [],
        "mitigativeBarrier": [],
    }
    causes = []
    outcomes = []
    preventative = []
    mitigative = []
    lines = []

    cause_node_by_name: dict[str, dict[str, Any]] = {}
    cause_placement_by_name: dict[str, dict[str, Any]] = {}

    y_start = 110
    y_gap = 120

    for index, name in enumerate(cause_names, start=1):
        source = _find_uncertainty(name, uncertainties)
        node_id = str(source.get("uncertainty_id") or _stable_id("UNC", name))
        node = {
            "id": node_id,
            "type": "cause",
            "name": name,
            "description": "",
            "surm_source": {
                "type": "uncertainty",
                "uncertainty_id": node_id,
            },
        }
        library["cause"].append(node)
        placement = {
            "id": f"CAUSE-PLACEMENT-{index}",
            "nodeId": node_id,
            "x": 120,
            "y": y_start + (index - 1) * y_gap,
            "w": 210,
            "h": 70,
            "pageId": "PAGE_1",
        }
        causes.append(placement)
        cause_node_by_name[name] = node
        cause_placement_by_name[name] = placement

    # One preventive barrier identity per resolution option, with associations
    # derived from the uncertainty-specific resolution mapping.
    barrier_by_option: dict[str, dict[str, Any]] = {}
    barrier_counter = 0
    for cause_name in cause_names:
        options = resolution_list.get(cause_name, {}) or {}
        for option, enabled in options.items():
            if enabled != "Y":
                continue
            option = str(option).strip()
            if not option:
                continue
            if option in barrier_by_option:
                continue

            barrier_counter += 1
            planner_match = next(
                (
                    row for row in resolution_planner
                    if str(row.get("Resolution Action", "")).strip() == option
                ),
                {},
            )
            barrier_id = str(
                planner_match.get("resolution_id")
                or _stable_id("RES", option)
            )
            barrier = {
                "id": barrier_id,
                "type": "preventativeBarrier",
                "name": option,
                "description": str(planner_match.get("Description", "") or ""),
                "owner": str(planner_match.get("Action Owner", "") or ""),
                "effectiveness": "",
                "degradation_factors": [],
                "controls": [],
                "surm_source": {
                    "type": "resolution",
                    "resolution_action": option,
                    "resolution_id": barrier_id,
                },
            }
            barrier_by_option[option] = {
                "node": barrier,
                "index": barrier_counter,
                "cause_names": [],
            }
            library["preventativeBarrier"].append(barrier)

        for option, enabled in options.items():
            if enabled == "Y" and str(option).strip() in barrier_by_option:
                barrier_by_option[str(option).strip()]["cause_names"].append(cause_name)

    for option, item in barrier_by_option.items():
        index = item["index"]
        placement = {
            "id": f"PREVENTIVE-PLACEMENT-{index}",
            "nodeId": item["node"]["id"],
            "x": 380 + ((index - 1) % 3) * 130,
            "y": 115 + ((index - 1) // 3) * 145,
            "w": 120,
            "h": 112,
            "pageId": "PAGE_1",
        }
        preventative.append(placement)

    preventative_lookup = {
        item["node"]["id"]: placement
        for placement in preventative
        for item in barrier_by_option.values()
    }

    # Each cause owns one line; each line stops at the preventive barriers
    # associated with that cause. The visual renderer can therefore reproduce
    # shared barriers without duplicating the barrier identity.
    for index, cause_name in enumerate(cause_names, start=1):
        stops = []
        for item in barrier_by_option.values():
            if cause_name in item["cause_names"]:
                stops.append(
                    f"PREVENTIVE-PLACEMENT-{item['index']}"
                )
        lines.append({
            "id": f"LINE-CAUSE-{index}",
            "originType": "cause",
            "originId": f"CAUSE-PLACEMENT-{index}",
            "stops": stops,
            "pageId": "PAGE_1",
        })

    for index, name in enumerate(consequence_names, start=1):
        outcome_id = _stable_id("OUT", name)
        node = {
            "id": outcome_id,
            "type": "outcome",
            "name": name,
            "description": "",
            "surm_source": {"type": "risk_consequence"},
        }
        library["outcome"].append(node)
        outcomes.append({
            "id": f"OUTCOME-PLACEMENT-{index}",
            "nodeId": outcome_id,
            "x": 1080,
            "y": y_start + (index - 1) * y_gap,
            "w": 210,
            "h": 70,
            "pageId": "PAGE_1",
        })

    for index, name in enumerate(mitigative_names, start=1):
        barrier_id = _stable_id("MIT", name)
        planner_match = next(
            (
                row for row in resolution_planner
                if str(row.get("Resolution Action", "")).strip() == name
            ),
            {},
        )
        node = {
            "id": barrier_id,
            "type": "mitigativeBarrier",
            "name": name,
            "description": str(planner_match.get("Description", "") or ""),
            "owner": str(planner_match.get("Action Owner", "") or ""),
            "effectiveness": "",
            "degradation_factors": [],
            "controls": [],
            "surm_source": {"type": "risk_contingency"},
        }
        library["mitigativeBarrier"].append(node)
        mitigative.append({
            "id": f"MITIGATIVE-PLACEMENT-{index}",
            "nodeId": barrier_id,
            "x": 790 + ((index - 1) % 3) * 90,
            "y": y_start + ((index - 1) // 3) * 145,
            "w": 46,
            "h": 96,
            "pageId": "PAGE_1",
        })

    for outcome_index, outcome in enumerate(outcomes, start=1):
        lines.append({
            "id": f"LINE-OUTCOME-{outcome_index}",
            "originType": "outcome",
            "originId": outcome["id"],
            "stops": [
                placement["id"] for placement in mitigative
            ],
            "pageId": "PAGE_1",
        })

    return {
        "version": BOWTIE_SCHEMA_VERSION,
        "risk_id": risk_id,
        "name": risk_name,
        "source_signature": _source_signature(risk_row),
        "pages": [{
            "id": "PAGE_1",
            "name": risk_name or "Risk Bowtie",
            "description": "SURM Risk Bowtie",
            "topLevelEvent": {
                "id": "TLE_1",
                "name": risk_name,
            },
            "hazard": {
                "id": "HAZARD_1",
                "name": "Subsurface Risk",
            },
        }],
        "causes": causes,
        "outcomes": outcomes,
        "preventativeBarriers": preventative,
        "mitigativeBarriers": mitigative,
        "lines": lines,
        "library": library,
        "editor_revision": 0,
        "layout_version": 2,
        "layout": {
            placement["id"]: {
                "x": placement["x"],
                "y": placement["y"],
                "w": placement["w"],
                "h": placement["h"],
            }
            for placement in [*causes, *preventative, *mitigative, *outcomes]
        },
        "metadata": {
            "risk_id": risk_id,
            "surm_managed": True,
        },
    }


def ensure_bowtie_register(
    risk_rows: list[dict[str, Any]],
    *,
    current: dict[str, Any] | None,
    uncertainties: list[dict[str, Any]],
    resolution_list: dict[str, Any],
    resolution_planner: list[dict[str, Any]],
) -> dict[str, Any]:
    """Ensure every current risk has a persisted Bowtie document.

    Existing diagrams are preserved even when the upstream risk changes; the
    source_signature lets the UI tell the engineer that a refresh is available.
    """
    current_register = deepcopy(current or {})
    result: dict[str, Any] = {}

    for row in risk_rows:
        risk_id = str(row.get("risk_id", "")).strip()
        if not risk_id:
            continue

        existing = current_register.get(risk_id)
        if existing:
            result[risk_id] = existing
            if existing.get("source_signature") != _source_signature(row):
                result[risk_id]["needs_refresh"] = True
            continue

        result[risk_id] = build_bowtie_document(
            row,
            uncertainties=uncertainties,
            resolution_list=resolution_list,
            resolution_planner=resolution_planner,
        )

    return result


def refresh_bowtie_document(
    risk_row: dict[str, Any],
    *,
    uncertainties: list[dict[str, Any]],
    resolution_list: dict[str, Any],
    resolution_planner: list[dict[str, Any]],
) -> dict[str, Any]:
    return build_bowtie_document(
        risk_row,
        uncertainties=uncertainties,
        resolution_list=resolution_list,
        resolution_planner=resolution_planner,
    )
