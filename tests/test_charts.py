import pandas as pd

from utils.charts import build_bowtie, build_uncertainty_matrix


def test_uncertainty_matrix_uses_numbered_markers_and_readable_scale():
    frame = pd.DataFrame([
        {
            "Matrix #": 1,
            "Uncertainty": "Very long reservoir connectivity uncertainty label",
            "Degree of Uncertainty": "H",
            "Impact Bin": "H",
            "Combined Rating": "HH",
            "Impact (Weighted)": 3.0,
        },
        {
            "Matrix #": 2,
            "Uncertainty": "Another long fluid distribution uncertainty label",
            "Degree of Uncertainty": "M",
            "Impact Bin": "H",
            "Combined Rating": "MH",
            "Impact (Weighted)": 2.5,
        },
    ])

    figure = build_uncertainty_matrix(frame)

    assert figure.layout.height >= 650
    assert len(figure.data) == 1
    assert list(figure.data[0].text) == ["1", "2"]
    assert figure.data[0].marker.size == 38


def test_bowtie_uses_structured_lanes_and_large_text():
    figure = build_bowtie({
        "Risk": "Very long reservoir performance risk event",
        "Uncertainty/Causes": (
            "Poor reservoir connectivity\n"
            "Uncertain fluid distribution\n"
            "Limited pressure data"
        ),
        "Resolution Plan": (
            "Additional dynamic modelling\n"
            "Pressure data acquisition"
        ),
        "Contingency Plan": "Alternative development strategy",
        "Impact/Consequence": (
            "Production shortfall;Reserve downgrade;Development delay"
        ),
    })

    assert figure.layout.height >= 760
    annotations = list(figure.layout.annotations)
    annotation_text = {str(item.text) for item in annotations if item.text}

    for label in [
        "<b>Threats</b>",
        "<b>Preventive Barriers</b>",
        "<b>Top Event</b>",
        "<b>Mitigative Barriers</b>",
        "<b>Consequences</b>",
    ]:
        assert label in annotation_text

    assert any(
        item.font and item.font.size >= 14
        for item in annotations
        if item.text and "TOP EVENT" in str(item.text)
    )
