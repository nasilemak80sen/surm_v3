"""
utils/charts.py
All Plotly chart builders — redesigned for clarity and proper bowtie shape.
Returns fig objects ready for st.plotly_chart().
"""
import plotly.graph_objects as go
import pandas as pd

FONT_FAMILY = "Calibri, Arial, sans-serif"

RATING_COLOR = {
    "HH": "#C00000", "HM": "#FF4500", "HL": "#FFA500",
    "MH": "#FF8C00", "MM": "#FFD700", "ML": "#92D050",
    "LH": "#FFA500", "LM": "#92D050", "LL": "#00B050",
}

CELL_FILL = {
    (1,3): "#fde68a", (2,3): "#fdba74", (3,3): "#fca5a5",
    (1,2): "#bbf7d0", (2,2): "#fef9c3", (3,2): "#fdba74",
    (1,1): "#86efac", (2,1): "#bbf7d0", (3,1): "#fde68a",
}

DEG_MAP    = {"H": 3, "M": 2, "L": 1}
IMPACT_MAP = {"H": 3, "M": 2, "L": 1}


def build_uncertainty_matrix(key_unc_df: pd.DataFrame) -> go.Figure:
    """Build a clean 3x3 uncertainty/impact matrix with numbered markers.

    Long uncertainty names intentionally stay out of the matrix cells. Each
    marker maps to the numbered detail table rendered below the chart.
    """
    fig = go.Figure()

    degree_labels = ["L", "M", "H"]
    impact_labels = ["L", "M", "H"]

    for deg_i, deg_label in enumerate(degree_labels, 1):
        for imp_i, imp_label in enumerate(impact_labels, 1):
            x0, x1 = deg_i - 0.5, deg_i + 0.5
            y0, y1 = imp_i - 0.5, imp_i + 0.5
            color = CELL_FILL.get((deg_i, imp_i), "#EEF2EF")

            fig.add_shape(
                type="rect",
                x0=x0,
                y0=y0,
                x1=x1,
                y1=y1,
                fillcolor=color,
                line=dict(color="white", width=2),
                layer="below",
            )

            rating = f"{deg_label}{imp_label}"
            fig.add_annotation(
                x=x0 + 0.07,
                y=y1 - 0.07,
                text=f"<b>{rating}</b>",
                showarrow=False,
                xanchor="left",
                yanchor="top",
                font=dict(
                    size=12,
                    color="rgba(23,32,27,0.52)",
                    family=FONT_FAMILY,
                ),
            )

    if not key_unc_df.empty:
        from collections import defaultdict
        import html

        positions: dict[tuple[int, int], int] = defaultdict(int)
        x_values = []
        y_values = []
        marker_text = []
        marker_colors = []
        hover_text = []

        for index, (_, row) in enumerate(key_unc_df.iterrows(), start=1):
            marker_number = str(row.get("Matrix #", index))
            degree = str(row.get("Degree of Uncertainty", "L") or "L")
            impact = str(row.get("Impact Bin", "L") or "L")
            x_base = {"L": 1, "M": 2, "H": 3}.get(degree, 1)
            y_base = {"L": 1, "M": 2, "H": 3}.get(impact, 1)

            cell_index = positions[(x_base, y_base)]
            positions[(x_base, y_base)] += 1

            # Arrange crowded cells as a compact 3-column mini-grid.
            col = cell_index % 3
            row_offset = cell_index // 3
            x_offset = (col - 1) * 0.25
            y_offset = (1 - row_offset) * 0.25

            x_values.append(x_base + x_offset)
            y_values.append(y_base + y_offset)
            marker_text.append(marker_number)
            rating = str(row.get("Combined Rating", "") or "")
            marker_colors.append(RATING_COLOR.get(rating, "#176B3A"))

            label = html.escape(str(row.get("Uncertainty", "") or "Uncertainty"))
            hover_text.append(
                f"<b>#{marker_number} — {label}</b>"
                f"<br>Degree: {html.escape(degree)}"
                f"<br>Impact: {html.escape(impact)}"
                f"<br>Rating: <b>{html.escape(rating)}</b>"
                f"<br>Weighted score: {float(row.get('Impact (Weighted)', 0) or 0):.3f}"
            )

        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=y_values,
                mode="markers+text",
                text=marker_text,
                textposition="middle center",
                textfont=dict(
                    size=15,
                    color="white",
                    family=FONT_FAMILY,
                ),
                marker=dict(
                    size=38,
                    color=marker_colors,
                    line=dict(color="white", width=3),
                    symbol="circle",
                ),
                hovertemplate=hover_text,
                hoverlabel=dict(
                    bgcolor="white",
                    bordercolor="#C7D3CC",
                    font=dict(size=13, family=FONT_FAMILY, color="#17201B"),
                ),
                showlegend=False,
            )
        )

    fig.update_layout(
        title=dict(
            text="Uncertainty Matrix",
            font=dict(size=22, color="#176B3A", family=FONT_FAMILY),
            x=0.5,
            xanchor="center",
        ),
        xaxis=dict(
            title=dict(
                text="<b>Degree of Uncertainty</b>",
                font=dict(size=17, family=FONT_FAMILY),
                standoff=16,
            ),
            tickvals=[1, 2, 3],
            ticktext=["Low", "Medium", "High"],
            tickfont=dict(size=15, family=FONT_FAMILY),
            range=[0.35, 3.65],
            showgrid=False,
            zeroline=False,
            linecolor="#97A49D",
            linewidth=1.5,
            fixedrange=True,
        ),
        yaxis=dict(
            title=dict(
                text="<b>Impact on Key Decisions</b>",
                font=dict(size=17, family=FONT_FAMILY),
                standoff=18,
            ),
            tickvals=[1, 2, 3],
            ticktext=["Low", "Medium", "High"],
            tickfont=dict(size=15, family=FONT_FAMILY),
            range=[0.35, 3.65],
            showgrid=False,
            zeroline=False,
            linecolor="#97A49D",
            linewidth=1.5,
            fixedrange=True,
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=700,
        margin=dict(l=105, r=45, t=90, b=105),
        font=dict(family=FONT_FAMILY, size=14),
        hoverlabel=dict(font_size=13, font_family=FONT_FAMILY),
    )
    return fig

def build_tornado_chart(key_unc_df: pd.DataFrame) -> go.Figure:
    if key_unc_df.empty:
        return go.Figure()

    df = key_unc_df.sort_values("Impact (Weighted)", ascending=True).copy()
    colors = [RATING_COLOR.get(r, "#1F6B3A") for r in df["Combined Rating"]]
    df["Short Name"] = df["Uncertainty"].apply(
        lambda x: x[:55] + "…" if len(x) > 57 else x)

    fig = go.Figure(go.Bar(
        x=df["Impact (Weighted)"],
        y=df["Short Name"],
        orientation="h",
        marker=dict(color=colors, line=dict(color="white", width=0.5)),
        text=df["Combined Rating"],
        textposition="outside",
        textfont=dict(size=12, color="#1A1A1A", family=FONT_FAMILY),
        hovertemplate="<b>%{y}</b><br>Score: %{x:.3f}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="Tornado Chart — Impact on Key Decisions (Weighted)",
                   font=dict(size=17, color="#1F6B3A", family=FONT_FAMILY), x=0.5),
        xaxis=dict(title=dict(text="Weighted Score",
                              font=dict(size=14, family=FONT_FAMILY)),
                   range=[0.6, 3.4], gridcolor="#E0E0E0",
                   tickfont=dict(size=12, family=FONT_FAMILY), dtick=0.4),
        yaxis=dict(title="", automargin=True,
                   tickfont=dict(size=12, family=FONT_FAMILY)),
        plot_bgcolor="white", paper_bgcolor="white",
        height=max(420, len(df) * 42 + 120),
        margin=dict(l=220, r=90, t=90, b=60),
        font=dict(family=FONT_FAMILY, size=13),
    )
    fig.update_yaxes(tickfont=dict(size=12), automargin=True)
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="#ECECEC")
    return fig


def _wrap_label(value: object, width: int = 20, max_lines: int = 3) -> str:
    """Wrap diagram labels while preserving complete words."""
    import html
    import textwrap

    text = html.escape(str(value or "").strip())
    if not text:
        return ""

    lines = textwrap.wrap(
        text,
        width=width,
        break_long_words=False,
        break_on_hyphens=False,
    )
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .") + "…"
    return "<br>".join(lines)


def _split_diagram_items(value: object, limit: int = 5) -> list[str]:
    import re

    raw = str(value or "")
    items = [
        item.strip().lstrip("0123456789. -•")
        for item in re.split(r"[\n;]+", raw)
        if item.strip()
    ]
    return items[:limit]


def _add_lane_card(
    fig: go.Figure,
    *,
    x_center: float,
    y_center: float,
    width: float,
    height: float,
    text: str,
    fill: str,
    line: str,
    font_color: str,
    font_size: int = 14,
) -> None:
    fig.add_shape(
        type="rect",
        x0=x_center - width / 2,
        x1=x_center + width / 2,
        y0=y_center - height / 2,
        y1=y_center + height / 2,
        fillcolor=fill,
        line=dict(color=line, width=1.5),
        layer="above",
    )
    fig.add_annotation(
        x=x_center,
        y=y_center,
        text=text,
        showarrow=False,
        xanchor="center",
        yanchor="middle",
        align="center",
        font=dict(
            size=font_size,
            color=font_color,
            family=FONT_FAMILY,
        ),
    )


def build_bowtie(risk_row: dict) -> go.Figure:
    """Build a structured, five-lane Bowtie that prioritises readability."""
    risk_name = str(risk_row.get("Risk", "Risk Event") or "Risk Event")
    causes = _split_diagram_items(risk_row.get("Uncertainty/Causes"), limit=5)
    controls = _split_diagram_items(risk_row.get("Resolution Plan"), limit=5)
    recovery = _split_diagram_items(risk_row.get("Contingency Plan"), limit=5)
    consequences = _split_diagram_items(
        risk_row.get("Impact/Consequence"),
        limit=5,
    )

    if not causes:
        causes = ["No threats listed"]
    if not controls:
        controls = ["No preventive barrier listed"]
    if not recovery:
        recovery = ["No mitigative barrier listed"]
    if not consequences:
        consequences = ["No consequence listed"]

    lane_x = {
        "threats": 1.5,
        "prevention": 4.5,
        "event": 7.5,
        "mitigation": 10.5,
        "consequences": 13.5,
    }
    lane_width = 2.35
    card_height = 1.0
    row_gap = 0.28
    max_items = max(
        len(causes),
        len(controls),
        len(recovery),
        len(consequences),
        1,
    )

    y_values = [
        0.9 + index * (card_height + row_gap)
        for index in range(max_items)
    ]
    y_mid = sum(y_values) / len(y_values)
    top_y = max(y_values) + 1.0
    bottom_y = 0.2

    fig = go.Figure()

    # Soft lane backgrounds keep the Bowtie visually organised without
    # forcing every relationship into a crossing arrow.
    lane_specs = [
        ("Threats", lane_x["threats"], "#FFF7E8", "#D9A441", "#6B4A12"),
        ("Preventive Barriers", lane_x["prevention"], "#ECF9F2", "#1D9E75", "#0F6E56"),
        ("Top Event", lane_x["event"], "#FDEEEE", "#C00000", "#8A0000"),
        ("Mitigative Barriers", lane_x["mitigation"], "#F2F0FB", "#534AB7", "#3C3489"),
        ("Consequences", lane_x["consequences"], "#FFF1EC", "#B95A36", "#6B2D1C"),
    ]

    for title, x, bg, border, text_color in lane_specs:
        fig.add_shape(
            type="rect",
            x0=x - lane_width / 2 - 0.08,
            x1=x + lane_width / 2 + 0.08,
            y0=bottom_y,
            y1=top_y,
            fillcolor=bg,
            line=dict(color=border, width=1),
            layer="below",
        )
        fig.add_annotation(
            x=x,
            y=top_y + 0.48,
            text=f"<b>{title}</b>",
            showarrow=False,
            xanchor="center",
            font=dict(size=15, color=text_color, family=FONT_FAMILY),
        )

    # Directional arrows between lanes. They communicate Bowtie flow without
    # drawing one line for every threat, barrier and consequence.
    for x1, x2 in [
        (lane_x["threats"] + lane_width / 2 + 0.15, lane_x["prevention"] - lane_width / 2 - 0.15),
        (lane_x["prevention"] + lane_width / 2 + 0.15, lane_x["event"] - lane_width / 2 - 0.15),
        (lane_x["event"] + lane_width / 2 + 0.15, lane_x["mitigation"] - lane_width / 2 - 0.15),
        (lane_x["mitigation"] + lane_width / 2 + 0.15, lane_x["consequences"] - lane_width / 2 - 0.15),
    ]:
        fig.add_annotation(
            x=(x1 + x2) / 2,
            y=y_mid,
            ax=x1,
            ay=y_mid,
            axref="x",
            ayref="y",
            xref="x",
            yref="y",
            arrowhead=2,
            arrowsize=1.2,
            arrowwidth=2.3,
            arrowcolor="#88958E",
            showarrow=True,
        )

    lane_cards = [
        (
            lane_x["threats"],
            causes,
            "#FFF7E8",
            "#D9A441",
            "#412402",
        ),
        (
            lane_x["prevention"],
            controls,
            "#EAF8F0",
            "#1D9E75",
            "#0F6E56",
        ),
        (
            lane_x["mitigation"],
            recovery,
            "#F3F0FB",
            "#534AB7",
            "#3C3489",
        ),
        (
            lane_x["consequences"],
            consequences,
            "#FFF1EC",
            "#B95A36",
            "#5B2617",
        ),
    ]

    for x, items, fill, border, font_color in lane_cards:
        start_y = y_mid + ((len(items) - 1) * (card_height + row_gap)) / 2
        for index, item in enumerate(items):
            y = start_y - index * (card_height + row_gap)
            _add_lane_card(
                fig,
                x_center=x,
                y_center=y,
                width=lane_width,
                height=card_height,
                text=_wrap_label(item, width=20, max_lines=3),
                fill=fill,
                line=border,
                font_color=font_color,
                font_size=14,
            )

    # The event gets a larger, uncluttered center block.
    event_height = 2.35
    _add_lane_card(
        fig,
        x_center=lane_x["event"],
        y_center=y_mid,
        width=2.5,
        height=event_height,
        text=(
            "<b>TOP EVENT</b><br><br>"
            f"{_wrap_label(risk_name, width=22, max_lines=3)}"
        ),
        fill="#C00000",
        line="#8A0000",
        font_color="white",
        font_size=17,
    )

    fig.add_annotation(
        x=lane_x["prevention"],
        y=bottom_y - 0.08,
        text="Prevent uncertainty from reaching the event",
        showarrow=False,
        xanchor="center",
        yanchor="top",
        font=dict(size=11, color="#5A6A61", family=FONT_FAMILY),
    )
    fig.add_annotation(
        x=lane_x["mitigation"],
        y=bottom_y - 0.08,
        text="Reduce consequence after the event",
        showarrow=False,
        xanchor="center",
        yanchor="top",
        font=dict(size=11, color="#5A6A61", family=FONT_FAMILY),
    )

    fig.update_layout(
        title=dict(
            text=f"Bowtie Analysis — {risk_name}",
            font=dict(size=22, color="#176B3A", family=FONT_FAMILY),
            x=0.5,
            xanchor="center",
        ),
        xaxis=dict(
            visible=False,
            range=[0.0, 15.0],
            fixedrange=True,
        ),
        yaxis=dict(
            visible=False,
            range=[-0.75, top_y + 1.05],
            fixedrange=True,
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=max(760, 220 + max_items * 125),
        margin=dict(l=24, r=24, t=96, b=65),
        font=dict(family=FONT_FAMILY, size=14),
        showlegend=False,
    )
    return fig

def _even_spacing(n: int, y_min: float, y_max: float) -> list:
    if n == 1:
        return [(y_min + y_max) / 2]
    step = (y_max - y_min) / (n - 1)
    return [y_min + i * step for i in range(n)]
