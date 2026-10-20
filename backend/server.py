"""Optional localhost API and Power BI connector for the Streamlit case study."""

import argparse
import csv
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import math
from pathlib import Path
import sys
from urllib.parse import urlsplit, parse_qs


project_folder = Path(__file__).resolve().parents[1]
if str(project_folder) not in sys.path:
    sys.path.insert(0, str(project_folder))

from case_study.config import ARTIFACTS
from case_study.service import get_service, snapshot_signature, SnapshotError, InputError

output_folder = ARTIFACTS
dashboard_folder = output_folder / "bi"

# Keep the public surface explicit. Request paths never become file paths.
table_names = {
    "class_summary", "quality_summary", "feature_rates", "tld_summary",
    "length_distribution", "statistical_evidence", "indicator_decisions",
    "rule_summary", "rule_chart", "descriptive_summary",
    "model_summary", "model_metric_chart", "model_confusion",
    "model_partitions",
    "sampling_comparison", "sampling_membership",
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
        parsed = urlsplit(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        if path in {"/", "/health"}:
            error = None
            try:
                service = get_service(snapshot_signature())
                ready = all(file.is_file() for file in csv_paths.values())
            except (SnapshotError, OSError, ValueError) as problem:
                ready, error = False, str(problem)
            self.respond(200 if ready else 503, {
                "status": "ready" if ready else "prepare the verified snapshot first",
                "purpose": "Verified notebook results, genuine model inference and Power BI imports",
                "refresh": "Run python -m case_study.prepare, then refresh Power BI",
                "error": error,
                "endpoints": ["/api/summary", "/api/evidence", "/api/study", "/api/questions", "/api/eda",
                              "/api/models", "/api/sampling", "/api/feature-schema?model=logistic_regression",
                              "/api/random-fill?model=logistic_regression", "POST /api/predict", *sorted(csv_paths)],
            })
            return
        if path in {"/api/study", "/api/questions", "/api/eda", "/api/models", "/api/sampling", "/api/feature-schema", "/api/random-fill"} or path.startswith("/api/questions/"):
            try:
                service = get_service(snapshot_signature())
                model_id = query.get("model", ["logistic_regression"])[0]
                if path == "/api/study":
                    result = service.study
                elif path == "/api/questions":
                    result = service.questions
                elif path.startswith("/api/questions/"):
                    value = path.rsplit("/", 1)[-1]
                    result = service.question(int(value)) if value.isdigit() else None
                    if result is None:
                        self.respond(404, {"error": "Unknown source question"})
                        return
                elif path == "/api/eda":
                    result = service.eda
                elif path == "/api/models":
                    result = {"models": service.study["models"], "target_mapping": service.study["model_label_mapping"]}
                elif path == "/api/sampling":
                    result = service.sampling
                elif path == "/api/feature-schema":
                    result = {"model_id": model_id, "feature_order": service.study["feature_order"], "fields": service.schema(model_id)}
                else:
                    result = service.random_fill(model_id)
                self.respond(200, result)
            except InputError as error:
                self.respond(422, {"error": str(error)})
            except (SnapshotError, OSError, ValueError) as error:
                self.respond(503, {"error": str(error)})
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
            self.respond(503, {"error": "Verified analysis is missing. Run python -m case_study.prepare."})
            return

        if path == "/api/evidence":
            reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
            records = [{key: value if key == "PValueDisplay" else json_value(value)
                        for key, value in row.items()} for row in reader]
            self.respond(200, records)
        elif path.endswith(".csv"):
            self.respond(200, content, "text/csv; charset=utf-8")
        else:
            self.respond(200, content)

    def do_POST(self):
        if urlsplit(self.path).path != "/api/predict":
            self.respond(404, {"error": "Unknown endpoint"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16384:
                self.respond(413, {"error": "Prediction JSON must be between 1 byte and 16 KB."})
                return
            if self.headers.get_content_type() != "application/json":
                self.respond(415, {"error": "Use application/json."})
                return
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict) or set(payload) != {"model_id", "features"}:
                raise InputError("Supply exactly model_id and features.")
            service = get_service(snapshot_signature())
            self.respond(200, service.predict(payload["model_id"], payload["features"]))
        except (InputError, json.JSONDecodeError, ValueError) as error:
            self.respond(422, {"error": str(error)})
        except (SnapshotError, OSError) as error:
            self.respond(503, {"error": str(error)})


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
