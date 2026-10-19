# Source and result audit

Prepared on 19 October 2026. The application uses only the supplied PhiUSIIL CSV
and three original notebooks. All code cells, saved text/table outputs, markdown
and embedded figures were inspected before the app was implemented. The notebooks
remain unchanged; the manifest and automated checks verify their SHA-256 hashes.

## Inspection coverage

| Notebook | Cells | Code cells | Saved figures | Responsibility |
|---|---:|---:|---:|---|
| Department_Of_Phisheries.ipynb | 79 | 31 | 18 | Inspection, preprocessing, 15 questions, tests and decisions |
| Plots.ipynb | 79 | 31 | 23 | Raw-record exploratory plots and interpretations |
| Model_Evaluation.ipynb | 20 | 10 | 4 | Four classifiers, baseline, evaluation and model figures |

Source code, original outputs and original PNGs remain accessible in the app's
source expanders and `artifacts/original/`. The complete EDA catalog records all
23 source plots, including plots not selected for the primary presentation.
Figure files and calculations are linked to their original zero-based cell indices.

## Dataset and preprocessing

The canonical CSV has 235,795 rows, 56 columns, 100,945 phishing rows and 134,850
legitimate rows. There are 54 features plus FILENAME and label. CSV labels are
0 = phishing and 1 = legitimate; the model's IsPhishing target reverses that mapping.

The main notebook checks missingness, duplicates, URL label conflicts, parsing
and repeated hosts. Its sequence is reproduced: drop exact duplicates, trim URLs,
exclude conflicting URL labels, retain one row per URL, parse lowercase hostnames
without trailing dots, exclude unparseable hosts, derive Class/IsPhishing, then
build a consistently labeled host sample for the statistical comparisons.

| Check | Actual result |
|---|---:|
| Missing cells | 0 |
| Exact duplicate rows removed | 0 |
| Conflicting URL rows excluded | 0 |
| Same-label repeated URL rows removed | 425 |
| Unparseable hosts excluded | 0 |
| Eligible unique URLs | 235,370 |
| Mixed-label hosts excluded from test sampling | 54 |
| One URL per consistently labeled host | 220,023 |
| Phishing hosts in the main sample | 85,227 |
| Legitimate hosts in the main sample | 134,796 |

Repeated domains are investigated separately from identical URL records.
Distinct URLs from the same host are retained for descriptive/model work.
Outliers are flagged with the notebook's IQR rule, documented and retained;
the adapter does not add clipping, winsorization or synthetic imputation.
Plots.ipynb uses all raw rows and removes FILENAME metadata only. Its grain is
explicitly different from the formal host comparisons. Counts are not interchanged.

## Original questions and tests

All 15 numbered question headings are parsed directly from the source markdown
and compared verbatim in the test suite. No supplemental questions were needed.
The application reproduces the following existing methods at alpha = 0.05:

| Questions | Existing method and scope |
|---|---|
| Q1–Q3 | Independent two-sample t tests with equal_var=False, using the host sample |
| Q4–Q10 | Chi-square tests of the binary feature and recorded class |
| Q11 | Chi-square test across the source's common TLD groups |
| Q12 | Paired t test of the two title-match scores on the same phishing hosts |
| Q13–Q14 | Source median-difference permutation tests: 1,500 hosts/class and 1,999 shuffles |
| Q15 | Paired t test of correctness for two rules on the same hosts |

Every reproduced test statistic is compared with the saved value at the source
table's four-decimal precision. P-value display strings are also compared.
Full numerical values from those same computations and available degrees of freedom
are retained. Raw underflow values are explained instead of claiming a true zero
probability. The permutation correction gives a minimum possible p-value of 0.0005.

No Fisher exact, Mann–Whitney or substituted hypothesis test was added. Course
material and the original questions guide the explanations. Plot 23's existing
95% t intervals are reproduced as a descriptive EDA view, not an additional test.
Assumptions, exploratory multiplicity, sample scope and practical effect sizes
are discussed. The data support associations and internal comparisons; they do
not establish causality or universal blocking rules.

## Selected EDA plots

| Source number | Purpose preserved |
|---:|---|
| 1 | Class distribution |
| 3 | URLLength histogram and KDE |
| 4 | LineOfCode histogram on a log scale |
| 5 | NoOfImage distribution |
| 6 | Grouped counts for the top 15 TLDs |
| 8 | Annotated URLSimilarityIndex histogram |
| 14 | NoOfExternalRef box plot on a log scale |
| 17 | Numeric-feature correlation heatmap |
| 21 | IQR outlier analysis |
| 22 | URL-length bins and class composition |
| 23 | Standardized feature means with the source's 95% intervals |
| 24 | Binary feature rates by recorded class |

Interactive charts preserve source features, bins, ordering, sampling seeds,
scales and calculations. Redundant variants and teaching examples of misleading
scales were omitted from the main carousel. Source PNGs and code are available
for comparison. URLSimilarityIndex's strong class separation is a reason to audit
feature provenance; the chart alone does not prove leakage.

## Model reproduction

The executable model notebook trains four classifiers, although its introduction
lists three. The user confirmed preserving all four. The majority baseline remains
in the comparison but is not a selectable trained classifier.

The original feature order is:

```text
URLLength, DomainLength, NoOfSubDomain, NoOfImage, NoOfCSS, NoOfJS,
IsHTTPS, HasTitle, HasFavicon, HasSocialNet, HasExternalFormSubmit
```

The code samples 80% of unique exact hosts into training with seed 42. It does
not stratify by class despite the source heading. Training contains 188,658 URLs
from 176,062 hosts; testing contains 46,712 URLs from 44,015 hosts. No exact host
or normalized value in the source Domain column crosses the partitions.
This check does not rule out related campaigns, collection artifacts or broader
registrable-domain relationships.

GaussianNB uses its defaults. LogisticRegression uses C=1, solver=lbfgs,
max_iter=1000 and random_state=42. Both apply log1p to the six count features,
then standardize these counts with training-only mean and standard deviation
(ddof=0); flags remain unchanged. The pruned tree uses max_depth=5 and seed 42;
the full tree uses seed 42. Trees receive the original numeric features.

| Model | Accuracy | Precision | Recall | F1 | TN | FP | FN | TP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Majority baseline | 0.5759 | 0.0000 | 0.0000 | 0.0000 | 26,903 | 0 | 19,809 | 0 |
| Gaussian Naive Bayes | 0.9677 | 0.9965 | 0.9270 | 0.9605 | 26,838 | 65 | 1,446 | 18,363 |
| Decision Tree (max_depth=5) | 0.9842 | 0.9741 | 0.9891 | 0.9815 | 26,382 | 521 | 216 | 19,593 |
| Logistic regression | 0.9972 | 0.9972 | 0.9963 | 0.9967 | 26,847 | 56 | 73 | 19,736 |
| Decision Tree (full) | 0.9974 | 0.9970 | 0.9968 | 0.9969 | 26,844 | 59 | 63 | 19,746 |

All metrics and confusion counts match the saved comparison table at its reported
precision. ROC points/AUC are obtained from those same fitted models and split.
The full tree and logistic regression have very close internal test scores;
no new significance test of their difference or future deployment performance
is claimed.

Saved artifacts contain genuine fitted estimators, training transformations,
feature order, observed input ranges and held-out reference predictions. Random
Fill selects a complete real held-out row. The prediction interface validates
all eleven inputs and invokes the selected model. It does not fetch a webpage
or infer all eleven features from a pasted URL.

## Corrections without editing the originals

1. The statistical conclusion calls 220,023 a unique-URL count. The correct
   eligible URL count is 235,370; 220,023 is the main host sample.
2. The Rule B narrative says it reduces false alerts. Both rules have zero
   observed false alerts, while Rule B misses 159 additional phishing hosts.
3. Statements about proof, impossible shuffled differences and p approximately
   zero are qualified using the actual test and simulation limits.
4. Attacker motives, certificate validity, domain price and construction effort
   are not measured. Such explanations are not presented as demonstrated causes.
5. The introduction's model count is corrected to four, as confirmed by the user.
6. The original confusion figure swaps logistic/pruned-tree titles and reverses
   the target labels on three panels. App matrices use each model's own verified
   predictions and [Legitimate, Phishing] axis order. Original PNG is retained.
7. Statistical export cell 74 references model variables moved to the model
   notebook. The adapter executes the statistical cells, exports their tables
   directly and obtains all model exports from Model_Evaluation.ipynb.
8. EDA and inference grains differ deliberately; their denominators are labeled.
9. Plot 24's title reverses high/low color descriptions. An explicit numeric
   colorbar corrects the legend while retaining values and ordering.
10. The app displays actual missing counts instead of a literal unevaluated
    f-string and identifies Q12's difference histogram correctly.

## Fingerprints and verification records

`artifacts/manifest.json` records the full dataset, notebook and generated-file
SHA-256 fingerprints and the preparation environment. It is the authoritative
machine-readable audit record. `execution_log.json` captures reproduced cell
output, while study.json includes statistical/model verification and split checks.
The release builder verifies source fingerprints inside the ZIP and its CRCs.
See TEST_REPORT.md for application and integration checks.
