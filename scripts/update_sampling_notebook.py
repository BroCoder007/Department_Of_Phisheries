"""Add the requested comparison while retaining the original question headings."""

import json
from pathlib import Path
import re
import shutil

import nbformat


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "Department_Of_Phisheries.ipynb"
BACKUP = ROOT / "artifacts" / "reference_before_sampling"


def refresh_verdict_notes(notebook):
    results_path = ROOT / "artifacts/sampling.json"
    if not results_path.is_file():
        return
    results = json.loads(results_path.read_text(encoding="utf-8"))["rows"]
    question_number = None
    for cell in notebook.cells:
        if cell.cell_type != "markdown":
            continue
        match = re.search(r"^#{1,6}\s+Q(\d+)\.", cell.source, re.M)
        if match:
            question_number = int(match[1])
        if question_number and cell.source.startswith("**What we understand from this graph**"):
            reference, sample = [row for row in results if row["Question"] == question_number]
            effect = f"{reference['Estimate']:.6g} {reference['EstimateUnits']}"
            if question_number == 11:
                effect = f"Cramer V = {reference['StandardizedEffect']:.4f} across the fixed TLD groups"
            cell.source = (f"**What we understand from this graph**\n\n"
                           f"The original analysis observes {effect}.\n\n"
                           f"{reference['Verdict']}\n\n"
                           f"The later sample comparison gives p ≈ {sample['PValueDisplay']} and "
                           f"the decision **{sample['Decision']}**. {sample['PracticalInterpretation']}\n\n"
                           "The sample is nested in the benchmark. Agreement checks sensitivity within this collection; "
                           "it does not establish independent replication, causality or guaranteed performance on new URLs.")


def update():
    BACKUP.mkdir(parents=True, exist_ok=True)
    for source in [PATH, ROOT / "artifacts/questions.json", ROOT / "artifacts/bi/statistical_evidence.csv"]:
        destination = BACKUP / source.name
        if not destination.exists():
            shutil.copy2(source, destination)

    notebook = nbformat.read(PATH, as_version=4)
    if any(cell.get("metadata", {}).get("sampling_comparison") for cell in notebook.cells):
        refresh_verdict_notes(notebook)
        nbformat.write(notebook, PATH)
        print("Refreshed the fifteen interpretation notes from the calculated comparison results.")
        return

    headings = [match[1] for cell in notebook.cells if cell.cell_type == "markdown"
                for match in [re.search(r"^#{1,6}\s+(Q\d+\.\s+.+)$", cell.source, re.M)] if match]
    notebook.cells[3].source = '''import sys

sys.path.insert(0, str(project_folder))
from case_study.statistics import probability_details, verdict_text


def show_plot(filename):
    plt.tight_layout()
    plt.savefig(figure_folder / f"{filename}.png", dpi=150, bbox_inches="tight")
    plt.show()
    plt.close()
'''
    notebook.cells[19].source = '''## 5. 15 analysis questions

We first retain the existing calculations on the eligible host benchmark. It has
one randomly selected URL for every consistently labelled exact hostname. This
represents the full eligible host frame, rather than a random subset of its hosts.
Q13 and Q14 already use smaller samples of 1,500 hosts per class.

The later sampling-comparison section repeats every question on one random sample
of 10,000 hosts. Each comparison preserves the original question and test.

The t tests compare numerical means, chi-square tests compare categorical counts,
and permutation tests compare median gaps under exchangeable labels. A small
p-value is evidence under the null model and its assumptions. It cannot establish
causation, repair collection bias, or guarantee useful detection on a new website.
'''
    notebook.cells[20].source = '''test_results = []


def record_result(question, feature, test_name, statistic, p_value, difference, units,
                  sample_note="One URL per eligible hostname"):
    degrees = None
    if "t-test" in test_name:
        degrees = float(test.df)
    elif "Chi-square" in test_name:
        degrees = int(degrees_of_freedom)

    probability = probability_details(test_name, statistic, p_value, degrees)
    decision = "Reject H0" if p_value <= alpha else "Fail to reject H0"
    result = {
        "Question": question,
        "Feature": feature,
        "Scope": sample_note,
        "Test": test_name,
        "Statistic": float(statistic),
        "PValue": float(p_value),
        "Estimate": float(difference),
        "EstimateUnits": units,
        "Decision": decision,
        "DegreesOfFreedom": degrees,
        "alpha": alpha,
        **probability,
    }
    result["Verdict"] = verdict_text(question, result)
    test_results.append(result)

    print(f"Test: {test_name}")
    print(f"Statistic = {statistic:.4f}, p-value = {result['PValueDisplay']}")
    print(result["Verdict"])
    if probability["FloatUnderflow"]:
        print("The ordinary float underflows to zero. The displayed approximation uses the same test distribution on a scaled log scale.")
'''

    # Model evaluation belongs to its companion notebook; remove its stale export references.
    notebook.cells[74].source = notebook.cells[74].source.split("model_metric_chart =")[0].rstrip() + "\n"
    notebook.cells[78].source = '''### Key Findings and Conclusions

Cleaning retains 235,370 eligible unique URLs from 235,795 raw rows. The main
benchmark contains 220,023 consistently labelled exact hosts, with one selected URL
per host. Q13–Q14 use their declared 3,000-host subsamples. These are different units
and scopes, so dividing the host count by the URL count is not a sampling fraction.

Mean URL length is about 12.73 characters higher in phishing hosts, whereas the
subdomain-count mean gap is only about 0.061. The latter illustrates why a small
p-value alone does not establish practical importance. HTTPS, favicons, social
links, form submission and financial keywords are associated with class in this
benchmark. Image and JavaScript median gaps are detected by the declared
permutation comparisons. Feature values do not establish attacker motives,
engineering effort, valid certificates or causality.

Both review rules have zero observed false alerts. Rule B misses 159 additional
phishing hosts and avoids zero false alerts, so its computed trade-off does not
support the earlier narrative of fewer false alarms. Zero observed errors do not
guarantee future safety. The recommended use remains contextual human review.

All four classifiers and the majority baseline are evaluated in
Model_Evaluation.ipynb. Their internal scores do not establish performance on
future traffic. The proposed randomized participant A/B study has not been run.
The following comparison checks the sensitivity of every statistical conclusion
to one documented random sample within this benchmark.
'''

    explanation = '''## 9. Original benchmark and random-sample comparison

We keep the original 15 results and compare them with a **simple random sample of
10,000 eligible hosts**, selected **without replacement**, using **seed 42**.
The finite population frame is the 220,023 eligible exact hosts already constructed
above. It does not represent every website on the internet. Each host has inclusion
probability 10,000 / 220,023, about 4.54%. No host is selected twice. We do not balance
the classes or choose observations according to a feature value or a test result.

**Why 10,000?** It gives several thousand observations per recorded class while
using less than 5% of the host frame, with manageable permutation computation.
This is a declared teaching sensitivity analysis, not a formal power calculation
or a sample size prescribed by the slides. We inspect actual class composition
and expected cell counts rather than assuming representativeness.

**Course links:** L11 slides 21–23 and 25 define sampling without replacement and
why the selection mechanism matters. L11 slides 34–38 explain sample size, sample
statistics and sampling variability. L12 slides 20–22, 39 and 42 define p-values
and rejecting or failing to reject H0. L12 slides 47–54 cover permutation testing.
L13 slides 20–24 cover chi-square independence, slides 30–31 distinguish practical
importance from significance, slides 40–41 cover Welch's t test, and slides 44,
50–55 cover paired tests and assumptions. L14 slide 25 explains why a p-value alone
does not prove causation.

Q12 retains the two scores together and uses the phishing subset of the shared
sample. Q15 retains both rule outcomes on every selected host. Q11 uses the same
ten TLD groups plus Other as the reference. Q13–Q14 retain their original 1,500 hosts
per class as the reference; the comparison uses the observed class counts in the
shared 10,000 hosts and repeats the same median statistic and 1,999 shuffles.

**Interpretation:** These samples are nested, so agreement is a sensitivity check
and is not independent replication. Finite benchmark differences can be described
directly. Original p-values are retained as model-based reference calculations.
For comparability, the sample repeats the original tests without finite-population
correction; its sampling fraction is below 5%. Source selection bias, related
campaigns and unadjusted multiple testing still limit inference to future websites.

The original-unit gap is an effect size. We also show descriptive mean/SD ratios
or Cramer V where applicable. These are summaries, not additional hypothesis tests.
Very small t/chi-square probabilities use scientific notation with a log-scale
tail calculation when a float underflows. Permutation probabilities keep their
original resolution of (extreme + 1) / 2,000, with minimum 0.0005.
'''
    design_code = '''from case_study.sampling import sampling_comparison

sampling_results = sampling_comparison(host_sample, test_results, alpha)
sampling_design = sampling_results["design"]
sampling_rows = sampling_results["rows"]
sampling_membership = sampling_results["membership"]

print(sampling_design["method"])
print(f"Eligible hosts: {sampling_design['population_hosts']:,}")
print(f"Selected hosts: {sampling_design['sample_size']:,}")
print(f"Sampling fraction: {sampling_design['sampling_fraction']:.4%}")
print(f"Seed: {sampling_design['seed']}")
display(pd.DataFrame(sampling_design["composition"]))
print(sampling_design["limitations"])
'''
    comparison_code = '''sampling_comparison_table = pd.DataFrame(sampling_rows)
comparison_columns = ["Question", "Analysis", "N", "Estimate", "EstimateUnits",
                      "Statistic", "DegreesOfFreedom", "PValueDisplay", "Decision",
                      "StandardizedEffect", "StandardizedEffectName"]

question_headings = QUESTION_HEADINGS

for question_number, question_heading in enumerate(question_headings, start=1):
    comparison = sampling_comparison_table.loc[
        sampling_comparison_table["Question"] == question_number
    ].copy()
    print("\\n" + question_heading)
    display(comparison[comparison_columns])

    effect_column = "StandardizedEffect" if question_number == 11 else "Estimate"
    effect_label = "Cramer V" if question_number == 11 else comparison.iloc[0]["EstimateUnits"]
    figure, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].bar(comparison["Analysis"], comparison[effect_column], color=["#364C70", "#16877C"])
    axes[0].axhline(0, color="grey", linewidth=0.8)
    axes[0].set_ylabel(effect_label)
    axes[0].set_title(f"Q{question_number}: observed effect")

    axes[1].bar(comparison["Analysis"], -comparison["Log10PValue"], color=["#364C70", "#16877C"])
    axes[1].axhline(-np.log10(alpha), color="#C44E52", linestyle="--", label="alpha = 0.05")
    axes[1].set_ylabel("-log10(p): larger means smaller p")
    axes[1].set_title(f"Q{question_number}: evidence strength")
    axes[1].legend()
    show_plot(f"sampling_comparison_q{question_number:02d}")

    for result in sampling_rows:
        if result["Question"] == question_number:
            print(result["Analysis"] + ": " + result["Verdict"])
            if result["Analysis"] == "Random sample":
                print(result["PracticalInterpretation"])
                print(result["AssumptionNote"])
                print("Decision agrees with reference:", result["DecisionMatchesReference"])

print(f"Matching decisions: {sampling_design['agreement_count']} of 15.")
print("Agreement alone does not show practical usefulness or repair bias in the original collection.")
'''.replace("QUESTION_HEADINGS", repr(headings))
    export_code = '''sampling_comparison_table.to_csv(dashboard_folder / "sampling_comparison.csv", index=False)
sampling_membership.to_csv(dashboard_folder / "sampling_membership.csv", index=False)
(output_folder / "sampling_design.json").write_text(
    json.dumps(sampling_design, indent=2, ensure_ascii=False), encoding="utf-8"
)
print("Saved the comparison and selected host identifiers for reproducibility.")
'''
    for cell in [nbformat.v4.new_markdown_cell(explanation), nbformat.v4.new_code_cell(design_code),
                 nbformat.v4.new_code_cell(comparison_code), nbformat.v4.new_code_cell(export_code)]:
        cell.metadata["sampling_comparison"] = True
        notebook.cells.append(cell)
    nbformat.write(notebook, PATH)
    print("Updated the notebook. Original questions and reference calculations retained; execute it next.")


if __name__ == "__main__":
    update()
