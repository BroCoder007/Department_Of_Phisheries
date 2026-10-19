"""Package the local app, original evidence and prepared results for handover."""

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "dist" / "Department_Of_Phisheries_Streamlit.zip"
FOLDERS = [".streamlit", "assets", "backend", "case_study", "docs", "scripts",
           "tests", "artifacts", "outputs/powerbi", "powerbi"]
FILES = ["streamlit_app.py", "README.md", "requirements.txt", "requirements-lock.txt",
         "start_app.ps1", "start_app.bat", "Department_Of_Phisheries.ipynb",
         "Plots.ipynb", "Model_Evaluation.ipynb", "PhiUSIIL_Phishing_URL_Dataset.csv"]


def release_files():
    paths = [ROOT / name for name in FILES]
    for folder in FOLDERS:
        paths.extend(path for path in (ROOT / folder).rglob("*") if path.is_file())
    excluded = {"__pycache__", ".pbi", ".git", ".venv"}
    return sorted(set(path for path in paths if not excluded.intersection(path.parts)
                      and path.suffix not in {".pyc", ".sqlite3", ".db"}))


def build():
    DESTINATION.parent.mkdir(exist_ok=True)
    paths = release_files()
    with ZipFile(DESTINATION, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for path in paths:
            archive.write(path, "Department_Of_Phisheries/" + path.relative_to(ROOT).as_posix())

    manifest = json.loads((ROOT / "artifacts/manifest.json").read_text(encoding="utf-8"))
    expected = {entry["filename"]: entry["sha256"] for entry in manifest["notebooks"].values()}
    expected["PhiUSIIL_Phishing_URL_Dataset.csv"] = manifest["dataset_sha256"]
    with ZipFile(DESTINATION) as archive:
        assert archive.testzip() is None, "A release member failed its CRC check."
        for filename, digest in expected.items():
            actual = hashlib.sha256(archive.read("Department_Of_Phisheries/" + filename)).hexdigest()
            assert actual == digest, f"Source changed: {filename}"
        names = archive.namelist()
        assert not any(".sqlite3" in name or "/.work/" in name for name in names)
    print(f"Created {DESTINATION}")
    print(f"{len(paths)} files; {DESTINATION.stat().st_size / 1024**2:.1f} MB; CRC and source hashes verified.")


if __name__ == "__main__":
    build()
