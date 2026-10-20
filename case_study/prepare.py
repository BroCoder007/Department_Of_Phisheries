"""Reproduce trusted local notebooks and persist a verified application snapshot.

Run from the project: python -m case_study.prepare
The original three .ipynb files are never edited.
"""

from contextlib import redirect_stdout
from datetime import datetime, timezone
import gc
import io
import json
import os
from pathlib import Path
import platform
import re
import shutil
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.metrics import roc_auc_score, roc_curve

from .config import ROOT, DATASET, ARTIFACTS, NOTEBOOKS, MODEL_IDS
from .sources import (fingerprint, read_notebook, save_original_figures, questions_from_notebook,
                      plots_from_notebook, stored_tables, CORRECTIONS)
from .charts import question_chart, eda_chart, SELECTED_PLOTS, pack, style


def safe_json(value):
    if isinstance(value, dict):
        return {str(k): safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [safe_json(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(safe_json(value), ensure_ascii=False, allow_nan=False, indent=2), encoding="utf-8")


def records(frame):
    return safe_json(frame.to_dict(orient="records"))


def execute(cell, namespace, index, log):
    displayed = []
    namespace["display"] = lambda value: displayed.append(value.copy() if isinstance(value, pd.DataFrame) else str(value))
    stream = io.StringIO()
    with redirect_stdout(stream):
        exec(compile(cell["source"], f"{namespace['__source__']}:cell-{index}", "exec"), namespace)
    log.append({"cell": index, "stdout": stream.getvalue(),
                "tables": [records(table) for table in displayed if isinstance(table, pd.DataFrame)]})


def question_details(number, ns):
    row = ns["test_results"][-1].copy()
    row["alpha"] = float(ns["alpha"])
    details = {"test": row, "figure": question_chart(number, ns), "tables": [], "columns": []}
    if number <= 3:
        row["DegreesOfFreedom"] = float(ns["test"].df)
        feature = row["Feature"]
        details["columns"] = [feature, "label", "URL / parsed Host for grouping"]
        for name, values in [("Phishing", ns["phishing_values"]), ("Legitimate", ns["legitimate_values"])]:
            details["tables"].append({"Class": name, "Hosts": len(values), "Mean": float(values.mean()),
                                      "Median": float(values.median()), "SD": float(values.std(ddof=1))})
        details["method"] = "Independent two-sample t-test with equal_var=False (the Welch version), comparing phishing minus legitimate means."
        details["interpretation"] = f"The mean gap is {row['Estimate']:.3f} {row['EstimateUnits']}. The test supplies evidence of a mean difference within this benchmark. The distributions overlap, so this does not establish an individual blocking rule."
        if number == 3:
            details["interpretation"] += " Most hosts have one recorded subdomain; the small average gap illustrates statistical versus practical significance."
    elif number <= 10:
        row["DegreesOfFreedom"] = int(ns["degrees_of_freedom"])
        row["MinimumExpectedCount"] = float(ns["expected"].min())
        observed = ns["observed"]
        details["columns"] = [row["Feature"], "label", "Host"]
        details["tables"] = [{"Class": name, "Absent": int(observed.loc[label, 0]),
                               "Present": int(observed.loc[label, 1]), "Hosts": int(observed.loc[label].sum()),
                               "PresenceRate": float(ns["presence_rates"].loc[label])}
                              for label, name in [(0, "Phishing"), (1, "Legitimate")]]
        details["expected_counts"] = np.asarray(ns["expected"]).tolist()
        details["method"] = "Chi-square independence on a class-by-feature contingency table, correction=False. Expected cell counts are checked against 5."
        details["interpretation"] = f"Presence differs by {row['Estimate']:.2f} percentage points (phishing minus legitimate). The feature is more common in legitimate hosts in this collection. Association does not identify its cause or validate a standalone security rule."
    elif number == 11:
        row["DegreesOfFreedom"] = int(ns["degrees_of_freedom"])
        row["MinimumExpectedCount"] = float(ns["expected"].min())
        details["columns"] = ["TLD", "label", "Host"]
        details["tables"] = records(ns["tld_summary"])
        details["method"] = "Chi-square independence for the ten most common TLDs by host count, with all remaining categories pooled as Other."
        details["interpretation"] = "Recorded class composition varies across these TLD groups. The omnibus test does not establish every pairwise difference, domain prices or universal risk for an unfamiliar TLD."
    elif number == 12:
        row["DegreesOfFreedom"] = float(ns["test"].df)
        details["columns"] = ["URLTitleMatchScore", "DomainTitleMatchScore", "label", "Host"]
        details["tables"] = [{"Paired phishing hosts": len(ns["url_scores"]),
                               "Mean URL-title score": float(ns["url_scores"].mean()),
                               "Mean domain-title score": float(ns["domain_scores"].mean()),
                               "Mean paired gap": float(ns["score_differences"].mean())}]
        details["method"] = "Paired t-test on two 0–100 scores for each phishing host. Each host contributes one difference; these are not before/after treatment measurements."
        details["interpretation"] = f"The URL-title score is higher by {row['Estimate']:.2f} points on average. This describes two supplied feature definitions, not the effect of an intervention. Their construction needs an independent provenance audit."
    elif number in [13, 14]:
        row["DegreesOfFreedom"] = None
        details["columns"] = [row["Feature"], "label", "Host"]
        details["tables"] = [{"Class": name, "Sampled hosts": len(values), "Median count": float(np.median(values))}
                              for name, values in [("Phishing", ns["phishing_counts"]), ("Legitimate", ns["legitimate_counts"])]]
        details["method"] = "Permutation test of the absolute median gap, using 1,500 hosts per class and 1,999 shuffles with the notebook's random seeds. p = (extreme + 1) / 2,000."
        details["interpretation"] = f"The observed median gap is {row['Estimate']:.1f}; its Monte Carlo p-value is {row['PValueDisplay']}. This is the simulation's resolution limit, not proof that chance is impossible. The result concerns the sampled hosts and says nothing about engineering effort or attacker intent."
        details["shuffles"] = 1999
        details["extreme_shuffles"] = int(ns["extreme_results"])
    else:
        row["DegreesOfFreedom"] = float(ns["test"].df)
        details["columns"] = ["IsHTTPS", "HasSocialNet", "IsPhishing", "Host"]
        a, b = ns["rule_a_correct"], ns["rule_b_correct"]
        details["tables"] = [{"Paired hosts": len(a), "Only A correct": int(((a == 1) & (b == 0)).sum()),
                               "Only B correct": int(((b == 1) & (a == 0)).sum()),
                               "A accuracy": float(a.mean()), "B accuracy": float(b.mean())}]
        details["method"] = "Paired t-test on 0/1 correctness for the same hosts. This uses a large-sample t approximation for discrete differences; it is not a randomized user A/B experiment."
        extra_missed = int(((a == 1) & (b == 0)).sum())
        avoided_alerts = int(((a == 0) & (b == 1)).sum())
        details["interpretation"] = f"B changes accuracy by {row['Estimate']:.3f} percentage points. It misses {extra_missed:,} additional phishing hosts and avoids {avoided_alerts:,} false alerts in this dataset. These observed errors do not certify safety for future data."
    ns["test_results"][-1].update({"DegreesOfFreedom": row["DegreesOfFreedom"]})
    details["assumptions"] = ("Eligible exact hosts are treated as independent; related subdomains and campaigns may remain dependent. Results describe a curated benchmark, and multiple exploratory questions raise false-discovery risk.")
    if number in [13, 14]:
        details["assumptions"] += " Labels must be exchangeable under the distributional null; equal medians alone do not guarantee this."
    return details


def verify_statistical_outputs(notebook, details):
    comparisons = []
    for number, detail in details.items():
        source_output = detail["saved_output"]
        match = re.search(r"Statistic = ([^,]+), p-value = ([^\n]+)", source_output)
        if not match:
            raise ValueError(f"Q{number} has no saved test output to verify against.")
        row = detail["test"]
        if not np.isclose(float(match[1]), row["Statistic"], atol=5.01e-5, rtol=0):
            raise ValueError(f"Q{number}: reproduced statistic differs from the saved notebook output.")
        if match[2].strip() != row["PValueDisplay"]:
            raise ValueError(f"Q{number}: reproduced p-value display differs from the source notebook.")
        comparisons.append({"Question": number, "SavedStatistic": float(match[1]), "ReproducedStatistic": row["Statistic"],
                            "SavedPValueDisplay": match[2].strip(), "Status": "Matches notebook rounding"})
    return comparisons


def prepare():
    missing = [str(path) for path in [DATASET, *NOTEBOOKS.values()] if not path.is_file()]
    if missing:
        raise FileNotFoundError("Required project inputs are missing: " + ", ".join(missing))
    ARTIFACTS.mkdir(exist_ok=True)
    source_hashes = {key: {"filename": path.name, "sha256": fingerprint(path)} for key, path in NOTEBOOKS.items()}
    dataset_hash = fingerprint(DATASET)
    notebooks = {key: read_notebook(path) for key, path in NOTEBOOKS.items()}
    originals = {key: save_original_figures(book, ARTIFACTS / "original" / key) for key, book in notebooks.items()}
    questions = questions_from_notebook(notebooks["analysis"], originals["analysis"])
    if len(questions) < 15:
        raise ValueError(f"The source contains {len(questions)} questions; supplemental work must be explicitly distinguished before proceeding.")
    question_map = {q["number"]: q for q in questions}
    plot_catalog = plots_from_notebook(notebooks["eda"], originals["eda"])
    print(f"Inspected {len(questions)} questions, {len(plot_catalog)} EDA figures and the full model notebook.", flush=True)

    logs = {"analysis": [], "models": []}
    ns = {"__name__": "__notebook_analysis__", "__source__": NOTEBOOKS["analysis"].name}
    original_show = plt.show
    plt.show = lambda *a, **k: plt.close()
    try:
        for index, cell in enumerate(notebooks["analysis"]["cells"]):
            if cell["cell_type"] != "code" or not cell["source"].strip():
                continue
            adapted = cell.copy()
            if "model_metric_chart =" in adapted["source"]:
                adapted["source"] = adapted["source"].split("model_metric_chart =")[0]
            execute(adapted, ns, index, logs["analysis"])
            if "figure_folder" in ns:
                ns["output_folder"] = ARTIFACTS / "analysis_outputs"
                ns["figure_folder"] = ARTIFACTS / "reproduced" / "analysis"
                ns["dashboard_folder"] = ARTIFACTS / "bi"
                for key in ["output_folder", "figure_folder", "dashboard_folder"]:
                    ns[key].mkdir(parents=True, exist_ok=True)
            if "def record_result(" in cell["source"]:
                original_record = ns["record_result"]

                def capture_result(*args, **kwargs):
                    original_record(*args, **kwargs)
                    number = int(args[0])
                    question_map[number].update(question_details(number, ns))

                ns["record_result"] = capture_result
        stat_checks = verify_statistical_outputs(notebooks["analysis"], question_map)
        raw = ns["raw_websites"]
        if Path(ns["dataset_path"]).resolve() != DATASET.resolve():
            raise ValueError("The notebook's dataset path does not match the configured PhiUSIIL dataset.")
        clean = ns["website_data"]
        hosts = ns["host_sample"]
        sampling = ns["sampling_results"]
        sampling_rows = sampling["rows"]
        for question in questions:
            number = question["number"]
            question["comparison"] = [row for row in sampling_rows if row["Question"] == number]
            question["test"]["Verdict"] = question["comparison"][0]["Verdict"]
        pd.DataFrame(sampling_rows).to_csv(ARTIFACTS / "bi/sampling_comparison.csv", index=False)
        sampling["membership"].to_csv(ARTIFACTS / "bi/sampling_membership.csv", index=False)
        write_json(ARTIFACTS / "sampling.json", {"design": sampling["design"], "rows": sampling_rows})
        raw_summary = raw.label.value_counts().sort_index()
        repeated_domains = int(raw.duplicated("Domain").sum())
        repeated_urls = int(raw.duplicated("URL").sum())
        repeated_feature_records = int(raw.drop(columns="FILENAME").duplicated().sum())
        host_url_counts = clean.Host.value_counts()
        study = {
            "title": "Department of Phisheries", "raw_rows": len(raw), "columns": len(raw.columns),
            "feature_count": len(raw.columns) - 2, "unique_urls": len(clean), "inference_hosts": len(hosts),
            "raw_class_counts": {"Phishing": int(raw_summary.loc[0]), "Legitimate": int(raw_summary.loc[1])},
            "host_class_counts": hosts.Class.value_counts().to_dict(),
            "missing_cells": int(raw.isna().sum().sum()), "repeated_url_rows": repeated_urls,
            "repeated_domain_rows": repeated_domains, "duplicate_rows_without_filename": repeated_feature_records,
            "hosts_with_multiple_urls": int(host_url_counts.gt(1).sum()),
            "source_label_mapping": {"0": "Phishing", "1": "Legitimate"},
            "model_label_mapping": {"0": "Legitimate", "1": "Phishing"},
            "quality": records(ns["quality_summary"]), "outliers": records(ns["outlier_summary"]),
            "dictionary": records(ns["data_dictionary"]), "descriptive_summary": records(ns["descriptive_summary"]),
            "structure_rates": records(ns["structure_rates"].reset_index()),
            "rule_summary": records(ns["rule_summary"]), "alpha": float(ns["alpha"]),
            "extra_missed": int(ns["extra_missed"]), "avoided_alerts": int(ns["avoided_alerts"]),
            "corrections": CORRECTIONS, "question_count": len(questions),
            "statistical_verification": stat_checks,
            "sampling_design": sampling["design"],
            "notebook_inspection": {key: {"cells": len(book["cells"]), "saved_figures": sum(len(v) for v in originals[key].values()),
                                         "code_cells": sum(c["cell_type"] == "code" for c in book["cells"])} for key, book in notebooks.items()},
        }
        clean_identity = fingerprint_table(clean[["URL", "label"]])
        eda = []
        for plot in plot_catalog:
            if plot["number"] in SELECTED_PLOTS:
                plot.update(eda_chart(plot["number"], raw))
                plot["linked_questions"] = {1: [1, 4], 3: [1, 2], 4: [13, 14], 5: [13], 6: [11],
                                            8: [12], 14: [7], 17: [1, 2, 12, 13, 14], 21: [1],
                                            22: [1], 23: [1, 2, 3], 24: [4, 5, 6, 8, 9, 10]}[plot["number"]]
                eda.append(plot)
        study["eda_selection"] = {"selected": SELECTED_PLOTS, "inspected_count": len(plot_catalog),
                                  "excluded_reason": "Redundant views and visualization-technique demonstrations are retained in the original notebook. The deliberately misleading axis and interpolated label field are not presented as substantive evidence."}
        write_json(ARTIFACTS / "questions.json", questions)
        write_json(ARTIFACTS / "eda.json", eda)
        write_json(ARTIFACTS / "plot_catalog.json", [{k: v for k, v in p.items() if k != "figure"} for p in plot_catalog])
        del raw, clean, hosts, ns
        gc.collect()

        print("Statistical results match all 15 saved notebook outputs. Training the exact model procedures...", flush=True)
        model_ns = {"__name__": "__notebook_models__", "__source__": NOTEBOOKS["models"].name}
        for index, cell in enumerate(notebooks["models"]["cells"]):
            if cell["cell_type"] == "code" and cell["source"].strip():
                execute(cell, model_ns, index, logs["models"])
                if "figure_folder" in model_ns:
                    model_ns["figure_folder"] = ARTIFACTS / "reproduced" / "models"
                    model_ns["figure_folder"].mkdir(parents=True, exist_ok=True)
        if fingerprint_table(model_ns["website_data"][["URL", "label"]]) != clean_identity:
            raise ValueError("The model and analysis notebooks do not produce the same eligible URL table.")
        reported = next(table for cell in notebooks["models"]["cells"] for table in stored_tables(cell)
                        if "Model" in table.columns and "FalseNegative" in table.columns)
        reproduced = model_ns["comparison_df"].reset_index(drop=True)
        reported = reported.reset_index(drop=True)
        if reported.Model.tolist() != reproduced.Model.tolist():
            raise ValueError("Model identities do not match the saved model notebook table.")
        numeric_columns = reproduced.columns.drop("Model")
        if not np.allclose(reported[numeric_columns].astype(float), reproduced[numeric_columns].astype(float), atol=5.01e-5, rtol=0):
            raise ValueError("Reproduced model evaluation differs from the notebook. Inspect versions and split before publishing any new scores.")
        models = {"naive_bayes": model_ns["gnb_model"], "pruned_tree": model_ns["dt_pruned"],
                  "logistic_regression": model_ns["lr_model"], "full_tree": model_ns["dt_full"]}
        features = model_ns["model_features"]
        training = model_ns["training_data"]
        test = model_ns["test_data"]
        schema = []
        for feature in features:
            values = model_ns["website_data"][feature]
            schema.append({"name": feature, "kind": "binary" if feature in model_ns["flag_predictors"] else "count",
                           "minimum": int(values.min()), "maximum": int(values.max()), "median": float(values.median())})
        prediction_rows = model_ns["X_test_tree"].reset_index(drop=True)
        bundle = {"models": models, "features": features, "count_predictors": model_ns["count_predictors"],
                  "flag_predictors": model_ns["flag_predictors"], "training_means": model_ns["training_means"],
                  "training_spreads": model_ns["training_spreads"], "reference_inputs": prediction_rows,
                  "reference_target": model_ns["y_test"],
                  "reference_predictions": {"naive_bayes": model_ns["y_pred_gnb"], "pruned_tree": model_ns["y_pred_pruned"],
                                            "logistic_regression": model_ns["y_pred_lr"], "full_tree": model_ns["y_pred_full"]},
                  "schema": schema,
                  "domain_length_constraint": bool((model_ns["website_data"].DomainLength <= model_ns["website_data"].URLLength).all())}
        joblib.dump(bundle, ARTIFACTS / "models.joblib", compress=3)
        model_cards = []
        for name, model_id in MODEL_IDS.items():
            model = models[model_id]
            inputs = model_ns["X_test_lr"] if model_id in {"naive_bayes", "logistic_regression"} else model_ns["X_test_tree"]
            probabilities = model.predict_proba(inputs)[:, list(model.classes_).index(1)]
            fpr, tpr, _ = roc_curve(model_ns["y_test"], probabilities, pos_label=1)
            metrics = reproduced.loc[reproduced.Model == name].iloc[0].to_dict()
            row = metrics
            matrix = [[int(row["TrueNegative"]), int(row["FalsePositive"])],
                      [int(row["FalseNegative"]), int(row["TruePositive"])]]
            model_cards.append({"id": model_id, "name": name, "metrics": metrics,
                                "auc": float(roc_auc_score(model_ns["y_test"], probabilities)),
                                "roc": {"fpr": fpr.tolist(), "tpr": tpr.tolist()}, "confusion": matrix,
                                "parameters": model.get_params(), "preprocessing": "log1p counts and training-only count standardization; flags unchanged" if model_id in {"naive_bayes", "logistic_regression"} else "Original float count and binary feature values; no scaling",
                                "source_cell": 7})
        host_overlap = set(training.Host) & set(test.Host)
        domain_overlap = set(training.Domain.astype(str).str.lower()) & set(test.Domain.astype(str).str.lower())
        study["models"] = model_cards
        study["model_comparison"] = records(reproduced)
        study["model_partitions"] = records(model_ns["partition_summary"])
        study["schema"] = schema
        study["feature_order"] = features
        study["model_verification"] = {"status": "Exact match to the saved comparison table at notebook precision",
                                        "train_test_host_overlap": len(host_overlap), "shared_source_domain_values": len(domain_overlap),
                                        "source_notebook": NOTEBOOKS["models"].name, "training_seed": 42,
                                        "split": "80% of unique hosts sampled into training; remaining hosts tested",
                                        "note": "The notebook heading calls the split host-stratified; the code samples hosts without class stratification. The app preserves that exact code."}
        study["model_original_figures"] = [f"original/models/{filename}" for names in originals["models"].values() for filename in names]
        study["model_code"] = "\n\n".join(c["source"] for c in notebooks["models"]["cells"] if c["cell_type"] == "code")
        study["model_source_reports"] = "\n".join(str(entry["stdout"]) for entry in logs["models"] if "CLASSIFICATION REPORT" in entry["stdout"])
        study["tree_importance"] = [{"Feature": name, "Importance": float(value)} for name, value in zip(features, models["full_tree"].feature_importances_)]
        model_summary = reproduced
        model_summary.to_csv(ARTIFACTS / "bi" / "model_summary.csv", index=False)
        model_ns["partition_summary"].to_csv(ARTIFACTS / "bi" / "model_partitions.csv", index=False)
        model_summary.melt(id_vars="Model", value_vars=["Accuracy", "BalancedAccuracy", "Precision", "Recall", "F1", "FalsePositiveRate"],
                           var_name="Metric", value_name="Score").to_csv(ARTIFACTS / "bi" / "model_metric_chart.csv", index=False)
        # Keep the existing Power BI confusion table's grain: the logistic test matrix.
        logistic = next(card for card in model_cards if card["id"] == "logistic_regression")
        pd.DataFrame([{"Actual": actual, "Predicted": predicted, "Websites": logistic["confusion"][i][j]}
                      for i, actual in enumerate(["Legitimate", "Phishing"])
                      for j, predicted in enumerate(["Legitimate", "Phishing"])]).to_csv(ARTIFACTS / "bi" / "model_confusion.csv", index=False)
        write_json(ARTIFACTS / "study.json", study)
        write_json(ARTIFACTS / "execution_log.json", logs)
        write_json(ARTIFACTS / "run_summary.json", {"dataset_sha256": dataset_hash, "raw_rows": study["raw_rows"],
                   "unique_eligible_urls": study["unique_urls"], "inference_hosts": study["inference_hosts"],
                   "test_count": len(questions), "model_count": len(models), "alpha": study["alpha"],
                   "scope": "Notebook-backed observational case study; model metrics verified against Model_Evaluation.ipynb"})
        dashboard_folder = ROOT / "outputs" / "powerbi"
        dashboard_folder.mkdir(parents=True, exist_ok=True)
        for table in (ARTIFACTS / "bi").glob("*.csv"):
            shutil.copy2(table, dashboard_folder / table.name)
        shutil.copy2(ARTIFACTS / "run_summary.json", ROOT / "outputs" / "run_summary.json")
        manifest = {"prepared_at": datetime.now(timezone.utc).isoformat(), "dataset_sha256": dataset_hash,
                    "notebooks": source_hashes,
                    "environment": {"python": platform.python_version(), "pandas": pd.__version__,
                                    "numpy": np.__version__, "scipy": scipy.__version__, "scikit_learn": sklearn.__version__},
                    "files": {path.relative_to(ARTIFACTS).as_posix(): fingerprint(path) for path in ARTIFACTS.rglob("*")
                              if path.is_file() and path.name != "manifest.json"}}
        write_json(ARTIFACTS / "manifest.json", manifest)
        print(f"Prepared verified snapshot: {len(questions)} questions, {len(eda)} selected EDA plots, {len(models)} classifiers. Original notebooks unchanged.", flush=True)
    finally:
        plt.show = original_show
        plt.close("all")
    if any(fingerprint(NOTEBOOKS[key]) != entry["sha256"] for key, entry in source_hashes.items()):
        raise RuntimeError("A source notebook changed during preparation; rebuild before serving.")


def fingerprint_table(frame):
    import hashlib
    return hashlib.sha256(pd.util.hash_pandas_object(frame, index=False).to_numpy().tobytes()).hexdigest()


if __name__ == "__main__":
    os.chdir(ROOT)
    prepare()
