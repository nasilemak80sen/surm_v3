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
    fig = go.Figure()

    for deg_i, deg_label in enumerate(["L", "M", "H"], 1):
        for imp_i, imp_label in enumerate(["L", "M", "H"], 1):
            x0, x1 = deg_i - 0.5, deg_i + 0.5
            y0, y1 = imp_i - 0.5, imp_i + 0.5
            color = CELL_FILL.get((deg_i, imp_i), "#EEE")
            fig.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1,
                          fillcolor=color, line_width=0, layer="below")
            rating = deg_label + imp_label
            fig.add_annotation(
                x=deg_i, y=imp_i, text=rating, showarrow=False,
                xanchor="center", yanchor="middle",
                font=dict(size=32, color="rgba(0,0,0,0.09)", family=FONT_FAMILY),
            )

    for v in [0.5, 1.5, 2.5, 3.5]:
        fig.add_shape(type="line", x0=v, x1=v, y0=0.5, y1=3.5,
                      line=dict(color="#AAAAAA", width=0.8))
        fig.add_shape(type="line", x0=0.5, x1=3.5, y0=v, y1=v,
                      line=dict(color="#AAAAAA", width=0.8))

    if not key_unc_df.empty:
        from collections import defaultdict
        pos_count = defaultdict(int)
        for _, r in key_unc_df.iterrows():
            deg    = r.get("Degree of Uncertainty", "L")
            imp    = r.get("Impact Bin", "L")
            x_base = DEG_MAP.get(deg, 1)
            y_base = IMPACT_MAP.get(imp, 1)
            key    = (x_base, y_base)
            offset = pos_count[key]
            pos_count[key] += 1
            jx = [0, 0.20, -0.20,  0.20, -0.20][min(offset, 4)]
            jy = [0, 0.20,  0.20, -0.20, -0.20][min(offset, 4)]
            x      = x_base + jx
            y      = y_base + jy
            rating = r.get("Combined Rating", "LL")
            color  = RATING_COLOR.get(rating, "#888")
            label  = str(r["Uncertainty"])
            short  = label[:30] + "…" if len(label) > 32 else label

            fig.add_trace(go.Scatter(
                x=[x], y=[y], mode="markers+text",
                marker=dict(size=28, color="white",
                            line=dict(color=color, width=3), symbol="circle"),
                text=[short], textposition="bottom center",
                textfont=dict(size=11, color=color, family=FONT_FAMILY),
                name=label,
                hovertemplate=(
                    f"<b>{label}</b><br>Degree: {deg}  |  Impact: {imp}<br>"
                    f"Rating: <b>{rating}</b><extra></extra>"
                ),
                showlegend=False,
            ))

    zone_labels = [
        (0.78, 3.25, "HIGH RISK",   "#C00000"),
        (2.0,  2.0,  "MEDIUM RISK", "#FF8C00"),
        (1.22, 0.75, "LOW RISK",    "#00B050"),
    ]
    for xp, yp, text, color in zone_labels:
        fig.add_annotation(
            x=xp, y=yp, text=text, showarrow=False, xanchor="center",
            font=dict(size=10, color=color, family=FONT_FAMILY), opacity=0.45,
        )

    fig.update_layout(
        title=dict(text="Uncertainty Matrix",
                   font=dict(size=18, color="#1F6B3A", family=FONT_FAMILY), x=0.5),
        xaxis=dict(
            title=dict(text="Degree of Uncertainty",
                       font=dict(size=14, family=FONT_FAMILY)),
            tickvals=[1, 2, 3], ticktext=["Low", "Medium", "High"],
            tickfont=dict(size=13, family=FONT_FAMILY),
            range=[0.3, 3.7], showgrid=False, zeroline=False,
            linecolor="#AAAAAA", linewidth=1,
        ),
        yaxis=dict(
            title=dict(text="Impact on Key Decisions",
                       font=dict(size=14, family=FONT_FAMILY)),
            tickvals=[1, 2, 3], ticktext=["Low", "Medium", "High"],
            tickfont=dict(size=13, family=FONT_FAMILY),
            range=[0.3, 3.7], showgrid=False, zeroline=False,
            linecolor="#AAAAAA", linewidth=1,
        ),
        plot_bgcolor="white", paper_bgcolor="white",
        height=560,
        margin=dict(l=90, r=60, t=90, b=90),
        font=dict(family=FONT_FAMILY, size=13),
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


def build_bowtie(risk_row: dict) -> go.Figure:
    risk_name    = risk_row.get("Risk", "Risk Event")
    causes_raw   = risk_row.get("Uncertainty/Causes", "")
    controls_raw = risk_row.get("Resolution Plan", "")
    contingency  = risk_row.get("Contingency Plan", "")
    consequence  = risk_row.get("Impact/Consequence", "")

    causes    = [c.strip().lstrip("0123456789. ") for c in causes_raw.split("\n") if c.strip()][:7]
    ctrl_list = [c.strip().lstrip("- ") for c in controls_raw.split("\n") if c.strip()][:5]
    cons_list = [c.strip() for c in consequence.split(";") if c.strip()] if consequence else []
    if not cons_list:
        cons_list = ["Impact not yet defined"]
    cons_list = cons_list[:5]
    if not causes:
        causes = ["(no causes listed)"]

    EVENT_CX     = 7.0
    EVENT_CY     = 5.0
    EVENT_LEFT   = 4.6
    EVENT_RIGHT  = 9.4
    EVENT_HALF_H = 1.1
    THREAT_X     = 2.2
    CONS_X       = 11.8
    BOX_W        = 2.05
    BOX_H        = 0.76
    BAR_L        = 3.4
    BAR_R        = 10.6

    n_c = max(len(causes), 1)
    n_k = max(len(cons_list), 1)
    cause_ys = _even_spacing(n_c, 0.6, 9.4)
    cons_ys  = _even_spacing(n_k, 0.6, 9.4)
    tl_top   = min(cause_ys) - BOX_H
    tl_bot   = max(cause_ys) + BOX_H
    tr_top   = min(cons_ys)  - BOX_H
    tr_bot   = max(cons_ys)  + BOX_H

    fig = go.Figure()

    # Triangle fills
    fig.add_trace(go.Scatter(
        x=[THREAT_X, EVENT_LEFT, THREAT_X, THREAT_X],
        y=[tl_top, EVENT_CY, tl_bot, tl_top],
        fill="toself", fillcolor="rgba(250,206,100,0.18)",
        line=dict(width=0), hoverinfo="skip", showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=[EVENT_RIGHT, CONS_X, CONS_X, EVENT_RIGHT],
        y=[EVENT_CY, tr_top, tr_bot, EVENT_CY],
        fill="toself", fillcolor="rgba(200,60,60,0.10)",
        line=dict(width=0), hoverinfo="skip", showlegend=False,
    ))

    # Threat → event arrows
    for y in cause_ys:
        fig.add_annotation(
            x=EVENT_LEFT + 0.06, y=EVENT_CY,
            ax=THREAT_X, ay=y,
            axref="x", ayref="y", xref="x", yref="y",
            arrowhead=2, arrowsize=1.2, arrowwidth=2.2,
            arrowcolor="#BA7517", showarrow=True,
        )

    # Event → consequence arrows
    for y in cons_ys:
        fig.add_annotation(
            x=CONS_X - 0.06, y=y,
            ax=EVENT_RIGHT, ay=EVENT_CY,
            axref="x", ayref="y", xref="x", yref="y",
            arrowhead=2, arrowsize=1.2, arrowwidth=2.2,
            arrowcolor="#993C1D", showarrow=True,
        )

    # Control barrier (teal pillar)
    fig.add_shape(type="rect",
        x0=BAR_L - 0.15, x1=BAR_L + 0.15,
        y0=tl_top - 0.4,  y1=tl_bot + 0.4,
        fillcolor="#1D9E75", line=dict(width=0), layer="above",
    )
    fig.add_annotation(x=BAR_L, y=tl_top - 0.75, text="<b>Controls</b>",
        showarrow=False, xanchor="center",
        font=dict(size=12, color="#0F6E56", family=FONT_FAMILY))

    # Recovery barrier (purple pillar)
    fig.add_shape(type="rect",
        x0=BAR_R - 0.15, x1=BAR_R + 0.15,
        y0=tr_top - 0.4,  y1=tr_bot + 0.4,
        fillcolor="#534AB7", line=dict(width=0), layer="above",
    )
    fig.add_annotation(x=BAR_R, y=tr_top - 0.75, text="<b>Recovery</b>",
        showarrow=False, xanchor="center",
        font=dict(size=12, color="#3C3489", family=FONT_FAMILY))

    # Threat boxes
    for cause, y in zip(causes, cause_ys):
        label = cause[:38] + "…" if len(cause) > 40 else cause
        fig.add_shape(type="rect",
            x0=0.1, x1=THREAT_X - 0.06,
            y0=y - BOX_H / 2, y1=y + BOX_H / 2,
            fillcolor="#FAEEDA", line=dict(color="#BA7517", width=0.8),
        )
        fig.add_annotation(
            x=(0.1 + THREAT_X - 0.06) / 2, y=y,
            text=label, showarrow=False, xanchor="center", yanchor="middle",
            font=dict(size=11, color="#412402", family=FONT_FAMILY),
        )

    # Central event box
    fig.add_shape(type="rect",
        x0=EVENT_LEFT, x1=EVENT_RIGHT,
        y0=EVENT_CY - EVENT_HALF_H, y1=EVENT_CY + EVENT_HALF_H,
        fillcolor="#C00000", line=dict(color="#800000", width=2),
    )
    risk_short = risk_name[:26] + "…" if len(risk_name) > 28 else risk_name
    fig.add_annotation(x=EVENT_CX, y=EVENT_CY + 0.3,
        text=f"<b>{risk_short}</b>", showarrow=False,
        xanchor="center", yanchor="middle",
        font=dict(size=13, color="white", family=FONT_FAMILY))
    fig.add_annotation(x=EVENT_CX, y=EVENT_CY - 0.4,
        text="Risk Event", showarrow=False,
        xanchor="center", yanchor="middle",
        font=dict(size=10, color="rgba(255,200,200,0.9)", family=FONT_FAMILY))

    # Consequence boxes
    for cons, y in zip(cons_list, cons_ys):
        label = cons[:38] + "…" if len(cons) > 40 else cons
        fig.add_shape(type="rect",
            x0=CONS_X + 0.06, x1=13.9,
            y0=y - BOX_H / 2, y1=y + BOX_H / 2,
            fillcolor="#FAECE7", line=dict(color="#993C1D", width=0.8),
        )
        fig.add_annotation(
            x=(CONS_X + 0.06 + 13.9) / 2, y=y,
            text=label, showarrow=False, xanchor="center", yanchor="middle",
            font=dict(size=11, color="#4A1B0C", family=FONT_FAMILY),
        )

    # Controls list below left barrier
    if ctrl_list:
        ctrl_text = "<br>".join("• " + c[:38] for c in ctrl_list[:4])
        fig.add_annotation(x=BAR_L, y=tl_bot + 0.6, text=ctrl_text,
            showarrow=False, xanchor="center", yanchor="top",
            font=dict(size=10, color="#0F6E56", family=FONT_FAMILY),
            bgcolor="rgba(200,245,220,0.85)", bordercolor="#1D9E75",
            borderwidth=1, borderpad=4)

    # Contingency below right barrier
    if contingency:
        fig.add_annotation(x=BAR_R, y=tr_bot + 0.6,
            text="Contingency:<br>" + contingency[:55],
            showarrow=False, xanchor="center", yanchor="top",
            font=dict(size=10, color="#3C3489", family=FONT_FAMILY),
            bgcolor="rgba(220,215,245,0.85)", bordercolor="#534AB7",
            borderwidth=1, borderpad=4)

    # Section labels
    fig.add_annotation(x=1.15, y=10.5, text="<b>Threats / Causes</b>",
        showarrow=False, xanchor="center",
        font=dict(size=13, color="#BA7517", family=FONT_FAMILY))
    fig.add_annotation(x=12.85, y=10.5, text="<b>Consequences</b>",
        showarrow=False, xanchor="center",
        font=dict(size=13, color="#993C1D", family=FONT_FAMILY))

    height = max(520, max(n_c, n_k) * 100 + 220)
    fig.update_layout(
        title=dict(text=f"Bowtie Diagram — {risk_name}",
                   font=dict(size=15, color="#1F6B3A", family=FONT_FAMILY), x=0.5),
        xaxis=dict(visible=False, range=[-0.3, 14.3]),
        yaxis=dict(visible=False, range=[-1.5, 11.5]),
        plot_bgcolor="white", paper_bgcolor="white",
        height=height,
        margin=dict(l=20, r=20, t=70, b=40),
        font=dict(family=FONT_FAMILY, size=13),
        showlegend=False,
    )
    return fig


def _even_spacing(n: int, y_min: float, y_max: float) -> list:
    if n == 1:
        return [(y_min + y_max) / 2]
    step = (y_max - y_min) / (n - 1)
    return [y_min + i * step for i in range(n)]
