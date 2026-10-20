"""Execute and save the amended case-study notebook, including its plots."""

from pathlib import Path

import nbformat
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "Department_Of_Phisheries.ipynb"
notebook = nbformat.read(path, as_version=4)
client = NotebookClient(notebook, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}})
client.execute()
nbformat.write(notebook, path)
print("Executed and saved every analysis cell, the fifteen sample comparisons and their figures.")
