# Department of Phisheries

A Foundations of Data Science case study of URL and webpage indicators in the
real PhiUSIIL dataset. The decision is which indicators deserve a place in a
review dashboard, and whether any single cue justifies automatic blocking.

The project emphasizes preprocessing, descriptive statistics, 15 analysis
questions, visualizations, hypothesis testing and a justified decision. One
logistic-regression model provides a supporting comparison with a majority
baseline. Course concepts from the supplied L8–L14 slides are mapped in the
notebook's first section.

## Files

| File or folder | Purpose |
|---|---|
| `Department_Of_Phisheries.ipynb` | Self-contained notebook with saved calculated outputs |
| `PhiUSIIL_Phishing_URL_Dataset.csv` | Original source data, used by the notebook |
| `PhiUSIIL_Phishing_URL_Dataset_copy.csv` | Existing copy; not combined with the original |
| `requirements.txt` | Notebook dependencies |
| `outputs/figures/` | Saved charts for the report/presentation |
| `outputs/powerbi/` | Computed aggregates, evidence, decisions and model results |
| `outputs/conclusion.md` | Conclusion generated from the calculated results |
| `outputs/run_summary.json` | Data fingerprint, sample counts, results and package versions |
| `powerbi/Phisheries.pbip` | Editable Power BI project with four report pages |
| `powerbi/README.md` | Desktop setup, refresh and backend connection instructions |
| `backend/server.py` | Optional local HTTP service for the exported analysis |

## Run the analysis

Use Python 3.10 or later, then install the dependencies in your project environment:

```powershell
python -m pip install -r requirements.txt
```

Open the notebook in VS Code/Jupyter, select that Python environment, and run the
cells from top to bottom with the working directory set to this project. The
notebook recreates the charts and export tables. It reads the local CSV and does
not fetch the websites or download replacement data.

## Open the Power BI report

Open `powerbi/Phisheries.pbip` in a Power BI Desktop installation that supports
PBIP and enhanced PBIR, then Refresh. The semantic model defaults to local CSV
imports from `D:\FODS PROJECT\outputs\powerbi`. Change its `DataFolder` parameter
if the folder moves. The four pages cover the dataset, review indicators,
statistical evidence and the supporting model. See `powerbi/README.md`.

The report definitions have been checked against Microsoft's JSON schemas and
their fields checked against the semantic model. Power BI Desktop engine loading
and visual rendering still need to be checked in Desktop; schema validation is
not a substitute for that step. No published dashboard or PBIX file is claimed.

## Connect the optional backend

```powershell
python backend/server.py
```

The service runs on `http://127.0.0.1:8765`. Set the Power BI `UseBackend`
parameter to `true` and Refresh to read the saved aggregates over HTTP. It is a
local import/refresh demonstration, not a streaming service. Stop it with Ctrl+C.

## How to interpret the evidence

The source CSV has 235,795 rows. The completed run retains 235,370 unique URLs
and uses one URL from each of 220,023 consistently labeled exact hosts for the
main tests. The 15 questions use only tests found in the supplied course slides:
Welch two-sample t-tests, chi-square independence tests, paired t-tests and
permutation tests. Q13–Q14 use 1,500 sampled hosts per class and 1,999 shuffles.
Reported p-values are unadjusted and exploratory, with decisions at 0.05.
Multiple questions increase the chance of false discoveries.

All plotting code is inside the notebook and uses Matplotlib. Analysis uses
pandas, NumPy and basic SciPy functions. Scikit-learn is limited to one logistic
regression model. Counts are transformed and scaled with ordinary DataFrame
operations using training data only. No separate plotting script is needed.

The collected classes differ strongly in URL structure as well as supplied
scores. Source selection and related hosts can affect the results. The review
decision concerns this benchmark: it does not establish internet-wide phishing
prevalence, causation, future detector performance or a universally safe blocking
policy. The ML split groups exact hostnames and is retrospective; it is not an
external, future-dated or campaign-level evaluation.

## Source and credit

[PhiUSIIL dataset, UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/967/phiusil-phishing-url-dataset),
Arvind Prasad and Shalini Chandra, donated in 2024, licensed CC BY 4.0.
[Original study](https://doi.org/10.1016/j.cose.2023.103545).
