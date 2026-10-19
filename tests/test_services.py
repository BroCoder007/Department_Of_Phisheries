import importlib.util
import io
import json
from pathlib import Path
import re
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
from PIL import Image

from case_study.config import ROOT, ARTIFACTS, NOTEBOOKS
from case_study.service import StudyService, InputError, SnapshotError
from case_study.sources import read_notebook, fingerprint
from case_study import team


class VerifiedNotebookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = StudyService()

    def test_every_original_heading_is_preserved_verbatim(self):
        headings = []
        for cell in read_notebook(NOTEBOOKS["analysis"])["cells"]:
            if cell["cell_type"] == "markdown":
                match = re.search(r"^#{1,6}\s+(Q\d+\.\s+.+)$", cell["source"], re.M)
                if match:
                    headings.append(match[1])
        self.assertGreaterEqual(len(headings), 15)
        self.assertEqual(headings, [q["heading"] for q in self.service.questions])

    def test_all_three_sources_and_saved_tests_are_verified(self):
        self.assertEqual(set(self.service.manifest["notebooks"]), {"analysis", "eda", "models"})
        for key, path in NOTEBOOKS.items():
            self.assertEqual(fingerprint(path), self.service.manifest["notebooks"][key]["sha256"])
        self.assertEqual(len(self.service.study["statistical_verification"]), 15)
        for question in self.service.questions:
            self.assertTrue(question["null"])
            self.assertTrue(question["alternative"])
            self.assertTrue(question["original_figures"])
            self.assertIn("record_result", question["code"])
            self.assertEqual(question["test"]["alpha"], 0.05)
        self.assertEqual(self.service.study["model_verification"]["train_test_host_overlap"], 0)

    def test_artifacts_and_raw_dataset_counts_are_consistent(self):
        for name, expected in self.service.manifest["files"].items():
            self.assertEqual(fingerprint(ARTIFACTS / name), expected, name)
        self.assertEqual(len(self.service.raw), self.service.study["raw_rows"])
        self.assertEqual(self.service.raw.shape[1], self.service.study["columns"])
        actual = self.service.raw.label.value_counts()
        self.assertEqual(actual[0], self.service.study["raw_class_counts"]["Phishing"])
        self.assertEqual(actual[1], self.service.study["raw_class_counts"]["Legitimate"])
        frame = pd.read_csv(ARTIFACTS / "bi/statistical_evidence.csv")
        for q in self.service.questions:
            row = frame.loc[frame.Question == q["number"]].iloc[0]
            self.assertAlmostEqual(row.Statistic, q["test"]["Statistic"], places=9)
            self.assertEqual(row.PValueDisplay, q["test"]["PValueDisplay"])
        self.assertEqual(self.service.study["extra_missed"], 159)
        self.assertEqual(self.service.study["avoided_alerts"], 0)

    def test_selected_eda_is_traceable_to_original_notebook(self):
        catalog = self.service.read_json("plot_catalog.json")
        source_plots = {p["number"]: p for p in catalog}
        self.assertEqual(len(catalog), 23)
        self.assertEqual(len(self.service.eda), 12)
        for plot in self.service.eda:
            self.assertEqual(plot["code"], source_plots[plot["number"]]["code"])
            self.assertEqual(plot["interpretation"], source_plots[plot["number"]]["interpretation"])
            self.assertTrue(plot["figure"]["data"])
            self.assertTrue(plot["sample_note"])

    def test_four_real_models_random_fill_and_predictions(self):
        bundle = self.service.bundle
        self.assertEqual(len(bundle["models"]), 4)
        for card in self.service.study["models"]:
            for seed in [0, 10, 101]:
                sample = self.service.random_fill(card["id"], seed)
                position = sample["reference_position"]
                original = bundle["reference_inputs"].iloc[position]
                self.assertEqual(sample["features"], {name: int(value) for name, value in original.items()})
                result = self.service.predict(card["id"], sample["features"])
                self.assertEqual(result["target"], int(bundle["reference_predictions"][card["id"]][position]))
                self.assertEqual(result["prediction"], "Phishing" if result["target"] == 1 else "Legitimate")
                self.assertAlmostEqual(result["phishing_probability"] + result["legitimate_probability"], 1)
                self.assertTrue(result["explanation"])

    def test_invalid_features_and_missing_dependencies_are_clear(self):
        sample = self.service.random_fill("logistic_regression", 1)["features"]
        for bad in [{}, {**sample, "unknown": 1}, {**sample, "NoOfJS": -1},
                    {**sample, "IsHTTPS": 2}, {**sample, "URLLength": float("nan")},
                    {**sample, "URLLength": 13, "DomainLength": 110}]:
            with self.assertRaises(InputError):
                self.service.predict("logistic_regression", bad)
        with self.assertRaises(InputError):
            self.service.random_fill("unrelated model")
        with self.assertRaises(InputError):
            self.service.schema([])
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SnapshotError):
                StudyService(artifacts=Path(directory))

    def test_preview_pagination_and_literal_search(self):
        first, total = self.service.preview(1, 25)
        second, total2 = self.service.preview(2, 25)
        self.assertEqual(total, total2)
        self.assertEqual(len(first), 25)
        self.assertTrue(set(first.FILENAME).isdisjoint(second.FILENAME))
        matched, count = self.service.preview(1, 25, label=0, search=".")
        self.assertTrue(matched.label.eq(0).all())
        self.assertGreater(count, 0)


class TeamPersistenceTests(unittest.TestCase):
    def test_four_neutral_profiles_upload_replace_remove_and_persist(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "team.sqlite3"
            people = team.members(path)
            self.assertEqual(len(people), 4)
            self.assertTrue(all(person["name"] == "" and person["photo"] is None for person in people))
            image = io.BytesIO()
            Image.new("RGB", (120, 160), "#cad1c5").save(image, format="PNG")
            for member_id in range(1, 5):
                saved = team.save_member(member_id, f"QA member {member_id}", "QA", "Testing", image.getvalue(), path=path)
                self.assertTrue(saved["photo"].startswith(b"\xff\xd8"))
            self.assertEqual(team.members(path)[3]["name"], "QA member 4")
            replacement = io.BytesIO()
            Image.new("RGB", (100, 140), "#173b3a").save(replacement, format="JPEG")
            previous = team.members(path)[0]["photo"]
            changed = team.save_member(1, "QA member 1", photo=replacement.getvalue(), path=path)
            self.assertNotEqual(previous, changed["photo"])
            cleared = team.save_member(1, "QA member 1", remove_photo=True, path=path)
            self.assertIsNone(cleared["photo"])
            with self.assertRaises(ValueError):
                team.save_member(1, "QA", photo=b"not an image", path=path)


class BackendIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("phisheries_api", ROOT / "backend/server.py")
        cls.api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.api)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), cls.api.AnalysisHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def get(self, path):
        with urlopen(self.base + path, timeout=20) as response:
            return json.load(response)

    def test_bi_exports_and_notebook_endpoints(self):
        self.assertEqual(self.get("/health")["status"], "ready")
        self.assertEqual(len(self.get("/api/evidence")), 15)
        self.assertEqual(len(self.get("/api/questions")), 15)
        self.assertEqual(len(self.get("/api/eda")), 12)
        self.assertEqual(len(self.get("/api/models")["models"]), 4)
        for endpoint, path in self.api.csv_paths.items():
            with urlopen(self.base + endpoint, timeout=20) as response:
                self.assertEqual(response.read(), path.read_bytes())
        for endpoint in ["/api/questions/999", "/data/../../README.md"]:
            with self.assertRaises(HTTPError) as result:
                self.get(endpoint)
            self.assertEqual(result.exception.code, 404)
            result.exception.close()

    def test_every_model_prediction_over_http(self):
        for model in self.get("/api/models")["models"]:
            sample = self.get("/api/random-fill?model=" + model["id"])
            schema = self.get("/api/feature-schema?model=" + model["id"])
            self.assertEqual(len(schema["fields"]), 11)
            payload = json.dumps({"model_id": model["id"], "features": sample["features"]}).encode()
            request = Request(self.base + "/api/predict", data=payload, headers={"Content-Type": "application/json"})
            with urlopen(request, timeout=20) as response:
                result = json.load(response)
            self.assertIn(result["prediction"], ["Phishing", "Legitimate"])
            self.assertEqual(result["model_id"], model["id"])
        invalid = Request(self.base + "/api/predict", data=b'{}', headers={"Content-Type": "application/json"})
        with self.assertRaises(HTTPError) as result:
            urlopen(invalid)
        self.assertEqual(result.exception.code, 422)
        result.exception.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
