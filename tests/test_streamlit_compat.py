from pathlib import Path
import subprocess
import sys


def test_runtime_pins_supported_streamlit_version():
    project_root = Path(__file__).resolve().parents[1]
    requirements = (project_root / "requirements.txt").read_text(encoding="utf-8")
    assert "streamlit==1.62.0" in requirements


def test_runtime_ui_does_not_use_newer_width_stretch_api():
    """The project supports Streamlit >=1.35, where width='stretch' is invalid for these APIs."""
    project_root = Path(__file__).resolve().parents[1]
    runtime_dirs = [project_root / "surm.py", project_root / "modules"]

    python_files = []
    for entry in runtime_dirs:
        if entry.is_file():
            python_files.append(entry)
        else:
            python_files.extend(entry.glob("*.py"))

    offenders = []
    for path in python_files:
        text = path.read_text(encoding="utf-8")
        if 'width="stretch"' in text or "width='stretch'" in text:
            offenders.append(path.relative_to(project_root).as_posix())

    assert offenders == []


def test_service_modules_import_cleanly_in_fresh_python_process():
    """Catch circular-import/module-cache failures before Streamlit hot reload hits them."""
    project_root = Path(__file__).resolve().parents[1]
    code = (
        "import utils.assurance; "
        "import utils.intelligence; "
        "import utils.export_excel; "
        "assert callable(utils.assurance.study_is_editable); "
        "assert callable(utils.intelligence.build_bowtie_qa); "
        "assert callable(utils.export_excel.build_excel_export)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "Service-module import smoke test failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
