"""Serve the case study's saved aggregates to Power BI over localhost."""

import argparse
import csv
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import math
from pathlib import Path
from urllib.parse import urlsplit


project_folder = Path(__file__).resolve().parents[1]
output_folder = project_folder / "outputs"
dashboard_folder = output_folder / "powerbi"

# Keep the public surface explicit. Request paths never become file paths.
table_names = {
    "class_summary", "quality_summary", "feature_rates", "tld_summary",
    "length_distribution", "statistical_evidence", "indicator_decisions",
    "rule_summary", "rule_chart", "descriptive_summary",
    "model_summary", "model_metric_chart", "model_confusion",
    "model_partitions",
}
csv_paths = {f"/data/{name}.csv": dashboard_folder / f"{name}.csv" for name in table_names}


def json_value(text):
    """Preserve missing values and avoid nonstandard Infinity/NaN in JSON."""
    if text == "":
        return None
    if text in {"True", "False"}:
        return text == "True"
    try:
        number = float(text)
    except (ValueError, TypeError):
        return text
    if not math.isfinite(number):
        return None
    return int(number) if number.is_integer() else number


class AnalysisHandler(BaseHTTPRequestHandler):
    def respond(self, status, payload, content_type="application/json; charset=utf-8"):
        if not isinstance(payload, bytes):
            payload = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in {"/", "/health"}:
            ready = (output_folder / "run_summary.json").is_file() and all(file.is_file() for file in csv_paths.values())
            self.respond(200 if ready else 503, {
                "status": "ready" if ready else "run the notebook first",
                "purpose": "Saved aggregate analysis for the Phisheries case study",
                "refresh": "Rerun the notebook, then refresh the Power BI import model",
                "endpoints": ["/api/summary", "/api/evidence", *sorted(csv_paths)],
            })
            return
        if path == "/api/summary":
            source = output_folder / "run_summary.json"
        elif path == "/api/evidence":
            source = dashboard_folder / "statistical_evidence.csv"
        elif path in csv_paths:
            source = csv_paths[path]
        else:
            self.respond(404, {"error": "Unknown endpoint"})
            return

        try:
            content = source.read_bytes()
        except FileNotFoundError:
            self.respond(503, {"error": "Analysis output is missing. Run the notebook from top to bottom."})
            return

        if path == "/api/evidence":
            reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
            records = [{key: json_value(value) for key, value in row.items()} for row in reader]
            self.respond(200, records)
        elif path.endswith(".csv"):
            self.respond(200, content, "text/csv; charset=utf-8")
        else:
            self.respond(200, content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    arguments = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", arguments.port), AnalysisHandler)
    print(f"Analysis backend: http://127.0.0.1:{arguments.port}", flush=True)
    print("Press Ctrl+C to stop. The server reads completed notebook outputs.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
