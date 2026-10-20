"""Readable probabilities and decisions for the notebook's existing tests."""

import math

from scipy import integrate, stats


def probability_details(test_name, statistic, p_value, degrees=None):
    """Keep tiny probabilities as log10 values when ordinary floats underflow."""
    if p_value > 0:
        log_probability = math.log(p_value)
        calculation = "SciPy probability from the original test"
    elif "t-test" in test_name:
        magnitude = abs(float(statistic))
        degrees = float(degrees)
        scale = (degrees + magnitude**2) / ((degrees + 1) * magnitude)

        def relative_density(distance):
            extra = scale * distance
            ratio = (2 * magnitude * extra + extra**2) / (degrees + magnitude**2)
            return math.exp(-0.5 * (degrees + 1) * math.log1p(ratio))

        area, _ = integrate.quad(relative_density, 0, math.inf, epsabs=1e-12, epsrel=1e-11)
        log_probability = math.log(2) + stats.t.logpdf(magnitude, degrees) + math.log(scale * area)
        calculation = "Two-sided t tail, integrated after scaling the density to avoid float underflow"
    elif "Chi-square" in test_name:
        value = float(statistic)
        shape = float(degrees) / 2
        scale = 1 / (0.5 - (shape - 1) / value)

        def relative_density(distance):
            extra = scale * distance
            return math.exp((shape - 1) * math.log1p(extra / value) - extra / 2)

        area, _ = integrate.quad(relative_density, 0, math.inf, epsabs=1e-12, epsrel=1e-11)
        log_probability = stats.chi2.logpdf(value, degrees) + math.log(scale * area)
        calculation = "Right chi-square tail, integrated after scaling the density to avoid float underflow"
    else:
        raise ValueError("A permutation p-value must include the observed arrangement and cannot be zero.")

    log10_probability = float(log_probability / math.log(10))
    exponent = math.floor(log10_probability)
    coefficient = 10 ** (log10_probability - exponent)
    display = f"{coefficient:.6f}e{exponent:+d}"
    return {"PValueDisplay": display, "Log10PValue": log10_probability,
            "PValueCalculation": calculation, "FloatUnderflow": bool(p_value == 0)}


def verdict_text(number, result):
    """Explain the statistical decision without turning evidence into proof."""
    alpha = result.get("alpha", 0.05)
    rejected = result["Log10PValue"] <= math.log10(alpha)
    relation = "≤" if rejected else ">"
    decision = "Reject H0" if rejected else "Fail to reject H0"
    topics = {
        1: "a difference in mean URL length between the recorded classes",
        2: "a difference in mean domain length between the recorded classes",
        3: "a difference in mean subdomain count between the recorded classes",
        4: "an association between HTTPS use and recorded class",
        5: "an association between favicon presence and recorded class",
        6: "an association between social-link presence and recorded class",
        7: "an association between external form submission and recorded class",
        8: "an association between the Bank keyword and recorded class",
        9: "an association between the Pay keyword and recorded class",
        10: "an association between the Crypto keyword and recorded class",
        11: "an association between the fixed TLD groups and recorded class",
        12: "a nonzero mean paired title-score difference on phishing hosts",
        13: "a distribution difference detected by the image-count median gap under exchangeable labels",
        14: "a distribution difference detected by the JavaScript-count median gap under exchangeable labels",
        15: "a nonzero mean correctness difference between Rule B and Rule A",
    }
    evidence = "sufficient evidence for" if rejected else "insufficient evidence for"
    text = (f"p ≈ {result['PValueDisplay']} {relation} α = {alpha:.2f}. {decision}: "
            f"this analysis provides {evidence} {topics[number]}, subject to the test assumptions. ")
    if rejected:
        text += "If H0 and the assumptions held, a test statistic at least this extreme would be unusual. "
    else:
        text += "The data do not distinguish the observed result strongly enough from H0 at this threshold. Failing to reject does not establish equality or prove H0. "
    text += "The p-value is not the probability that H0 is true. Check the effect size before deciding whether the finding matters."
    return text
