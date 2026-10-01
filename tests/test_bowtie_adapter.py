import pandas as pd

from utils.bowtie_adapter import (
    BOWTIE_SCHEMA_VERSION,
    build_bowtie_document,
    ensure_bowtie_register,
)


def _risk():
    return {
        "risk_id": "RSK-001",
        "Risk": "Poor reservoir connectivity",
        "Uncertainty/Causes": "1. Reservoir continuity\n2. Fault properties",
        "Resolution Plan": "- Fault Seal Analysis\n- Integrated Reservoir Connectivity Studies",
        "Contingency Plan": "Re-evaluate development strategy",
        "Impact/Consequence": "Production shortfall;Injection underperformance",
    }


def test_bowtie_document_seeds_stable_risk_topology():
    document = build_bowtie_document(
        _risk(),
        uncertainties=[
            {
                "uncertainty_id": "UNC-003",
                "name": "Reservoir continuity",
                "risks": ["Poor reservoir connectivity"],
            },
            {
                "uncertainty_id": "UNC-007",
                "name": "Fault properties",
                "risks": ["Poor reservoir connectivity"],
            },
        ],
        resolution_list={
            "Reservoir continuity": {
                "Fault Seal Analysis": "Y",
                "Integrated Reservoir Connectivity Studies": "Y",
            },
            "Fault properties": {
                "Fault Seal Analysis": "Y",
                "Integrated Reservoir Connectivity Studies": "Y",
            },
        },
        resolution_planner=[
            {
                "resolution_id": "RES-001",
                "Resolution Action": "Fault Seal Analysis",
                "Description": "Assess fault seal behaviour.",
                "Action Owner": "Geology",
            }
        ],
    )

    assert document["version"] == BOWTIE_SCHEMA_VERSION
    assert document["risk_id"] == "RSK-001"
    assert document["layout_version"] == 2
    assert document["layout"]["CAUSE-PLACEMENT-1"]["x"] == 120
    assert len(document["causes"]) == 2
    assert len(document["preventativeBarriers"]) == 2
    assert len(document["outcomes"]) == 2
    assert len(document["mitigativeBarriers"]) == 1

    fault_seal = next(
        node
        for node in document["library"]["preventativeBarrier"]
        if node["name"] == "Fault Seal Analysis"
    )
    assert fault_seal["id"] == "RES-001"

    cause_line = document["lines"][0]
    assert "PREVENTIVE-PLACEMENT-1" in cause_line["stops"]
    assert "PREVENTIVE-PLACEMENT-2" in cause_line["stops"]


def test_bowtie_only_creates_preventive_barriers_from_risk_register_resolution_plan():
    row = _risk()
    row["Resolution Plan"] = "- Fault Seal Analysis"

    document = build_bowtie_document(
        row,
        uncertainties=[
            {"uncertainty_id": "UNC-003", "name": "Reservoir continuity", "risks": ["Poor reservoir connectivity"]},
        ],
        resolution_list={
            "Reservoir continuity": {
                "Fault Seal Analysis": "Y",
                "Integrated Reservoir Connectivity Studies": "Y",
                "Another option": "Y",
            }
        },
        resolution_planner=[
            {"resolution_id": "RES-001", "Resolution Action": "Fault Seal Analysis"},
            {"resolution_id": "RES-002", "Resolution Action": "Integrated Reservoir Connectivity Studies"},
            {"resolution_id": "RES-003", "Resolution Action": "Another option"},
        ],
    )

    names = [
        node["name"]
        for node in document["library"]["preventativeBarrier"]
    ]
    assert names == ["Fault Seal Analysis"]


def test_bowtie_auto_layout_contract_does_not_create_objects():
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]
    source = (
        project_root / "components/bowtie_editor/frontend/bowtie_v2.js"
    ).read_text(encoding="utf-8")

    auto_start = source.index("function autoArrange()")
    auto_end = source.index("  function textWrap(", auto_start)
    auto_layout = source[auto_start:auto_end]

    assert "addObject(" not in auto_layout
    assert "doc.preventativeBarriers.push" not in auto_layout
    assert "doc.mitigativeBarriers.push" not in auto_layout
    assert "doc.causes.push" not in auto_layout
    assert "doc.outcomes.push" not in auto_layout


def test_unchanged_risk_source_does_not_recreate_removed_generated_barrier():
    row = _risk()
    current = ensure_bowtie_register(
        [row],
        current={},
        uncertainties=[
            {"uncertainty_id": "UNC-003", "name": "Reservoir continuity", "risks": ["Poor reservoir connectivity"]},
            {"uncertainty_id": "UNC-007", "name": "Fault properties", "risks": ["Poor reservoir connectivity"]},
        ],
        resolution_list={
            "Reservoir continuity": {"Fault Seal Analysis": "Y", "Integrated Reservoir Connectivity Studies": "Y"},
            "Fault properties": {"Fault Seal Analysis": "Y", "Integrated Reservoir Connectivity Studies": "Y"},
        },
        resolution_planner=[],
    )["RSK-001"]

    removed_placement = current["preventativeBarriers"][0]
    removed_node_id = removed_placement["nodeId"]
    removed_placement_id = removed_placement["id"]
    current["preventativeBarriers"] = [
        item for item in current["preventativeBarriers"]
        if item["id"] != removed_placement_id
    ]
    current["library"]["preventativeBarrier"] = [
        node for node in current["library"]["preventativeBarrier"]
        if node["id"] != removed_node_id
    ]

    preserved = ensure_bowtie_register(
        [row],
        current={"RSK-001": current},
        uncertainties=[],
        resolution_list={},
        resolution_planner=[],
    )["RSK-001"]

    assert removed_placement_id not in {
        item["id"] for item in preserved["preventativeBarriers"]
    }
    assert removed_node_id not in {
        node["id"] for node in preserved["library"]["preventativeBarrier"]
    }

def test_bowtie_register_reconciles_risk_form_changes_without_rebuilding_layout():
    row = _risk()
    first = ensure_bowtie_register(
        [row],
        current={},
        uncertainties=[
            {"uncertainty_id": "UNC-003", "name": "Reservoir continuity", "risks": ["Poor reservoir connectivity"]},
            {"uncertainty_id": "UNC-007", "name": "Fault properties", "risks": ["Poor reservoir connectivity"]},
        ],
        resolution_list={
            "Reservoir continuity": {"Fault Seal Analysis": "Y"},
            "Fault properties": {"Fault Seal Analysis": "Y"},
        },
        resolution_planner=[{
            "resolution_id": "RES-001",
            "Resolution Action": "Fault Seal Analysis",
            "Description": "Assess fault seal behaviour.",
            "Action Owner": "Geology",
        }],
    )["RSK-001"]

    # Simulate a user-created Bowtie object and an intentional manual
    # repositioning of the generated preventive barrier.
    first["library"]["cause"].append({
        "id": "MANUAL-1",
        "type": "cause",
        "name": "Manual Bowtie Threat",
        "description": "",
        "surm_source": {"type": "manual"},
    })
    first["causes"].append({
        "id": "CAUSE-MANUAL-1",
        "nodeId": "MANUAL-1",
        "x": 170,
        "y": 700,
        "w": 240,
        "h": 86,
        "pageId": "PAGE_1",
    })
    first["lines"].append({
        "id": "LINE-MANUAL-1",
        "originType": "cause",
        "originId": "CAUSE-MANUAL-1",
        "stops": [],
        "pageId": "PAGE_1",
    })
    first["preventativeBarriers"][0]["y"] = 620

    changed = dict(row)
    changed["Contingency Plan"] = "Activate emergency pressure surveillance"
    changed["Impact/Consequence"] = "Updated production consequence"

    result = ensure_bowtie_register(
        [changed],
        current={"RSK-001": first},
        uncertainties=[
            {"uncertainty_id": "UNC-003", "name": "Reservoir continuity", "risks": ["Poor reservoir connectivity"]},
            {"uncertainty_id": "UNC-007", "name": "Fault properties", "risks": ["Poor reservoir connectivity"]},
        ],
        resolution_list={
            "Reservoir continuity": {"Fault Seal Analysis": "Y"},
            "Fault properties": {"Fault Seal Analysis": "Y"},
        },
        resolution_planner=[{
            "resolution_id": "RES-001",
            "Resolution Action": "Fault Seal Analysis",
            "Description": "Assess fault seal behaviour.",
            "Action Owner": "Geology",
        }],
    )["RSK-001"]

    assert result["source_signature"] != first["source_signature"]
    assert result.get("needs_refresh") is False
    assert any(
        node["name"] == "Manual Bowtie Threat"
        for node in result["library"]["cause"]
    )
    assert result["preventativeBarriers"][0]["y"] == 620
    assert any(
        node["name"] == "Updated production consequence"
        for node in result["library"]["outcome"]
    )
    assert any(
        node["name"] == "Activate emergency pressure surveillance"
        for node in result["library"]["mitigativeBarrier"]
    )
