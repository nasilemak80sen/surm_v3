import pandas as pd

from utils.charts import build_bowtie, build_tornado_chart, build_uncertainty_matrix


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



def test_uncertainty_matrix_export_includes_full_name_panel():
    frame = pd.DataFrame([
        {
            "Matrix #": 1,
            "Uncertainty": "Very long reservoir connectivity uncertainty label",
            "Degree of Uncertainty": "H",
            "Impact Bin": "H",
            "Combined Rating": "HH",
            "Impact (Weighted)": 3.0,
        },
    ])

    figure = build_uncertainty_matrix(frame, show_full_names=True)

    annotations = [str(item.text) for item in figure.layout.annotations if item.text]
    normalized_annotations = [text.replace("<br>", " ") for text in annotations]
    assert any("Very long reservoir connectivity uncertainty label" in text for text in normalized_annotations)
    assert any("Full uncertainty names" in text for text in annotations)
    assert list(figure.layout.xaxis.domain) == [0.0, 0.62]


def test_tornado_export_uses_full_uncertainty_labels():
    frame = pd.DataFrame([
        {
            "Uncertainty": "Very long reservoir connectivity uncertainty label",
            "Combined Rating": "HH",
            "Impact (Weighted)": 3.0,
        },
        {
            "Uncertainty": "Short uncertainty",
            "Combined Rating": "MM",
            "Impact (Weighted)": 2.0,
        },
    ])

    figure = build_tornado_chart(frame, full_labels=True)

    assert "Very long reservoir connectivity uncertainty label" in list(figure.data[0].y)
    assert figure.layout.margin.l == 360
