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


def test_bowtie_register_preserves_existing_diagrams_and_flags_upstream_change():
    row = _risk()
    first = ensure_bowtie_register(
        [row],
        current={},
        uncertainties=[],
        resolution_list={},
        resolution_planner=[],
    )["RSK-001"]

    changed = dict(row)
    changed["Resolution Plan"] = "- Different resolution"

    preserved = ensure_bowtie_register(
        [changed],
        current={"RSK-001": first},
        uncertainties=[],
        resolution_list={},
        resolution_planner=[],
    )["RSK-001"]

    assert preserved["risk_id"] == "RSK-001"
    assert preserved["source_signature"] == first["source_signature"]
    assert preserved["needs_refresh"] is True
