from pathlib import Path


FRONTEND = Path(__file__).resolve().parents[1] / "components" / "bowtie_editor" / "frontend" / "index.html"


def test_streamlit_v1_component_handshake_uses_top_level_protocol_fields():
    source = FRONTEND.read_text(encoding="utf-8")

    assert "function post(type, data)" in source
    assert "Object.assign(" in source
    assert "{isStreamlitMessage:true, type:type}" in source
    assert "post('streamlit:componentReady',{apiVersion:1})" in source
    assert "post('streamlit:setFrameHeight',{height:document.documentElement.scrollHeight || 720})" in source
    assert "{isStreamlitMessage:true,type,value}" not in source


def test_component_value_message_keeps_value_at_top_level():
    source = FRONTEND.read_text(encoding="utf-8")

    assert "type:'streamlit:setComponentValue'" in source
    assert "value:{document:clone(doc),revision:doc.editor_revision}" in source
