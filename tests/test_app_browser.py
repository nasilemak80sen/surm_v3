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
            "--server.fileWatcherType=none",
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
            page.on("pageerror", lambda exc: page_errors.append(str(exc)))

            page.goto(f"http://127.0.0.1:{port}", wait_until="domcontentloaded")
            expect(page.locator("body")).to_contain_text("SURM Toolkit", timeout=20_000)
            expect(page.locator("body")).to_contain_text("CURRENT STUDY", timeout=20_000)
            assert not page_errors, page_errors

            browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
