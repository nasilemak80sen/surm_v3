"""
utils/export_png.py
Converts Plotly figures to PNG bytes for download buttons.
Requires kaleido: pip install kaleido
"""
import io
import plotly.graph_objects as go

def fig_to_png_bytes(fig: go.Figure, width: int = 1200, height: int = 700, scale: int = 2) -> bytes:
    """
    Renders a Plotly figure to PNG bytes.
    scale=2 gives retina-quality output.
    Returns bytes ready for st.download_button().
    """
    return fig.to_image(format="png", width=width, height=height, scale=scale)
