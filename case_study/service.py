"""Read verified notebook results and run inference through the genuine models."""

from functools import lru_cache
import json
import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn

from .config import ARTIFACTS, DATASET, NOTEBOOKS, CLASS_NAMES
from .sources import fingerprint


class SnapshotError(RuntimeError):
    pass


class InputError(ValueError):
    pass


class StudyService:
    def __init__(self, artifacts=ARTIFACTS, dataset=DATASET, verify_sources=True):
        self.folder = Path(artifacts)
        self.dataset = Path(dataset)
        manifest_path = self.folder / "manifest.json"
        if not manifest_path.is_file():
            raise SnapshotError("Prepared analysis is missing. Run python -m case_study.prepare from the project folder.")
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for name in ["study.json", "questions.json", "eda.json", "sampling.json", "models.joblib"]:
            path = self.folder / name
            expected = self.manifest["files"].get(name)
            if not path.is_file() or expected != fingerprint(path):
                raise SnapshotError(f"The prepared file {name} is missing or inconsistent. Rebuild the verified snapshot.")
        if verify_sources:
            for key, entry in self.manifest["notebooks"].items():
                path = NOTEBOOKS[key]
                if not path.is_file() or fingerprint(path) != entry["sha256"]:
                    raise SnapshotError(f"{path.name} changed after preparation. Rebuild before displaying its results.")
            if not self.dataset.is_file():
                raise SnapshotError(f"The PhiUSIIL dataset is missing: {self.dataset}")
            if fingerprint(self.dataset) != self.manifest["dataset_sha256"]:
                raise SnapshotError("The dataset differs from the verified snapshot. Rebuild rather than mixing results.")
        self.study = self.read_json("study.json")
        self.questions = self.read_json("questions.json")
        self.eda = self.read_json("eda.json")
        self.sampling = self.read_json("sampling.json")
        self._models = None
        self._raw = None

    def read_json(self, name):
        return json.loads((self.folder / name).read_text(encoding="utf-8"))

    @property
    def bundle(self):
        if self._models is None:
            if self.manifest["environment"]["scikit_learn"] != sklearn.__version__:
                raise SnapshotError("The scikit-learn version differs from the fitted artifacts. Run preparation in this environment.")
            path = self.folder / "models.joblib"
            if fingerprint(path) != self.manifest["files"]["models.joblib"]:
                raise SnapshotError("Model artifacts changed after verification. Rebuild the snapshot.")
            self._models = joblib.load(path)
        return self._models

    @property
    def raw(self):
        if self._raw is None:
            self._raw = pd.read_csv(self.dataset)
        return self._raw

    def question(self, number):
        return next((q for q in self.questions if q["number"] == int(number)), None)

    def schema(self, model_id):
        if not isinstance(model_id, str) or model_id not in {m["id"] for m in self.study["models"]}:
            raise InputError("Choose one of the four models from the notebook.")
        return self.study["schema"]

    def random_fill(self, model_id, seed=None):
        self.schema(model_id)
        random = np.random.default_rng(seed)
        rows = self.bundle["reference_inputs"]
        position = int(random.integers(0, len(rows)))
        values = {key: int(value) for key, value in rows.iloc[position].to_dict().items()}
        return {"model_id": model_id, "features": values, "source": "One real held-out PhiUSIIL row",
                "reference_position": position}

    def validate(self, model_id, values):
        schema = self.schema(model_id)
        if not isinstance(values, dict):
            raise InputError("Features must be an object with the named model inputs.")
        required = {field["name"] for field in schema}
        if set(values) != required:
            missing, extra = sorted(required - set(values)), sorted(set(values) - required)
            raise InputError(f"Input schema mismatch. Missing: {missing or 'none'}; unknown: {extra or 'none'}.")
        valid = {}
        for field in schema:
            name = field["name"]
            value = values[name]
            if isinstance(value, bool):
                value = int(value)
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise InputError(f"{name} must be a finite number.")
            if value != int(value):
                raise InputError(f"{name} must be a whole number.")
            if not field["minimum"] <= value <= field["maximum"]:
                raise InputError(f"{name} must be between {field['minimum']} and {field['maximum']} (observed dataset range).")
            if field["kind"] == "binary" and value not in [0, 1]:
                raise InputError(f"{name} must be 0 or 1.")
            valid[name] = int(value)
        if self.bundle["domain_length_constraint"] and valid["DomainLength"] > valid["URLLength"]:
            raise InputError("Domain length cannot exceed the full URL length in this dataset's input schema.")
        return valid

    def predict(self, model_id, values):
        valid = self.validate(model_id, values)
        frame = pd.DataFrame([valid], columns=self.bundle["features"], dtype=float)
        prepared = frame.copy()
        if model_id in {"naive_bayes", "logistic_regression"}:
            columns = self.bundle["count_predictors"]
            prepared[columns] = (np.log1p(prepared[columns]) - self.bundle["training_means"]) / self.bundle["training_spreads"]
        model = self.bundle["models"][model_id]
        label = int(model.predict(prepared)[0])
        probabilities = model.predict_proba(prepared)[0]
        probability = float(probabilities[list(model.classes_).index(1)])
        explanation = []
        if model_id == "logistic_regression":
            contributions = prepared.iloc[0].to_numpy() * model.coef_[0]
            order = np.argsort(np.abs(contributions))[::-1][:3]
            explanation = [f"{self.bundle['features'][index]} contributes {contributions[index]:+.3f} to modeled log-odds relative to the intercept."
                           for index in order]
        elif model_id in {"pruned_tree", "full_tree"}:
            nodes = model.decision_path(prepared).indices
            for node in nodes:
                feature_index = model.tree_.feature[node]
                if feature_index >= 0:
                    feature = self.bundle["features"][feature_index]
                    cutoff = float(model.tree_.threshold[node])
                    relation = "≤" if prepared.iloc[0, feature_index] <= cutoff else ">"
                    explanation.append(f"{feature} = {valid[feature]} {relation} {cutoff:.3g}")
            explanation = explanation[:6]
        else:
            explanation = ["Gaussian Naive Bayes combines class-conditional Gaussian likelihoods for the notebook's transformed feature vector.",
                           "The probability depends on its conditional-independence and distribution assumptions."]
        return {"model_id": model_id, "target": label, "prediction": CLASS_NAMES[label],
                "phishing_probability": probability, "legitimate_probability": 1 - probability,
                "features": valid, "explanation": explanation,
                "scope": "Feature-vector prediction from the fitted benchmark model; no website was fetched and no operational safety is guaranteed."}

    def preview(self, page=1, page_size=25, label=None, search=""):
        if not 1 <= int(page_size) <= 200 or int(page) < 1:
            raise InputError("Choose a positive page number and between 1 and 200 rows per page.")
        data = self.raw
        if label is not None:
            data = data.loc[data.label == int(label)]
        if search:
            mask = data.URL.str.contains(str(search), case=False, regex=False, na=False)
            mask |= data.Domain.str.contains(str(search), case=False, regex=False, na=False)
            data = data.loc[mask]
        count = len(data)
        start = (int(page) - 1) * int(page_size)
        return data.iloc[start:start + int(page_size)].copy(), count


def snapshot_signature():
    paths = [ARTIFACTS / "manifest.json", DATASET, *NOTEBOOKS.values()]
    return tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) if p.is_file() else (str(p), 0, 0) for p in paths)


@lru_cache(maxsize=2)
def get_service(signature=None):
    return StudyService()
