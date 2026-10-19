from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
DATASET = Path(os.environ.get("PHIUSIIL_DATASET", ROOT / "PhiUSIIL_Phishing_URL_Dataset.csv"))
ARTIFACTS = ROOT / "artifacts"
NOTEBOOKS = {
    "analysis": ROOT / "Department_Of_Phisheries.ipynb",
    "eda": ROOT / "Plots.ipynb",
    "models": ROOT / "Model_Evaluation.ipynb",
}
TEAM_DATABASE = ROOT / "data" / "team.sqlite3"
CLASS_NAMES = {0: "Legitimate", 1: "Phishing"}  # Model target, not the CSV label.
MODEL_IDS = {"Gaussian Naive Bayes": "naive_bayes", "Decision Tree (max_depth=5)": "pruned_tree",
             "Logistic regression": "logistic_regression", "Decision Tree (full)": "full_tree"}
