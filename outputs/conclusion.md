We started with 235,795 records and retained 235,370
unique eligible URLs. The main statistical comparisons use 220,023
consistently labeled exact hosts. EDA showed long tails, repeated hosts and
strong differences in the recorded classes' URL structure.

The average URL-length gap is 12.73 characters
(phishing minus legitimate), with p = below numerical precision.
HTTPS presence differs by -55.38 percentage points,
with p = below numerical precision. The full table reports all 15 tests,
their comparison units and their decisions at alpha = 0.05.

In the paired rule comparison, Rule B changes accuracy by
-0.072 percentage points relative to A,
with p = 1.82e-36. It misses 159
additional phishing hosts and avoids 0 false alerts in this sample.
That error trade-off matters alongside the statistical decision.

Our decision is to build a contextual review dashboard, showing feature rates,
sample counts and rule errors. These data do not establish a universally safe
automatic blocking rule. The supporting logistic model has internal test recall
99.6% and false-positive rate
0.2%; those results require external validation.

Source selection, related hosts, feature construction and page-retrieval quality
may affect the findings. Testing several exploratory questions also raises the
chance of false discoveries. The permutation results concern their stated
subsamples, and the paired correctness test uses a large-sample approximation.
There are no dates, loss measures or randomized user outcomes. Next steps are
an independently collected dated sample, better grouping of related sites and
the controlled A/B warning study described above.
