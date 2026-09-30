"""Browser smoke test for the real SURM Streamlit entrypoint."""

from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

pytestmark = pytest.mark.browser


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_server(port: int, process: subprocess.Popen[str], timeout: float = 25.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            raise AssertionError(
                f"Streamlit exited before becoming ready (code={process.returncode}).\n{output}"
            )
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.25)

    raise AssertionError("Streamlit server did not become reachable within 25 seconds.")


def _wait_for_idle(page, timeout: int = 10_000) -> None:
    """Wait until Streamlit is connected and the current script run is idle."""
    expect(
        page.locator('[data-testid="stApp"][data-test-connection-state="CONNECTED"]')
    ).to_be_visible(timeout=timeout)
    expect(
        page.locator('[data-testid="stApp"][data-test-script-state="notRunning"]')
    ).to_have_count(1, timeout=timeout)


def _assert_core_ui(page) -> None:
    """Assert the application contract using user-visible UI, not Streamlit internals."""
    expect(page.get_by_text("SURM Toolkit", exact=True).first).to_be_visible(timeout=10_000)
    expect(page.get_by_text("CURRENT STUDY", exact=True).first).to_be_visible(timeout=10_000)
    expect(page.get_by_text("AT A GLANCE", exact=True)).to_be_visible(timeout=10_000)
    expect(page.get_by_text("Study setup", exact=True)).to_be_visible(timeout=10_000)
    expect(page.get_by_text("Workflow progress", exact=True)).to_be_visible(timeout=10_000)
    expect(page.get_by_label("Project Name")).to_be_visible(timeout=10_000)


def _browser_diagnostics(page) -> dict:
    """Collect enough runtime state to make a white-screen failure actionable."""
    return page.evaluate(
        """() => {
            const app = document.querySelector('[data-testid="stApp"]');
            const root = document.querySelector('[data-testid="stAppViewContainer"]');
            const main = document.querySelector('[data-testid="stMainBlockContainer"]');
            const rect = main ? main.getBoundingClientRect() : null;
            return {
                app: app ? {
                    connection: app.getAttribute('data-test-connection-state'),
                    script: app.getAttribute('data-test-script-state'),
                } : null,
                root: root ? {
                    display: getComputedStyle(root).display,
                    visibility: getComputedStyle(root).visibility,
                    opacity: getComputedStyle(root).opacity,
                } : null,
                main: main ? {
                    display: getComputedStyle(main).display,
                    visibility: getComputedStyle(main).visibility,
                    opacity: getComputedStyle(main).opacity,
                    width: rect ? rect.width : 0,
                    height: rect ? rect.height : 0,
                } : null,
                titleCount: document.querySelectorAll('[data-testid="stAppViewContainer"] *').length,
                bodyTextLength: (document.body.innerText || '').length,
            };
        }"""
    )


def test_full_streamlit_entrypoint_is_visible_in_browser():
    project_root = Path(__file__).resolve().parents[1]
    port = _free_port()
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(project_root / "surm.py"),
            "--server.headless=true",
            f"--server.port={port}",
            "--browser.gatherUsageStats=false",
        ],
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        _wait_for_server(port, process)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page_errors: list[str] = []
            console_errors: list[str] = []
            request_failures: list[str] = []

            page.on("pageerror", lambda exc: page_errors.append(str(exc)))
            page.on(
                "console",
                lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
            )
            page.on(
                "requestfailed",
                lambda request: request_failures.append(
                    f"{request.method} {request.url}: {request.failure}"
                ),
            )

            page.goto(
                f"http://127.0.0.1:{port}",
                wait_until="domcontentloaded",
            )

            _wait_for_idle(page)
            _assert_core_ui(page)

            # Detect the user's flash-then-blank failure rather than only
            # verifying the first successful paint.
            last_delay = 0
            for delay_ms in (1_000, 2_000, 3_000, 5_000):
                page.wait_for_timeout(delay_ms - last_delay)
                _wait_for_idle(page)
                _assert_core_ui(page)
                last_delay = delay_ms

            # Exercise a real widget-driven rerun. Project Name uses an
            # on_change callback, so blur triggers the same rerun path a user
            # hits while filling the study setup form.
            project_input = page.get_by_label("Project Name")
            project_input.fill("Browser Stability Test")
            project_input.press("Tab")
            expect(project_input).to_have_value("Browser Stability Test", timeout=10_000)
            page.wait_for_timeout(2_000)
            _wait_for_idle(page)
            _assert_core_ui(page)
            expect(project_input).to_have_value("Browser Stability Test", timeout=10_000)

            sidebar = page.locator('[data-testid="stSidebar"]')
            sidebar.get_by_role("button", name="• Team").click()
            _wait_for_idle(page)
            expect(page.get_by_text("Team", exact=True).first).to_be_visible(timeout=10_000)
            _assert_core_ui(page)

            sidebar.get_by_role("button", name="• Uncertainties").click()
            _wait_for_idle(page)
            expect(page.get_by_text("Uncertainties", exact=True).first).to_be_visible(timeout=10_000)
            expect(page.get_by_text("Selection Summary", exact=True)).to_be_visible(timeout=10_000)

            sidebar.get_by_role("button", name="• Overview").click()
            _wait_for_idle(page)
            _assert_core_ui(page)

            diagnostics = _browser_diagnostics(page)
            assert diagnostics["app"] is not None, diagnostics
            assert diagnostics["app"]["connection"] == "CONNECTED", diagnostics
            assert diagnostics["app"]["script"] == "notRunning", diagnostics
            assert diagnostics["main"] is not None, diagnostics
            assert diagnostics["main"]["width"] > 0, diagnostics
            assert diagnostics["main"]["height"] > 0, diagnostics

            assert not page_errors, page_errors
            assert not console_errors, console_errors
            assert not request_failures, request_failures

            browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
