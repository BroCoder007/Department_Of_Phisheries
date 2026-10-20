"""Repeat the fifteen course tests on one reproducible sample of hosts."""

import hashlib
import math

import numpy as np
import pandas as pd
from scipy import stats

from .statistics import probability_details, verdict_text


SAMPLE_SIZE = 10000
SAMPLE_SEED = 42
BINARY_FEATURES = ["IsHTTPS", "HasFavicon", "HasSocialNet", "HasExternalFormSubmit", "Bank", "Pay", "Crypto"]
COURSE_REFERENCES = [
    {"file": "L11-Sampling and Emprical distribution.pptx", "slides": "21–23, 25, 34–38",
     "use": "Simple random sampling without replacement, selection mechanism, sample size and sampling variability."},
    {"file": "L12-Hypothesis testing and Error probabilities.pptx", "slides": "20–22, 39, 42, 47–54",
     "use": "P-value meaning, alpha decision, failure to reject and permutation comparisons."},
    {"file": "L13-Statistical Testing and comparing model.pptx", "slides": "20–24, 30–31, 40–41, 44, 50–55",
     "use": "Chi-square independence, Welch and paired t tests, assumptions and practical significance."},
    {"file": "L14-Causation and Experiment.pptx", "slides": "25",
     "use": "A p-value alone does not prove causality. Randomly sampling hosts is not randomly assigning a treatment."},
]


def analyse_sample(hosts, original, common_tlds, alpha=0.05):
    """Use the same question, feature, direction and test as the original row."""
    number = original["Question"]
    feature = original["Feature"]
    phishing = hosts.loc[hosts.label == 0]
    legitimate = hosts.loc[hosts.label == 1]
    result = {key: original[key] for key in ["Question", "Feature", "Test", "EstimateUnits"]}
    result.update({"Analysis": "Random sample", "Scope": "Shared simple random sample of eligible hosts",
                   "alpha": alpha, "N": len(hosts), "PhishingHosts": len(phishing),
                   "LegitimateHosts": len(legitimate), "MinimumExpectedCount": None,
                   "StandardizedEffect": None, "StandardizedEffectName": None})
    degrees = None

    if number <= 3:
        first, second = phishing[feature], legitimate[feature]
        test = stats.ttest_ind(first, second, equal_var=False)
        statistic, p_value, degrees = test.statistic, test.pvalue, test.df
        estimate = float(first.mean() - second.mean())
        pooled_sd = math.sqrt(((len(first) - 1) * first.var(ddof=1) + (len(second) - 1) * second.var(ddof=1)) / (len(hosts) - 2))
        result.update({"StandardizedEffect": estimate / pooled_sd,
                       "StandardizedEffectName": "Mean gap / pooled sample SD (descriptive Cohen d)",
                       "PhishingMean": float(first.mean()), "LegitimateMean": float(second.mean()),
                       "PhishingVariance": float(first.var(ddof=1)), "LegitimateVariance": float(second.var(ddof=1))})
    elif number <= 11:
        if number <= 10:
            observed = pd.crosstab(hosts.label, hosts[feature]).reindex(index=[0, 1], columns=[0, 1], fill_value=0)
            rates = observed[1] / observed.sum(axis=1)
            estimate = float(100 * (rates.loc[0] - rates.loc[1]))
        else:
            groups = hosts.TLD.where(hosts.TLD.isin(common_tlds), "Other")
            observed = pd.crosstab(groups, hosts.label).reindex(columns=[0, 1], fill_value=0)
        statistic, p_value, degrees, expected = stats.chi2_contingency(observed, correction=False)
        if number == 11:
            estimate = float(statistic)
        result.update({"MinimumExpectedCount": float(expected.min()),
                       "StandardizedEffect": math.sqrt(statistic / (len(hosts) * min(observed.shape[0] - 1, observed.shape[1] - 1))),
                       "StandardizedEffectName": "Cramer V", "Observed": observed.values.tolist()})
    elif number == 12:
        first, second = phishing.URLTitleMatchScore, phishing.DomainTitleMatchScore
        differences = first - second
        test = stats.ttest_rel(first, second)
        statistic, p_value, degrees = test.statistic, test.pvalue, test.df
        estimate = float(differences.mean())
        result.update({"N": len(phishing), "LegitimateHosts": 0,
                       "Scope": "Phishing hosts within the shared sample, preserving both scores per host",
                       "StandardizedEffect": estimate / differences.std(ddof=1),
                       "StandardizedEffectName": "Mean paired gap / SD of paired gaps (descriptive dz)"})
    elif number in [13, 14]:
        first = phishing[feature].to_numpy()
        second = legitimate[feature].to_numpy()
        estimate = float(np.median(first) - np.median(second))
        pooled = np.concatenate([first, second])
        random = np.random.default_rng(SAMPLE_SEED + number)
        shuffled_gaps = np.empty(1999)
        for repetition in range(len(shuffled_gaps)):
            shuffled = random.permutation(pooled)
            shuffled_gaps[repetition] = np.median(shuffled[:len(first)]) - np.median(shuffled[len(first):])
        extreme = int(np.sum(np.abs(shuffled_gaps) >= abs(estimate)))
        statistic, p_value = estimate, (extreme + 1) / 2000
        result.update({"Shuffles": 1999, "ExtremeShuffles": extreme,
                       "PhishingMedian": float(np.median(first)), "LegitimateMedian": float(np.median(second))})
    else:
        actual = hosts.IsPhishing.to_numpy()
        rule_a = hosts.IsHTTPS.eq(0).to_numpy()
        rule_b = (hosts.IsHTTPS.eq(0) & hosts.HasSocialNet.eq(0)).to_numpy()
        a_correct, b_correct = (rule_a == actual).astype(int), (rule_b == actual).astype(int)
        differences = b_correct - a_correct
        test = stats.ttest_rel(b_correct, a_correct)
        statistic, p_value, degrees = test.statistic, test.pvalue, test.df
        estimate = float(100 * differences.mean())
        result.update({"StandardizedEffect": float(differences.mean() / differences.std(ddof=1)),
                       "StandardizedEffectName": "Mean paired gap / SD of paired gaps (descriptive dz)",
                       "OnlyACorrect": int(((a_correct == 1) & (b_correct == 0)).sum()),
                       "OnlyBCorrect": int(((a_correct == 0) & (b_correct == 1)).sum()),
                       "ExtraMissedPhishing": int(((rule_a & ~rule_b) & (actual == 1)).sum()),
                       "AvoidedFalseAlerts": int(((rule_a & ~rule_b) & (actual == 0)).sum())})

    result.update({"Statistic": float(statistic), "PValue": float(p_value),
                   "DegreesOfFreedom": None if degrees is None else float(degrees), "Estimate": estimate})
    result.update(probability_details(result["Test"], statistic, p_value, degrees))
    result["Decision"] = "Reject H0" if result["Log10PValue"] <= math.log10(alpha) else "Fail to reject H0"
    result["Verdict"] = verdict_text(number, result)
    minimum = result["MinimumExpectedCount"]
    result["AssumptionNote"] = ("Expected count below 5: chi-square approximation is unreliable; treat the decision cautiously."
                                if minimum is not None and minimum < 5 else "No expected-count failure detected where applicable.")
    if number == 15:
        result["PracticalInterpretation"] = f"B changes accuracy by {estimate:.4f} percentage points, misses {result['ExtraMissedPhishing']} additional phishing hosts and avoids {result['AvoidedFalseAlerts']} false alerts in these selected hosts."
    elif number == 11:
        result["PracticalInterpretation"] = f"Association strength Cramer V = {result['StandardizedEffect']:.4f}; the chi-square statistic depends strongly on sample size. No individual TLD pair is tested."
    else:
        result["PracticalInterpretation"] = f"Observed effect = {estimate:.4f} {result['EstimateUnits']}. Consider this magnitude and the overlapping observations before recommending any rule."
    return result


def sampling_comparison(host_frame, original_rows, alpha=0.05):
    """Sample once, then repeat all fifteen original analyses on that sample."""
    selected = host_frame.sample(n=SAMPLE_SIZE, replace=False, random_state=SAMPLE_SEED).copy()
    common_tlds = host_frame.TLD.value_counts().head(10).index
    comparison = []
    for original in original_rows:
        number = original["Question"]
        reference = dict(original, Analysis="Original notebook", alpha=alpha)
        reference.update(probability_details(reference["Test"], reference["Statistic"], reference["PValue"], reference.get("DegreesOfFreedom")))
        reference["N"] = (int((host_frame.label == 0).sum()) if number == 12 else 3000 if number in [13, 14] else len(host_frame))
        if number == 11:
            reference["StandardizedEffect"] = math.sqrt(reference["Statistic"] / reference["N"])
            reference["StandardizedEffectName"] = "Cramer V"
        reference["Verdict"] = verdict_text(number, reference)
        sample = analyse_sample(selected, original, common_tlds, alpha)
        sample["DecisionMatchesReference"] = sample["Decision"] == reference["Decision"]
        sample["EstimateDifference"] = sample["Estimate"] - reference["Estimate"]
        comparison.extend([reference, sample])

    composition = []
    for label, name in [(0, "Phishing"), (1, "Legitimate")]:
        population_count = int((host_frame.label == label).sum())
        sample_count = int((selected.label == label).sum())
        composition.append({"Class": name, "EligibleHosts": population_count, "SampledHosts": sample_count,
                            "EligibleShare": population_count / len(host_frame), "SampleShare": sample_count / len(selected)})
    membership = selected[["Host", "FILENAME", "label"]].copy()
    digest = hashlib.sha256("\n".join(sorted(selected.Host)).encode()).hexdigest()
    design = {
        "method": "Simple random sampling without replacement", "seed": SAMPLE_SEED,
        "sample_size": len(selected), "population_hosts": len(host_frame),
        "sampling_fraction": len(selected) / len(host_frame), "host_membership_sha256": digest,
        "composition": composition, "course_references": COURSE_REFERENCES,
        "reason": "10,000 hosts give several thousand observations per recorded class while using under 5% of the eligible host frame. This provides a manageable common sample for all questions. The size was fixed before comparing p-values; it is a teaching sensitivity analysis, not a formal power calculation or an optimal size prescribed by the slides.",
        "selection": "pandas sample(n=10000, replace=False, random_state=42), applied once to the existing one-URL-per-consistent-host frame. Every host has inclusion probability 10000/N. Selection does not balance classes or depend on feature values or p-values.",
        "scope": "The population frame is the 220,023 eligible exact hosts in this benchmark. It is not all websites on the internet. The original frame covers every eligible host, with one randomly selected URL per host; it is not a random subset of those hosts.",
        "limitations": "The sample is nested in the reference frame, so agreement is a sensitivity check, not independent replication. Sampling cannot repair source collection bias, campaign dependence or multiple exploratory testing. Reference p-values are retained as the original superpopulation-model calculations; finite benchmark population differences can instead be described directly. Conventional tests are repeated without a finite-population correction to preserve the original methods; the sample fraction is below 5%.",
        "pairing": "Q12 uses only phishing hosts within the common sample and keeps the two scores paired. Q15 keeps both rule outcomes per selected host. Q11 fixes the original ten TLD groups plus Other. Q13–Q14 keep their original 3,000-host reference and repeat the same 1,999-shuffle tests using the class counts observed in the shared 10,000-host sample.",
        "p_values": "Scientific-notation tail probabilities are numerical approximations. Underflowed t/chi-square tails are computed on a scaled log scale, preserving the same statistic and distribution. Permutation p-values remain (extreme + 1)/2000, with minimum 0.0005; this resolution is not improved by scientific notation.",
        "agreement_count": sum(row.get("DecisionMatchesReference", False) for row in comparison),
    }
    return {"design": design, "rows": comparison, "membership": membership}
