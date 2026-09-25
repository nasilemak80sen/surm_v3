from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "components" / "bowtie_editor" / "frontend"
HTML = FRONTEND / "index.html"
JS = FRONTEND / "bowtie_v2.js"


def _source() -> str:
    return HTML.read_text(encoding="utf-8") + "\n" + JS.read_text(encoding="utf-8")


def test_streamlit_v1_component_handshake_uses_top_level_protocol_fields():
    source = _source()

    assert '<script src="bowtie_v2.js"></script>' in source
    assert "function post(type, data)" in source
    assert "Object.assign(" in source
    assert "{isStreamlitMessage:true, type:type}" in source
    assert 'post("streamlit:componentReady", {apiVersion:1})' in source
    assert "function ready(height)" in source
    assert 'post("streamlit:setFrameHeight", {height:Number(height) || 820})' in source

    assert "{isStreamlitMessage:true,type,value}" not in source


def test_component_value_message_keeps_value_at_top_level():
    source = _source()

    assert 'type:"streamlit:setComponentValue"' in source
    assert "value:{document:clone(doc),revision:doc.editor_revision}" in source


def test_bowtie_frontend_v2_locks_semantic_lanes_and_persists_layout():
    source = _source()

    assert "const GRID = 20;" in source
    assert "const LANE_X = {" in source
    assert "value.layout_version = 2;" in source
    assert "function syncLayoutMetadata(target)" in source
    assert 'targetDoc.layout_version = 2;' in source
    assert "function autoArrange()" in source
    assert 'setStatus("Auto layout applied: relationships drive vertical placement")' in source


def test_bowtie_frontend_routes_relationships_as_edges_and_updates_live():
    source = _source()

    assert "function renderConnectors(layer)" in source
    assert "drawnBarrierToEvent" in source
    assert "drawnEventToBarrier" in source
    assert "function refreshConnectorLayer()" in source
    assert 'el.setAttribute("transform", "translate("' in source
    assert 'setStatus("Dragging · lane locked · "' in source


def test_bowtie_frontend_includes_zoom_pan_fit_and_inspector_health():
    source = _source()

    assert "function fitToContent(padding, announce)" in source
    assert "svg.addEventListener(" + '"wheel"' + " in source
    assert "function setZoom(factor, centerX, centerY)" in source
    assert "function renderEditor()" in source
    assert "function renderRelationships()" in source
    assert "function renderHealth()" in source
    assert "function prepareExportSvg()" in source


def test_bowtie_delete_is_type_safe_and_removes_placement_library_and_lines():
    source = _source()

    assert "const type = placement.type;" in source
    assert "doc[key] = doc[key].filter(" in source
    assert "doc.library[type] = (doc.library[type] || []).filter(" in source
    assert ".filter(function (line) { return line.originId !== placement.id; })" in source
    assert "stops: (line.stops || []).filter(function (stopId)" in source
