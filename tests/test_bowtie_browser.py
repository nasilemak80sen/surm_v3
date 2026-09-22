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
        "pages": [{"topLevelEvent": {"name": "Loss of containment"}}],
        "causes": [
            {
                "id": "CAUSE-PLACEMENT-1",
                "nodeId": "C1",
                "x": 120,
                "y": 180,
                "w": 210,
                "h": 80,
                "pageId": "PAGE_1",
            }
        ],
        "preventativeBarriers": [
            {
                "id": "PREVENTIVE-PLACEMENT-1",
                "nodeId": "PB1",
                "x": 410,
                "y": 180,
                "w": 120,
                "h": 112,
                "pageId": "PAGE_1",
            }
        ],
        "mitigativeBarriers": [
            {
                "id": "MITIGATIVE-PLACEMENT-1",
                "nodeId": "MB1",
                "x": 1040,
                "y": 180,
                "w": 120,
                "h": 112,
                "pageId": "PAGE_1",
            }
        ],
        "outcomes": [
            {
                "id": "OUTCOME-PLACEMENT-1",
                "nodeId": "O1",
                "x": 1440,
                "y": 180,
                "w": 210,
                "h": 80,
                "pageId": "PAGE_1",
            }
        ],
        "lines": [
            {
                "id": "LINE-CAUSE",
                "originType": "cause",
                "originId": "CAUSE-PLACEMENT-1",
                "stops": ["PREVENTIVE-PLACEMENT-1"],
                "pageId": "PAGE_1",
            },
            {
                "id": "LINE-OUTCOME",
                "originType": "outcome",
                "originId": "OUTCOME-PLACEMENT-1",
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
                }
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
                }
            ],
        },
    }


def test_bowtie_editor_browser_round_trip_and_controls():
    server, thread = _serve_frontend()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(accept_downloads=True)
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
                        "height": 760,
                    },
                },
            )

            expect(page.locator("#riskInfo")).to_contain_text("RSK-001")
            expect(page.locator("#title")).to_have_text("Browser Regression Risk")

            messages = page.evaluate("window.__surmMessages")
            assert any(
                item["type"] == "streamlit:componentReady"
                for item in messages
            )
            assert any(
                item["type"] == "streamlit:setFrameHeight"
                for item in messages
            )

            first_cause = page.locator(
                '[data-kind="cause"][data-id="CAUSE-PLACEMENT-1"]'
            )
            before_x = float(first_cause.get_attribute("x"))

            box = first_cause.bounding_box()
            assert box is not None
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.down()
            page.mouse.move(
                box["x"] + box["width"] / 2 + 40,
                box["y"] + box["height"] / 2 + 10,
            )
            page.mouse.up()

            after_x = float(
                page.locator(
                    '[data-kind="cause"][data-id="CAUSE-PLACEMENT-1"]'
                ).get_attribute("x")
            )
            assert after_x != before_x

            page.locator("#addCause").click()
            expect(page.locator("#objects")).to_contain_text("New Threat")

            new_threat = page.locator("#objects button", has_text="New Threat")
            new_threat.click()
            expect(page.locator("#editName")).to_have_value("New Threat")

            page.locator("#editName").fill("Edited Threat")
            page.locator("#editName").press("Tab")
            expect(page.locator("#objects")).to_contain_text("Edited Threat")

            page.wait_for_timeout(250)
            emitted = page.evaluate("window.__surmMessages")
            assert any(
                item["type"] == "streamlit:setComponentValue"
                and item["value"]
                and item["value"]["document"]["editor_revision"] > 0
                for item in emitted
            )

            undo = page.locator("#undo")
            redo = page.locator("#redo")
            expect(undo).not_to_be_disabled()

            undo.click()
            expect(page.locator("#objects")).to_contain_text("New Threat")
            expect(redo).not_to_be_disabled()

            redo.click()
            expect(page.locator("#objects")).to_contain_text("Edited Threat")

            with page.expect_download(timeout=5000) as download_info:
                page.locator("#exportSvg").click()
            download = download_info.value
            assert download.suggested_filename.endswith("_Bowtie.svg")

            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
