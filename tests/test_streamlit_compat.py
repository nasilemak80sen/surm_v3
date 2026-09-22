from pathlib import Path


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
