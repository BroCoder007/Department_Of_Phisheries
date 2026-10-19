"""Read the original notebooks without rewriting or executing uploaded content."""

import base64
import hashlib
import io
from html.parser import HTMLParser
import json
from pathlib import Path
import re

import pandas as pd


def fingerprint(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_notebook(path):
    notebook = json.loads(Path(path).read_text(encoding="utf-8"))
    for cell in notebook["cells"]:
        cell["source"] = "".join(cell.get("source", []))
    return notebook


def stream_text(cell):
    return "\n".join("".join(output.get("text", [])) for output in cell.get("outputs", [])
                     if output.get("output_type") == "stream")


class _TableReader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"}:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.cell is not None:
            if self.row is not None:
                self.row.append("".join(self.cell).strip())
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def stored_tables(cell):
    tables = []
    for output in cell.get("outputs", []):
        html = output.get("data", {}).get("text/html")
        if html and "<table" in "".join(html):
            parser = _TableReader()
            parser.feed("".join(html))
            if not parser.rows:
                continue
            header, body = parser.rows[0], parser.rows[1:]
            if header and header[0] == "":
                header = header[1:]
                body = [row[1:] for row in body]
            table = pd.DataFrame(body, columns=header)
            for name in table.columns:
                try:
                    table[name] = pd.to_numeric(table[name])
                except (ValueError, TypeError):
                    pass
            tables.append(table)
    return tables


def save_original_figures(notebook, destination):
    destination.mkdir(parents=True, exist_ok=True)
    figures = {}
    for index, cell in enumerate(notebook["cells"]):
        for output_index, output in enumerate(cell.get("outputs", [])):
            png = output.get("data", {}).get("image/png")
            if png:
                filename = f"cell_{index:03d}_{output_index:02d}.png"
                (destination / filename).write_bytes(base64.b64decode("".join(png)))
                figures.setdefault(index, []).append(filename)
    return figures


def questions_from_notebook(notebook, original_figures):
    starts = []
    for index, cell in enumerate(notebook["cells"]):
        match = re.search(r"^#{1,6}\s+(Q(\d+)\.\s+(.+))$", cell["source"], re.M) if cell["cell_type"] == "markdown" else None
        if match:
            starts.append((index, int(match[2]), match[1], match[3]))
    questions = []
    for position, (start, number, heading, title) in enumerate(starts):
        stop = starts[position + 1][0] if position + 1 < len(starts) else len(notebook["cells"])
        section = []
        for index in range(start, stop):
            cell = notebook["cells"][index]
            if index > start and cell["cell_type"] == "markdown" and re.match(r"^##\s+\d+\.", cell["source"]):
                break
            section.append((index, cell))
        header = notebook["cells"][start]["source"]
        hypothesis_lines = [line.strip().lstrip("- ") for line in header.splitlines()
                            if re.search(r"\*\*H[01]:|(?:Null|Alternative) Hypothesis", line)]
        questions.append({
            "number": number, "heading": heading, "title": title,
            "source_cell": start, "original_markdown": header,
            "null": hypothesis_lines[0] if hypothesis_lines else "Not stated in the notebook",
            "alternative": hypothesis_lines[1] if len(hypothesis_lines) > 1 else "Not stated in the notebook",
            "original_interpretation": "\n\n".join(c["source"] for i, c in section[1:] if c["cell_type"] == "markdown"),
            "code": "\n\n".join(c["source"] for i, c in section if c["cell_type"] == "code"),
            "saved_output": "\n".join(stream_text(c) for i, c in section if c["cell_type"] == "code"),
            "original_figures": [f"original/analysis/{name}" for i, c in section for name in original_figures.get(i, [])],
        })
    return questions


def plots_from_notebook(notebook, originals):
    plots = []
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "markdown":
            continue
        match = re.search(r"^### Plot (\d+)\s*[—–-]\s*(.+)$", cell["source"], re.M)
        if not match:
            continue
        code_index = index + 1
        if code_index >= len(notebook["cells"]):
            continue
        plot_code = notebook["cells"][code_index]
        interpretation = notebook["cells"][code_index + 1]["source"] if code_index + 1 < len(notebook["cells"]) else ""
        plots.append({"number": int(match[1]), "title": match[2], "source_cell": code_index,
                      "code": plot_code["source"], "interpretation": interpretation,
                      "saved_output": stream_text(plot_code),
                      "original_figures": [f"original/eda/{name}" for name in originals.get(code_index, [])]})
    return plots


CORRECTIONS = [
    {"id": "sample_grains", "source": "Department_Of_Phisheries.ipynb, conclusion cell 78",
     "issue": "The conclusion calls 220,023 the retained unique-URL count and describes all 15 tests as full-host comparisons.",
     "correction": "235,370 unique URLs are retained; 220,023 consistently labeled exact hosts form the main test sample. Q13–Q14 use 1,500 hosts per class. Exact hostname grouping does not guarantee independent campaigns."},
    {"id": "rule_tradeoff", "source": "Department_Of_Phisheries.ipynb, cells 69 and 78",
     "issue": "The narrative says Rule B reduces false alarms.",
     "correction": "Both rules produce zero false alerts in this sample. B misses 159 additional phishing hosts and avoids zero false alerts. The app uses the computed table, not the contradictory sentence."},
    {"id": "statistical_language", "source": "Department_Of_Phisheries.ipynb, question interpretations",
     "issue": "Some interpretations call tests proof, describe simulated differences as impossible, or print p approximately zero.",
     "correction": "Tests supply evidence under assumptions. The permutation simulation has 1,999 shuffles plus the observed arrangement and a minimum p of 0.0005. Floating-point underflow is not a mathematical probability of zero."},
    {"id": "causal_explanations", "source": "Department_Of_Phisheries.ipynb, cells 32, 35, 53, 61 and 64",
     "issue": "Text attributes patterns to attacker intent, valid certificates, cheap domains, hurried construction or engineering effort.",
     "correction": "The dataset records features and labels, not motives, certificate validity, domain prices or engineering effort. The app reports observed differences and keeps such explanations as untested possibilities."},
    {"id": "model_count", "source": "Model_Evaluation.ipynb, introduction versus training cell 7",
     "issue": "The introduction lists three classifiers, but executable code also trains Gaussian Naive Bayes.",
     "correction": "All four fitted classifiers and the majority baseline are preserved, as explicitly confirmed by the user."},
    {"id": "confusion_labels", "source": "Model_Evaluation.ipynb, cell 15",
     "issue": "The logistic and pruned-tree subplot titles are swapped. The first three matrices use the CSV's reversed class order even though model target 0 means legitimate.",
     "correction": "The app renders each matrix from its own verified predictions with actual/predicted labels Legitimate (0), Phishing (1). Original figure is retained for comparison."},
    {"id": "analysis_export", "source": "Department_Of_Phisheries.ipynb, cell 74",
     "issue": "The export-preparation cell still references model_summary and confusion after model training moved to Model_Evaluation.ipynb.",
     "correction": "The adapter executes every preprocessing and question/test cell, then exports available statistical tables directly. All model exports come from Model_Evaluation.ipynb. Original notebooks are unchanged."},
    {"id": "eda_grain", "source": "Plots.ipynb, cells 6–9",
     "issue": "Plots retains repeated URLs and domains for descriptive EDA, while the analysis notebook deduplicates URLs and samples hosts for testing.",
     "correction": "Both strategies are preserved. EDA views say raw source records; question/test views say eligible hosts or their stated subsample. Their different denominators are not mixed."},
    {"id": "heatmap_legend", "source": "Plots.ipynb, cell 71",
     "issue": "The binary-rate heatmap title says blue is high and red is low, but its actual colorbar maps low to blue and high to red.",
     "correction": "The interactive heatmap uses an explicitly labeled 0–1 colorbar. Values and class ordering are unchanged; the original figure remains accessible."},
    {"id": "minor_wording", "source": "Plots.ipynb cell 3; Department_Of_Phisheries.ipynb cell 56",
     "issue": "A missing f-string prints a literal expression for missing cells; a title-score interpretation calls its histogram a boxplot.",
     "correction": "The app shows the actual missing-cell count and identifies the title-difference chart as a histogram."},
]
