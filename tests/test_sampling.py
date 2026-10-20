import json
import math
import unittest
from urllib.parse import urlsplit

import numpy as np
import pandas as pd
from scipy import integrate, special, stats

from case_study.config import ARTIFACTS, NOTEBOOKS
from case_study.service import StudyService
from case_study.sources import read_notebook
from case_study.statistics import probability_details, verdict_text


class SamplingEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = StudyService()

    def test_selection_is_reproducible_and_primary_results_are_preserved(self):
        source = read_notebook(NOTEBOOKS["analysis"])
        namespace = {
            "raw_websites": self.service.raw, "random_seed": 42,
            "class_names": {0: "Phishing", 1: "Legitimate"}, "class_order": ["Phishing", "Legitimate"],
            "missing_values": self.service.raw.isna().sum(), "pd": pd, "display": lambda *args: None,
            "read_host": lambda url: (urlsplit(str(url)).hostname or "").lower().rstrip("."),
        }
        exec(source["cells"][9]["source"], namespace)
        frame = namespace["host_sample"]
        expected = frame.sample(n=10000, replace=False, random_state=42)
        membership = pd.read_csv(ARTIFACTS / "bi/sampling_membership.csv")
        self.assertEqual(expected.Host.tolist(), membership.Host.tolist())
        self.assertEqual(membership.Host.nunique(), 10000)
        self.assertEqual(membership.label.value_counts().to_dict(), {1: 6115, 0: 3885})
        saved = pd.read_csv(ARTIFACTS / "reference_before_sampling/statistical_evidence.csv")
        prior_questions = json.loads((ARTIFACTS / "reference_before_sampling/questions.json").read_text(encoding="utf-8"))
        self.assertEqual([q["heading"] for q in prior_questions], [q["heading"] for q in self.service.questions])
        for question in self.service.questions:
            original = saved.loc[saved.Question == question["number"]].iloc[0]
            self.assertAlmostEqual(question["test"]["Statistic"], original.Statistic, places=8)
            self.assertAlmostEqual(question["test"]["Estimate"], original.Estimate, places=10)
            self.assertEqual(question["test"]["Decision"], original.Decision)
        q1 = self.service.question(1)["comparison"][1]
        actual = stats.ttest_ind(expected.loc[expected.label == 0, "URLLength"],
                                 expected.loc[expected.label == 1, "URLLength"], equal_var=False)
        self.assertAlmostEqual(q1["Statistic"], actual.statistic, places=10)
        self.assertAlmostEqual(q1["Log10PValue"], math.log10(actual.pvalue), places=10)

    def test_all_questions_have_valid_scopes_probabilities_and_figures(self):
        self.assertEqual(len(self.service.sampling["rows"]), 30)
        for question in self.service.questions:
            reference, sample = question["comparison"]
            self.assertEqual(sample["Question"], question["number"])
            self.assertEqual(reference["Test"], sample["Test"])
            self.assertEqual(sample["N"], 3885 if question["number"] == 12 else 10000)
            self.assertEqual(reference["N"], 3000 if question["number"] in [13, 14] else 85227 if question["number"] == 12 else 220023)
            if sample["MinimumExpectedCount"] is not None:
                self.assertGreaterEqual(sample["MinimumExpectedCount"], 5)
            for row in [reference, sample]:
                self.assertRegex(row["PValueDisplay"], r"^\d\.\d+e[+-]\d+$")
                self.assertTrue(math.isfinite(row["Log10PValue"]))
                self.assertIn("not the probability that H0 is true", row["Verdict"])
            if question["number"] in [13, 14]:
                self.assertEqual(sample["PValue"], (sample["ExtremeShuffles"] + 1) / 2000)
        notebook = read_notebook(NOTEBOOKS["analysis"])
        self.assertFalse([output for cell in notebook["cells"] for output in cell.get("outputs", []) if output["output_type"] == "error"])
        figures = [output for cell in notebook["cells"] if cell.get("metadata", {}).get("sampling_comparison")
                   for output in cell.get("outputs", []) if "image/png" in output.get("data", {})]
        self.assertEqual(len(figures), 15)

    def test_underflow_tails_against_independent_probability_formulas(self):
        q1 = self.service.question(1)["test"]
        degrees, magnitude = q1["DegreesOfFreedom"], abs(q1["Statistic"])
        # The t tail also equals a regularized incomplete beta integral.
        a = degrees / 2
        x = degrees / (degrees + magnitude**2)
        integral, _ = integrate.quad(lambda z: math.exp(-z) * math.sqrt((1 - x) / (1 - x * math.exp(-z / a))), 0, math.inf)
        log_p = a * math.log(x) - math.log(a) - special.betaln(a, 0.5) - 0.5 * math.log1p(-x) + math.log(integral)
        self.assertAlmostEqual(q1["Log10PValue"], log_p / math.log(10), places=7)
        for number in [4, 5, 6, 7, 8, 9, 10]:
            result = self.service.question(number)["test"]
            expected = (math.log(2) + stats.norm.logsf(math.sqrt(result["Statistic"]))) / math.log(10)
            self.assertAlmostEqual(result["Log10PValue"], expected, places=7)
        q11 = self.service.question(11)["test"]
        half_statistic = q11["Statistic"] / 2
        expected = (-half_statistic + special.logsumexp([k * math.log(half_statistic) - math.lgamma(k + 1) for k in range(5)])) / math.log(10)
        self.assertAlmostEqual(q11["Log10PValue"], expected, places=7)
        ordinary = probability_details("Two-sample t-test", 2.5, 0, 50)
        self.assertAlmostEqual(ordinary["Log10PValue"], math.log10(2 * stats.t.sf(2.5, 50)), places=9)

    def test_failure_to_reject_is_explained_without_accepting_the_null(self):
        result = {"alpha": 0.05, **probability_details("Paired t-test", 0.5, 0.62, 100)}
        text = verdict_text(15, result)
        self.assertIn("Fail to reject H0", text)
        self.assertIn("does not establish equality or prove H0", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
