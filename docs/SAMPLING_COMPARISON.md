# Sampling comparison

Added 20 October 2026 in notebook section 9 and the existing Streamlit dashboards.

## Selection and justification

The finite frame contains 220,023 consistently labelled exact hosts, with one
selected URL for every eligible host. Raw rows (235,795), cleaned URLs (235,370)
and hosts are different units. Dividing a host count by a URL count is not a
sampling fraction.

```python
random_hosts = host_sample.sample(n=10000, replace=False, random_state=42)
```

Every host has inclusion probability 10,000 / 220,023 = **4.544979%**. The selected
sample contains **3,885 phishing and 6,115 legitimate hosts**. The phishing share
is 38.85%, compared with 38.7355% in the frame. Class composition alone does not
establish that every feature or distribution tail is represented accurately.

10,000 gives several thousand hosts per class, uses less than 5% of the frame
and keeps permutation computation manageable. This is a declared teaching
sensitivity analysis, not a formal power calculation or a size prescribed by
the slides. Size and seed are fixed without searching for a desired p-value.
Selection is without replacement, without class balancing and independent of
feature values. Membership identifiers and a SHA-256 hash are exported.

## Supplied course material

| Material | Slides | Applied concepts |
|---|---|---|
| L11 Sampling and Emprical distribution | 21–23, 25 | Simple random sampling without replacement and selection mechanism |
| L11 | 34–38 | Sample size, sample summaries, parameter/statistic and sampling variability |
| L12 Hypothesis testing and Error probabilities | 20–22, 39, 42 | Meaning of p-value, alpha, reject/fail to reject |
| L12 | 47–54 | Permutation statistics and empirical p-values |
| L13 Statistical Testing and comparing model | 20–24 | Chi-square independence |
| L13 | 30–31 | Statistical versus practical significance |
| L13 | 40–41 | Welch test and decimal degrees of freedom |
| L13 | 44, 50–55 | Pairing, paired t test, assumptions and test selection |
| L14 Causation and Experiment | 25 | A p-value alone does not establish causation |

References were checked against the actual supplied PPTX files. All numerical
findings come from PhiUSIIL, rather than slide examples.

## Every question retains its method

| Questions | Added comparison |
|---|---|
| Q1–Q3 | Same Welch tests, numerical features and difference direction |
| Q4–Q10 | Same binary feature/class chi-square tables; expected counts checked |
| Q11 | Same original ten TLD groups plus Other, fixed across scopes |
| Q12 | Two scores paired on the 3,885 selected phishing hosts |
| Q13–Q14 | Same median-gap statistic and 1,999 shuffles on the shared sample |
| Q15 | Both rule outcomes retained on each of 10,000 hosts |

Q13–Q14 retain their original **1,500 hosts per class** as the reference. No new
full-population permutation result is claimed. Their sample comparison uses
the actual 3,885/6,115 class counts. Q12's reference contains 85,227 paired hosts;
the other main reference tests use 220,023 hosts.

Each question shows both estimates in natural units, statistic, df, p-value and
explained verdict. Natural-unit differences are effect sizes. Descriptive Cohen d,
paired dz and Cramer V are also provided where useful; these are summaries rather
than additional hypothesis tests. All 15 comparison figures are inside the
notebook and compare effects and −log10(p).

## P-values and verdicts

For t/chi-square tails that underflow ordinary floats, the same test distribution
is integrated after scaling its density relative to the observed statistic.
The calculation retains log10(p) and a scientific-notation string. These are
numerical approximations to the same distributional probabilities, not new tests.

| Question | Original p, approximately | Sample p, approximately |
|---|---:|---:|
| Q1 | 2.201928e-1314 | 3.495335e-140 |
| Q3 | 3.784781e-102 | 2.495867e-6 |
| Q15 | 1.818941e-36 | 2.695808e-3 |

Import **PValueDisplay as text** in spreadsheets/BI. Numeric conversion can turn
tiny values back into zero. Log10PValue is a finite numeric plotting field.
PValue retains the original SciPy float return for traceability. The Power BI
model already types PValueDisplay as text; JSON endpoints preserve its string.

Permutation p-values remain **(extreme + 1) / 2,000**, with minimum 0.0005.
More display digits do not increase simulation precision.

All 15 sample decisions agree with the reference at alpha = 0.05. The verdicts
explain p versus alpha and the relevant claim. Failure to reject means insufficient
evidence and does not prove equality or H0. These remain exploratory, unadjusted
tests; a small p-value does not establish practical usefulness, causality or the
probability that H0 is true. Inspect effect magnitudes and assumptions too.

## Scope and limitations

The sample is nested in its reference frame, so agreement is a sensitivity check
rather than independent replication. Sampling inside this collection cannot
remove source selection bias, campaign dependence or feature-provenance issues.
The host frame is not a random sample of all websites on the internet.

Finite benchmark differences can be described directly. Original p-values are
retained as model-based reference calculations treating observations as arising
from a wider process. Conventional tests are repeated without finite-population
correction for methodological comparability; the sample fraction is below 5%.
This does not claim exact design-based finite-population inference.

## Reproduction and outputs

```powershell
python scripts/execute_analysis_notebook.py
python -m case_study.prepare
python -m streamlit run streamlit_app.py
```

- Notebook section 9: executed design, all 30 comparison rows, 15 figures and verdicts.
- Dashboards 1 and 4: plan, composition and course references.
- Dashboards 3 and 4: each question's original/sample comparison.
- artifacts/sampling.json: design and results.
- artifacts/bi/sampling_comparison.csv: two scopes per question.
- artifacts/bi/sampling_membership.csv: selected host/FILENAME/label identifiers.
- outputs/powerbi/: matching CSVs.
- GET /api/sampling: design and comparison JSON.
- GET /data/sampling_comparison.csv and /data/sampling_membership.csv: BI imports.

The previous notebook and statistical outputs are retained in
artifacts/reference_before_sampling. Original headings, statistics, estimates and
decisions are checked against it. Companion notebooks and four model procedures
are unchanged.
