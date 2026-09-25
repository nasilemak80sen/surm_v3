from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from playwright.sync_api import expect, sync_playwright


pytestmark = pytest.mark.browser


FRONTEND = (
    Path(__file__).resolve().parents[1]
    / "components"
    / "bowtie_editor"
    / "frontend"
    / "index.html"
)


def _serve_frontend():
    handler = partial(
        SimpleHTTPRequestHandler,
        directory=str(FRONTEND.parent),
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _fixture_document() -> dict:
    return {
        "name": "Browser Regression Risk",
        "risk_id": "RSK-001",
        "editor_revision": 0,
        "layout_version": 2,
        "pages": [{"topLevelEvent": {"name": "Loss of containment"}}],
        "causes": [
            {
                "id": "CAUSE-PLACEMENT-1",
                "nodeId": "C1",
                "x": 170,
                "y": 180,
                "w": 240,
                "h": 86,
                "pageId": "PAGE_1",
            },
            {
                "id": "CAUSE-PLACEMENT-2",
                "nodeId": "C2",
                "x": 170,
                "y": 360,
                "w": 240,
                "h": 86,
                "pageId": "PAGE_1",
            },
        ],
        "preventativeBarriers": [
            {
                "id": "PREVENTIVE-PLACEMENT-1",
                "nodeId": "PB1",
                "x": 500,
                "y": 270,
                "w": 150,
                "h": 110,
                "pageId": "PAGE_1",
            }
        ],
        "mitigativeBarriers": [
            {
                "id": "MITIGATIVE-PLACEMENT-1",
                "nodeId": "MB1",
                "x": 1100,
                "y": 270,
                "w": 150,
                "h": 110,
                "pageId": "PAGE_1",
            }
        ],
        "outcomes": [
            {
                "id": "OUTCOME-PLACEMENT-1",
                "nodeId": "O1",
                "x": 1430,
                "y": 180,
                "w": 240,
                "h": 86,
                "pageId": "PAGE_1",
            },
            {
                "id": "OUTCOME-PLACEMENT-2",
                "nodeId": "O2",
                "x": 1430,
                "y": 360,
                "w": 240,
                "h": 86,
                "pageId": "PAGE_1",
            },
        ],
        "lines": [
            {
                "id": "LINE-CAUSE-1",
                "originType": "cause",
                "originId": "CAUSE-PLACEMENT-1",
                "stops": ["PREVENTIVE-PLACEMENT-1"],
                "pageId": "PAGE_1",
            },
            {
                "id": "LINE-CAUSE-2",
                "originType": "cause",
                "originId": "CAUSE-PLACEMENT-2",
                "stops": ["PREVENTIVE-PLACEMENT-1"],
                "pageId": "PAGE_1",
            },
            {
                "id": "LINE-OUTCOME-1",
                "originType": "outcome",
                "originId": "OUTCOME-PLACEMENT-1",
                "stops": ["MITIGATIVE-PLACEMENT-1"],
                "pageId": "PAGE_1",
            },
            {
                "id": "LINE-OUTCOME-2",
                "originType": "outcome",
                "originId": "OUTCOME-PLACEMENT-2",
                "stops": ["MITIGATIVE-PLACEMENT-1"],
                "pageId": "PAGE_1",
            },
        ],
        "library": {
            "cause": [
                {
                    "id": "C1",
                    "type": "cause",
                    "name": "Existing Threat",
                    "description": "",
                    "surm_source": {"type": "fixture"},
                },
                {
                    "id": "C2",
                    "type": "cause",
                    "name": "Second Threat",
                    "description": "",
                    "surm_source": {"type": "fixture"},
                },
            ],
            "preventativeBarrier": [
                {
                    "id": "PB1",
                    "type": "preventativeBarrier",
                    "name": "Preventive Barrier",
                    "description": "",
                    "owner": "Engineer",
                    "effectiveness": "medium",
                    "degradation_factors": [],
                    "controls": [],
                    "surm_source": {"type": "fixture"},
                }
            ],
            "mitigativeBarrier": [
                {
                    "id": "MB1",
                    "type": "mitigativeBarrier",
                    "name": "Mitigative Barrier",
                    "description": "",
                    "owner": "Engineer",
                    "effectiveness": "medium",
                    "degradation_factors": [],
                    "controls": [],
                    "surm_source": {"type": "fixture"},
                }
            ],
            "outcome": [
                {
                    "id": "O1",
                    "type": "outcome",
                    "name": "Existing Consequence",
                    "description": "",
                    "surm_source": {"type": "fixture"},
                },
                {
                    "id": "O2",
                    "type": "outcome",
                    "name": "Second Consequence",
                    "description": "",
                    "surm_source": {"type": "fixture"},
                },
            ],
        },
    }


def test_bowtie_v2_browser_layout_interaction_and_round_trip():
    server, thread = _serve_frontend()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(accept_downloads=True)
            page_errors = []
            page.on("pageerror", lambda exc: page_errors.append(str(exc)))
            page.add_init_script(
                """window.__surmScriptErrors = [];
window.addEventListener("error", event => {
  window.__surmScriptErrors.push({
    message: event.message,
    filename: event.filename,
    line: event.lineno,
    column: event.colno
  });
});"""
            )

            page.goto(
                f"http://127.0.0.1:{server.server_port}/index.html",
                wait_until="load",
            )
            page.evaluate(
                """
                window.__surmMessages = [];
                window.addEventListener("message", event => {
                    const data = event.data || {};
                    if (data.isStreamlitMessage) {
                        window.__surmMessages.push({
                            type: data.type,
                            value: data.value || null
                        });
                    }
                });
                """
            )

            page.evaluate(
                """payload => {
                    window.dispatchEvent(
                        new MessageEvent("message", {data: payload})
                    );
                }""",
                {
                    "type": "streamlit:render",
                    "args": {
                        "document": _fixture_document(),
                        "editable": True,
                        "height": 820,
                    },
                },
            )

            script_errors = page.evaluate("window.__surmScriptErrors")
            assert not page_errors, {"page_errors": page_errors, "script_errors": script_errors}

            expect(page.locator("#riskInfo")).to_contain_text("RSK-001")
            expect(page.locator("#title")).to_have_text("Browser Regression Risk")
            expect(page.locator("#health")).to_contain_text("2 threats")
            assert page.locator('[data-id="PREVENTIVE-PLACEMENT-1"]').count() == 1
            assert page.locator('[data-id="MITIGATIVE-PLACEMENT-1"]').count() == 1

            messages = page.evaluate("window.__surmMessages")
            assert any(
                item["type"] == "streamlit:componentReady"
                for item in messages
            )
            assert any(
                item["type"] == "streamlit:setFrameHeight"
                for item in messages
            )

            connectors = page.locator('[data-layer="connectors"] .connector')
            assert connectors.count() >= 6
            before_path = connectors.first.get_attribute("d")

            first_cause = page.locator(
                '[data-kind="cause"][data-id="CAUSE-PLACEMENT-1"]'
            )
            box = first_cause.bounding_box()
            assert box is not None

            page.mouse.move(
                box["x"] + box["width"] / 2,
                box["y"] + box["height"] / 2,
            )
            page.mouse.down()
            page.mouse.move(
                box["x"] + box["width"] / 2 + 17,
                box["y"] + box["height"] / 2 + 31,
            )

            during_path = page.locator('[data-layer="connectors"] .connector').first.get_attribute("d")
            assert during_path != before_path

            after_drag_x = float(first_cause.get_attribute("data-x"))
            after_drag_y = float(first_cause.get_attribute("data-y"))
            assert after_drag_x == 170.0
            assert after_drag_y % 20 == 0

            page.mouse.up()
            page.wait_for_timeout(180)
            assert not page_errors, page_errors

            expect(page.locator("#status")).to_contain_text("Position saved")

            page.locator('[data-id="CAUSE-PLACEMENT-1"]').click()
            rel = page.locator(
                '#relationships input[data-rel="PREVENTIVE-PLACEMENT-1"]'
            )
            expect(rel).to_be_checked()
            rel.uncheck()
            page.wait_for_timeout(50)
            assert page.locator('[data-layer="connectors"] .connector').count() >= 5
            rel.check()
            page.wait_for_timeout(50)
            expect(rel).to_be_checked()

            page.locator("#auto").click()
            page.wait_for_timeout(50)
            assert float(
                page.locator(
                    '[data-kind="preventativeBarrier"][data-id="PREVENTIVE-PLACEMENT-1"]'
                ).get_attribute("data-x")
            ) == 500.0

            first_y = float(
                page.locator(
                    '[data-kind="cause"][data-id="CAUSE-PLACEMENT-1"]'
                ).get_attribute("data-y")
            )
            assert first_y % 20 == 0

            before_zoom = page.locator("#svg").get_attribute("viewBox")
            page.locator("#zoomIn").click()
            after_zoom = page.locator("#svg").get_attribute("viewBox")
            assert after_zoom != before_zoom
            page.locator("#zoomReset").click()
            expect(page.locator("#zoomReset")).to_have_text("100%")
            page.locator("#fit").click()
            expect(page.locator("#status")).to_have_text("Fit to content")

            page.evaluate("document.getElementById('addCause').click()")
            page.wait_for_timeout(50)
            expect(page.locator("#objects")).to_contain_text("New Threat")

            new_threat = page.locator("#objects button", has_text="New Threat")
            new_threat.click()
            expect(page.locator("#editName")).to_have_value("New Threat")

            page.locator("#editName").fill("Edited Threat")
            page.locator("#editName").press("Tab")
            page.wait_for_timeout(50)
            assert not page_errors, page_errors
            expect(page.locator("#objects")).to_contain_text("Edited Threat")

            page.wait_for_timeout(250)
            emitted = page.evaluate("window.__surmMessages")
            assert any(
                item["type"] == "streamlit:setComponentValue"
                and item["value"]
                and item["value"]["document"]["layout_version"] == 2
                and item["value"]["document"]["editor_revision"] > 0
                for item in emitted
            )

            undo = page.locator("#undo")
            redo = page.locator("#redo")
            expect(undo).not_to_be_disabled()

            page.evaluate("document.getElementById('undo').click()")
            page.wait_for_timeout(50)
            expect(page.locator("#objects")).to_contain_text("New Threat")
            expect(redo).not_to_be_disabled()

            page.evaluate("document.getElementById('redo').click()")
            page.wait_for_timeout(50)
            expect(page.locator("#objects")).to_contain_text("Edited Threat")

            with page.expect_download(timeout=5000) as download_info:
                page.locator("#exportSvg").click()
            download = download_info.value
            assert download.suggested_filename.endswith("_Bowtie_V2.svg")

            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_bowtie_v2_crud_cycle_preserves_selection_and_relationships():
    server, thread = _serve_frontend()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page_errors = []
            page.on("pageerror", lambda exc: page_errors.append(str(exc)))

            page.goto(
                f"http://127.0.0.1:{server.server_port}/index.html",
                wait_until="load",
            )

            page.evaluate(
                """payload => {
                    window.__surmMessages = [];
                    window.addEventListener("message", event => {
                        const data = event.data || {};
                        if (data.isStreamlitMessage) {
                            window.__surmMessages.push({
                                type: data.type,
                                value: data.value || null
                            });
                        }
                    });
                    window.dispatchEvent(
                        new MessageEvent("message", {data: payload})
                    );
                }""",
                {
                    "type": "streamlit:render",
                    "args": {
                        "document": _fixture_document(),
                        "editable": True,
                        "height": 820,
                    },
                },
            )

            assert not page_errors, page_errors

            # READ: canvas selection and Navigator selection must expose the same object.
            page.locator('[data-kind="cause"][data-id="CAUSE-PLACEMENT-1"]').click()
            expect(page.locator("#editName")).to_have_value("Existing Threat")
            expect(page.locator("#delete")).not_to_be_disabled()

            # UPDATE: edit multiple inspector fields, then commit them explicitly.
            page.locator("#editName").fill("Updated Threat")
            page.locator("#editDesc").fill("Updated through the Bowtie inspector.")
            page.locator("#applyChanges").click()

            expect(page.locator("#objects")).to_contain_text("Updated Threat")
            emitted_immediate = page.evaluate("window.__surmMessages")
            changed_immediate = [
                item["value"]["document"]
                for item in emitted_immediate
                if item["type"] == "streamlit:setComponentValue"
                and item["value"]
            ]
            assert changed_immediate
            assert changed_immediate[-1]["library"]["cause"][0]["name"] == "Updated Threat"
            assert changed_immediate[-1]["library"]["cause"][0]["description"] == (
                "Updated through the Bowtie inspector."
            )
            expect(page.locator("#editName")).to_have_value("Updated Threat")
            expect(page.locator("#editDesc")).to_have_value(
                "Updated through the Bowtie inspector."
            )

            emitted = page.evaluate("window.__surmMessages")
            changed = [
                item["value"]["document"]
                for item in emitted
                if item["type"] == "streamlit:setComponentValue"
                and item["value"]
            ]
            assert changed
            changed_document = changed[-1]
            assert changed_document["editor_revision"] > 0

            # Streamlit rerun: same persisted document must NOT clear selection/history.
            page.evaluate(
                """document => {
                    window.dispatchEvent(
                        new MessageEvent("message", {
                            data: {
                                type: "streamlit:render",
                                args: {
                                    document: document,
                                    editable: true,
                                    height: 820
                                }
                            }
                        })
                    );
                }""",
                changed_document,
            )
            page.wait_for_timeout(60)

            expect(page.locator("#editName")).to_have_value("Updated Threat")
            expect(page.locator("#delete")).not_to_be_disabled()
            expect(page.locator("#undo")).not_to_be_disabled()

            # CREATE + UPDATE + DELETE: preventive barrier and its barrier-specific fields.
            page.locator("#objects button", has_text="Updated Threat").click()
            page.locator("#addPrevent").click()
            page.wait_for_timeout(40)
            expect(page.locator("#objects")).to_contain_text("New Preventive Barrier")

            prevent_emitted = page.evaluate("window.__surmMessages")
            prevent_docs = [
                item["value"]["document"]
                for item in prevent_emitted
                if item["type"] == "streamlit:setComponentValue"
                and item["value"]
            ]
            assert prevent_docs
            prevent_doc = prevent_docs[-1]
            new_prevent_id = next(
                p["id"]
                for p in prevent_doc["preventativeBarriers"]
                if p["nodeId"].startswith("PB_")
            )
            updated_threat_line = next(
                line for line in prevent_doc["lines"]
                if line["originId"] == "CAUSE-PLACEMENT-1"
            )
            assert new_prevent_id in updated_threat_line["stops"]
            new_prevent = page.locator(
                "#objects button", has_text="New Preventive Barrier"
            )
            new_prevent.click()
            expect(page.locator("#editName")).to_have_value("New Preventive Barrier")
            page.locator("#editName").fill("Updated Preventive Barrier")
            page.locator("#editDesc").fill("Barrier description from inspector.")
            page.locator("#editOwner").fill("Reservoir Engineering")
            page.locator("#editEff").select_option("high")
            page.locator("#editDegradation").fill("Erosion\nLoss of containment")
            page.locator("#editControls").fill("Inspection\nIntegrity review")
            page.locator("#applyChanges").click()
            page.wait_for_timeout(180)

            expect(page.locator("#objects")).to_contain_text("Updated Preventive Barrier")
            expect(page.locator("#editOwner")).to_have_value("Reservoir Engineering")
            expect(page.locator("#editEff")).to_have_value("high")
            expect(page.locator("#editDegradation")).to_have_value(
                "Erosion\nLoss of containment"
            )
            expect(page.locator("#editControls")).to_have_value(
                "Inspection\nIntegrity review"
            )

            page.locator("#delete").click()
            page.wait_for_timeout(100)
            expect(page.locator("#objects")).not_to_contain_text(
                "Updated Preventive Barrier"
            )

            # CREATE + DELETE: mitigative barrier.
            page.locator("#objects button", has_text="Existing Consequence").click()
            page.locator("#addMitigate").click()
            page.wait_for_timeout(40)
            expect(page.locator("#objects")).to_contain_text("New Mitigative Barrier")

            mitigate_emitted = page.evaluate("window.__surmMessages")
            mitigate_docs = [
                item["value"]["document"]
                for item in mitigate_emitted
                if item["type"] == "streamlit:setComponentValue"
                and item["value"]
            ]
            assert mitigate_docs
            mitigate_doc = mitigate_docs[-1]
            new_mitigate_id = next(
                p["id"]
                for p in mitigate_doc["mitigativeBarriers"]
                if p["nodeId"].startswith("MB_")
            )
            existing_outcome_line = next(
                line for line in mitigate_doc["lines"]
                if line["originId"] == "OUTCOME-PLACEMENT-1"
            )
            assert new_mitigate_id in existing_outcome_line["stops"]
            page.locator(
                "#objects button", has_text="New Mitigative Barrier"
            ).click()
            page.locator("#delete").click()
            page.wait_for_timeout(100)
            expect(page.locator("#objects")).not_to_contain_text(
                "New Mitigative Barrier"
            )

            # CREATE + DELETE: second threat must receive a unique origin line ID.
            page.locator("#addCause").click()
            page.wait_for_timeout(40)
            repeated_threat_docs = [
                item["value"]["document"]
                for item in page.evaluate("window.__surmMessages")
                if item["type"] == "streamlit:setComponentValue"
                and item["value"]
            ]
            assert repeated_threat_docs
            repeated_doc = repeated_threat_docs[-1]
            cause_line_ids = [
                line["id"]
                for line in repeated_doc["lines"]
                if line["originType"] == "cause"
            ]
            assert len(cause_line_ids) == len(set(cause_line_ids))
            assert any(line["originId"] == "CAUSE-PLACEMENT-3" for line in repeated_doc["lines"])
            page.locator("#delete").click()
            page.wait_for_timeout(40)
            after_threat_delete = [
                item["value"]["document"]
                for item in page.evaluate("window.__surmMessages")
                if item["type"] == "streamlit:setComponentValue"
                and item["value"]
            ][-1]
            assert not any(
                line["originId"] == "CAUSE-PLACEMENT-3"
                for line in after_threat_delete["lines"]
            )

            # CREATE + DELETE: consequence.
            page.locator("#addOutcome").click()
            page.wait_for_timeout(40)
            expect(page.locator("#objects")).to_contain_text("New Consequence")
            page.locator(
                "#objects button", has_text="New Consequence"
            ).click()
            page.locator("#delete").click()
            page.wait_for_timeout(100)
            expect(page.locator("#objects")).not_to_contain_text(
                "New Consequence"
            )

            # DELETE: the updated threat and its origin line.
            page.locator("#objects button", has_text="Updated Threat").click()
            page.locator("#delete").click()
            page.wait_for_timeout(100)
            expect(page.locator("#objects")).not_to_contain_text("Updated Threat")
            assert page.locator('[data-layer="connectors"] .connector').count() >= 2

            assert not page_errors, page_errors
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
