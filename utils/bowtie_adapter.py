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


def _source_signature(
    risk_row: dict[str, Any],
    resolution_planner: list[dict[str, Any]] | None = None,
) -> str:
    parts = [
        str(risk_row.get("risk_id", "")),
        str(risk_row.get("Risk", "")),
        str(risk_row.get("Uncertainty/Causes", "")),
        str(risk_row.get("Resolution Plan", "")),
        str(risk_row.get("Contingency Plan", "")),
        str(risk_row.get("Impact/Consequence", "")),
    ]

    planner_map = {}
    for row in resolution_planner or []:
        if not isinstance(row, dict):
            continue
        action = str(row.get("Resolution Action", "") or "").strip()
        if not action:
            continue
        planner_map[action] = (
            str(row.get("resolution_id", "") or "").strip(),
            str(row.get("Action Owner", "") or "").strip(),
            str(row.get("Description", "") or "").strip(),
        )

    for action in _items(risk_row.get("Resolution Plan")):
        planner_id, owner, description = planner_map.get(action, ("", "", ""))
        parts.extend([action, planner_id, owner, description])

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

    # The Risk Register is the canonical Bowtie input. Only resolution
    # actions actually written into this risk row become preventive barriers.
    # Do not re-read the full upstream resolution mapping here: doing so can
    # silently re-introduce options the user did not select for this risk.
    selected_resolution_names = list(dict.fromkeys(
        _items(risk_row.get("Resolution Plan"))
    ))

    barrier_by_option: dict[str, dict[str, Any]] = {}
    barrier_counter = 0

    for option in selected_resolution_names:
        planner_match = next(
            (
                row for row in resolution_planner
                if str(row.get("Resolution Action", "")).strip() == option
            ),
            {},
        )
        barrier_counter += 1
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
            "cause_names": list(cause_names),
        }
        library["preventativeBarrier"].append(barrier)

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
        "source_signature": _source_signature(risk_row, resolution_planner),
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


_GENERATED_SOURCE_TYPES = {
    "uncertainty",
    "resolution",
    "risk_consequence",
    "risk_contingency",
}


def _source_key(node: dict[str, Any]) -> tuple[str, str] | None:
    """Return a stable identity for SURM-generated Bowtie nodes."""
    source = node.get("surm_source") or {}
    source_type = str(source.get("type", "") or "").strip()

    if source_type == "uncertainty":
        identity = str(
            source.get("uncertainty_id")
            or node.get("id")
            or node.get("name")
            or ""
        ).strip()
    elif source_type == "resolution":
        identity = str(
            source.get("resolution_id")
            or source.get("resolution_action")
            or node.get("name")
            or ""
        ).strip()
    elif source_type in {"risk_consequence", "risk_contingency"}:
        identity = str(node.get("name", "") or "").strip()
    else:
        return None

    return (source_type, identity) if identity else None


def _merge_generated_category(
    existing: dict[str, Any],
    desired: dict[str, Any],
    *,
    placement_key: str,
    library_key: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    """Merge SURM-generated nodes while preserving manual nodes and layout."""
    existing_nodes = [
        node for node in (existing.get("library", {}).get(library_key, []) or [])
        if isinstance(node, dict)
    ]
    desired_nodes = [
        node for node in (desired.get("library", {}).get(library_key, []) or [])
        if isinstance(node, dict)
    ]
    existing_placements = [
        placement for placement in (existing.get(placement_key, []) or [])
        if isinstance(placement, dict)
    ]
    desired_placements = [
        placement for placement in (desired.get(placement_key, []) or [])
        if isinstance(placement, dict)
    ]

    existing_generated = {
        _source_key(node): node
        for node in existing_nodes
        if _source_key(node) is not None
    }

    merged_nodes = [
        deepcopy(node)
        for node in existing_nodes
        if _source_key(node) is None
    ]
    merged_placements = [
        deepcopy(placement)
        for placement in existing_placements
        if not _source_key(
            next(
                (
                    node for node in existing_nodes
                    if str(node.get("id", "")) == str(placement.get("nodeId", ""))
                ),
                {},
            )
        )
    ]

    desired_node_id_to_actual: dict[str, str] = {}
    desired_placement_id_to_actual: dict[str, str] = {}

    for desired_node in desired_nodes:
        key = _source_key(desired_node)
        current = existing_generated.get(key) if key else None

        if current:
            merged = deepcopy(current)
            merged["name"] = desired_node.get("name", merged.get("name", ""))
            merged["description"] = desired_node.get(
                "description",
                merged.get("description", ""),
            )
            if desired_node.get("type") in {
                "preventativeBarrier",
                "mitigativeBarrier",
            }:
                merged["owner"] = desired_node.get(
                    "owner",
                    merged.get("owner", ""),
                )
            merged["surm_source"] = deepcopy(
                desired_node.get("surm_source", merged.get("surm_source", {}))
            )
            actual_id = str(current.get("id", ""))
            merged_nodes.append(merged)
        else:
            merged = deepcopy(desired_node)
            actual_id = str(merged.get("id", ""))
            merged_nodes.append(merged)

        desired_node_id_to_actual[str(desired_node.get("id", ""))] = actual_id

    existing_placement_by_node = {
        str(placement.get("nodeId", "")): placement
        for placement in existing_placements
        if isinstance(placement, dict)
    }

    used_placement_ids = {
        str(placement.get("id", ""))
        for placement in existing_placements
        if placement.get("id")
    }

    for desired_placement in desired_placements:
        desired_node_id = str(desired_placement.get("nodeId", ""))
        actual_node_id = desired_node_id_to_actual.get(desired_node_id, desired_node_id)
        current_placement = existing_placement_by_node.get(actual_node_id)

        if current_placement:
            # Preserve existing position/size exactly. Reconciliation must not
            # turn a source update into an implicit layout operation.
            merged_placements.append(deepcopy(current_placement))
            desired_placement_id_to_actual[str(desired_placement.get("id", ""))] = str(
                current_placement.get("id", "")
            )
            continue

        new_placement = deepcopy(desired_placement)
        new_placement["nodeId"] = actual_node_id
        placement_id = str(new_placement.get("id", ""))
        while placement_id in used_placement_ids:
            placement_id = f"{placement_id}-NEW"
        new_placement["id"] = placement_id
        used_placement_ids.add(placement_id)
        merged_placements.append(new_placement)
        desired_placement_id_to_actual[str(desired_placement.get("id", ""))] = placement_id

    return merged_nodes, merged_placements, desired_placement_id_to_actual


def reconcile_bowtie_document(
    existing: dict[str, Any],
    risk_row: dict[str, Any],
    *,
    uncertainties: list[dict[str, Any]],
    resolution_list: dict[str, Any],
    resolution_planner: list[dict[str, Any]],
) -> dict[str, Any]:
    """Synchronise risk-form data into an existing Bowtie without rebuilding it.

    SURM-generated nodes are updated/added/removed from the current Risk
    Register inputs. Manual Bowtie nodes, edits, relationships and placements
    remain intact. Layout is never created as a side effect of synchronisation.
    """
    desired = build_bowtie_document(
        risk_row,
        uncertainties=uncertainties,
        resolution_list=resolution_list,
        resolution_planner=resolution_planner,
    )
    result = deepcopy(existing)

    result["risk_id"] = desired["risk_id"]
    result["name"] = desired["name"]
    result["source_signature"] = desired["source_signature"]
    result["needs_refresh"] = False

    pages = result.get("pages") or desired.get("pages") or []
    if not pages:
        pages = deepcopy(desired.get("pages", []))
    if pages:
        pages[0]["name"] = desired["name"]
        pages[0]["topLevelEvent"] = {
            **(pages[0].get("topLevelEvent") or {}),
            "name": desired["name"],
        }
    result["pages"] = pages

    placement_maps = {}
    for category in (
        ("causes", "cause"),
        ("preventativeBarriers", "preventativeBarrier"),
        ("mitigativeBarriers", "mitigativeBarrier"),
        ("outcomes", "outcome"),
    ):
        merged_nodes, merged_placements, id_map = _merge_generated_category(
            result,
            desired,
            placement_key=category[0],
            library_key=category[1],
        )
        result.setdefault("library", {})[category[1]] = merged_nodes
        result[category[0]] = merged_placements
        placement_maps[category[0]] = id_map

    # Build lookup for the resulting node source type so relationship updates
    # preserve links to manual barriers while replacing only SURM-generated stops.
    placement_source_types: dict[str, str] = {}
    library = result.get("library", {}) or {}
    for placement_key, library_key in (
        ("causes", "cause"),
        ("preventativeBarriers", "preventativeBarrier"),
        ("mitigativeBarriers", "mitigativeBarrier"),
        ("outcomes", "outcome"),
    ):
        nodes_by_id = {
            str(node.get("id", "")): node
            for node in library.get(library_key, []) or []
            if isinstance(node, dict)
        }
        for placement in result.get(placement_key, []) or []:
            node = nodes_by_id.get(str(placement.get("nodeId", "")))
            if node:
                source_type = str((node.get("surm_source") or {}).get("type", ""))
                placement_source_types[str(placement.get("id", ""))] = source_type

    desired_lines = []
    for desired_line in desired.get("lines", []) or []:
        origin_id = str(desired_line.get("originId", ""))
        mapped_origin = origin_id
        for id_map in placement_maps.values():
            mapped_origin = id_map.get(origin_id, mapped_origin)
        if mapped_origin == origin_id and not any(
            str(p.get("id", "")) == origin_id
            for key in ("causes", "outcomes")
            for p in result.get(key, []) or []
        ):
            continue

        desired_stops = []
        for stop_id in desired_line.get("stops", []) or []:
            mapped_stop = stop_id
            for id_map in placement_maps.values():
                mapped_stop = id_map.get(stop_id, mapped_stop)
            if mapped_stop not in desired_stops:
                desired_stops.append(mapped_stop)

        desired_lines.append({
            **deepcopy(desired_line),
            "originId": mapped_origin,
            "stops": desired_stops,
        })

    desired_origin_ids = {
        str(line.get("originId", ""))
        for line in desired_lines
    }

    existing_lines = [
        line for line in (result.get("lines", []) or [])
        if isinstance(line, dict)
    ]
    reconciled_lines = []

    for line in existing_lines:
        origin = str(line.get("originId", ""))
        if origin in desired_origin_ids:
            continue

        if origin and placement_source_types.get(origin) in _GENERATED_SOURCE_TYPES:
            continue

        # Preserve manual relationship records.
        reconciled_lines.append(deepcopy(line))

    for desired_line in desired_lines:
        existing_line = next(
            (
                line for line in existing_lines
                if str(line.get("originId", "")) == str(desired_line.get("originId", ""))
            ),
            None,
        )

        if existing_line:
            generated_stops = set(
                desired_line.get("stops", []) or []
            )
            manual_stops = [
                stop
                for stop in (existing_line.get("stops", []) or [])
                if placement_source_types.get(str(stop))
                not in _GENERATED_SOURCE_TYPES
            ]
            desired_line["stops"] = []
            for stop in [*manual_stops, *generated_stops]:
                if stop not in desired_line["stops"]:
                    desired_line["stops"].append(stop)

            merged_line = {
                **deepcopy(existing_line),
                **deepcopy(desired_line),
            }
            reconciled_lines.append(merged_line)
        else:
            reconciled_lines.append(deepcopy(desired_line))

    result["lines"] = reconciled_lines

    # Keep the existing browser/editor layout untouched, only extending it for
    # genuinely new source-derived placements. Drop stale entries for nodes
    # that are no longer present so a later node cannot inherit old geometry.
    active_layout_ids = {
        str(placement.get("id", ""))
        for placement_key in (
            "causes",
            "preventativeBarriers",
            "mitigativeBarriers",
            "outcomes",
        )
        for placement in result.get(placement_key, []) or []
        if placement.get("id")
    }
    result["layout"] = {
        str(pid): deepcopy(value)
        for pid, value in (result.get("layout", {}) or {}).items()
        if str(pid) in active_layout_ids
    }
    for placement_key in (
        "causes",
        "preventativeBarriers",
        "mitigativeBarriers",
        "outcomes",
    ):
        for placement in result.get(placement_key, []) or []:
            pid = str(placement.get("id", ""))
            result["layout"].setdefault(pid, {
                "x": placement.get("x", 0),
                "y": placement.get("y", 0),
                "w": placement.get("w", 0),
                "h": placement.get("h", 0),
            })

    result["layout_version"] = 2
    return result


def ensure_bowtie_register(
    risk_rows: list[dict[str, Any]],
    *,
    current: dict[str, Any] | None,
    uncertainties: list[dict[str, Any]],
    resolution_list: dict[str, Any],
    resolution_planner: list[dict[str, Any]],
) -> dict[str, Any]:
    """Ensure every current risk has a Bowtie reconciled to Risk Register data."""
    current_register = deepcopy(current or {})
    result: dict[str, Any] = {}

    for row in risk_rows:
        risk_id = str(row.get("risk_id", "")).strip()
        if not risk_id:
            continue

        existing = current_register.get(risk_id)
        if existing:
            current_signature = _source_signature(
                row,
                resolution_planner,
            )
            if existing.get("source_signature") == current_signature:
                # No upstream form data changed. Preserve the current Bowtie
                # exactly; this is critical after Auto Layout or manual edits.
                result[risk_id] = existing
            else:
                result[risk_id] = reconcile_bowtie_document(
                    existing,
                    row,
                    uncertainties=uncertainties,
                    resolution_list=resolution_list,
                    resolution_planner=resolution_planner,
                )
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
    current: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Synchronise a Risk Register row into Bowtie, preserving manual edits."""
    if current:
        return reconcile_bowtie_document(
            current,
            risk_row,
            uncertainties=uncertainties,
            resolution_list=resolution_list,
            resolution_planner=resolution_planner,
        )
    return build_bowtie_document(
        risk_row,
        uncertainties=uncertainties,
        resolution_list=resolution_list,
        resolution_planner=resolution_planner,
    )
