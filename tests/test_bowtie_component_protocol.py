from pathlib import Path


FRONTEND = Path(__file__).resolve().parents[1] / "components" / "bowtie_editor" / "frontend" / "index.html"


def test_streamlit_v1_component_handshake_uses_top_level_protocol_fields():
    source = FRONTEND.read_text(encoding="utf-8")

    assert "function post(type, data)" in source
    assert "Object.assign(" in source
    assert "{isStreamlitMessage:true, type:type}" in source
    assert "post('streamlit:componentReady',{apiVersion:1})" in source
    assert "function ready(height)" in source
    assert "post('streamlit:setFrameHeight',{height:Number(height)||760})" in source

    assert "{isStreamlitMessage:true,type,value}" not in source


def test_component_value_message_keeps_value_at_top_level():
    source = FRONTEND.read_text(encoding="utf-8")

    assert "type:'streamlit:setComponentValue'" in source
    assert "value:{document:clone(doc),revision:doc.editor_revision}" in source


def test_bowtie_frontend_normalizes_saved_placements_and_uses_fixed_viewport():
    source = FRONTEND.read_text(encoding="utf-8")

    assert "function normalizeDocument(raw)" in source
    assert "value.causes.forEach(p=>{" in source
    assert "p.type='cause';" in source

    assert "value.preventativeBarriers.forEach(p=>p.type='preventativeBarrier')" in source
    assert "value.mitigativeBarriers.forEach(p=>p.type='mitigativeBarrier')" in source
    assert "value.outcomes.forEach(p=>{" in source
    assert "p.type='outcome';" in source
    assert "post('streamlit:setFrameHeight',{height:Number(height)||760})" in source
    assert "setTimeout(()=>ready(args.height),0)" in source


def test_bowtie_frontend_accepts_streamlit_render_without_inbound_marker():
    source = FRONTEND.read_text(encoding="utf-8")

    assert "if(data.type!=='streamlit:render')return;" in source
    assert "if(!data.isStreamlitMessage)return;" not in source


def test_bowtie_delete_is_type_safe_and_removes_placement_library_and_lines():
    source = FRONTEND.read_text(encoding="utf-8")

    assert "const buckets=[" in source
    assert "doc[key]=list.filter(p=>p.id!==placement.id);" in source
    assert "doc.library[type]=(doc.library[type]||[]).filter(n=>n.id!==placement.nodeId);" in source
    assert ".filter(line=>line.originId!==placement.id)" in source
    assert "stops:(line.stops||[]).filter(stopId=>stopId!==placement.id)" in source


def test_bowtie_nodes_use_readable_dimensions_and_text_wrapping():
    source = FRONTEND.read_text(encoding="utf-8")

    assert "p.w=120;" in source
    assert "p.h=112;" in source
    assert ".node-text{font-size:14px;font-weight:600;" in source
    assert ".barrier-text{font-size:12px;font-weight:600;" in source
    assert "const lines=textWrap(n?n.name:p.nodeId,15,5);" in source
    assert "const lines=textWrap(text,28,4);" in source
    assert "const legacySize=Number(p.w||0)<80;" in source
