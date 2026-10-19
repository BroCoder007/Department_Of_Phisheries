# Department of Phisheries

A Streamlit application built around the three supplied PhiUSIIL notebooks.
The statistical case study leads the presentation; machine learning supports it.
Original notebooks are preserved byte for byte.

## Quick start

Python 3.12 or newer is required by the recorded dependency set (SciPy 1.18). The supplied
snapshot was prepared and tested with Python 3.14.6. Use the recorded dependency
versions for the closest reproduction.

```powershell
cd "D:\FODS PROJECT"
python -m pip install -r requirements-lock.txt
python -m streamlit run streamlit_app.py
```

Open **http://127.0.0.1:8501**. The included `artifacts/` directory contains
verified results and fitted models, so the app can start without retraining.
`start_app.ps1` and `start_app.bat` are equivalent Windows launchers.

For a fresh environment, you may create and activate a virtual environment first:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
```

`requirements.txt` describes the direct dependencies; `requirements-lock.txt`
records the actual tested versions. Saved joblib models require scikit-learn
1.9.0. If you change sources, dataset or model environment, rebuild:

```powershell
python -m case_study.prepare
```

Preparation reproduces the notebook computations and checks them against their
saved outputs. It refuses to substitute different evaluation scores when a
comparison fails. It never edits the original notebooks.

## Exactly six dashboards

| Dashboard | What it presents | Source |
|---|---|---|
| 01 Problem & dataset | Objectives, record/feature counts, raw preview with pagination, missing values, repeated observations, outliers and cleaning audit | Department_Of_Phisheries.ipynb |
| 02 Exploratory analysis | 12 selected interactive plots with Previous/Next, selection, counter, progress, interpretations and original figures | Plots.ipynb |
| 03 Analysis questions | All 15 original questions, unchanged headings, calculations, visualizations and linked tests | Department_Of_Phisheries.ipynb |
| 04 Statistical evidence | Original H0/H1, methods, alpha, actual statistics/p-values, recovered df and qualified interpretations | Department_Of_Phisheries.ipynb |
| 05 Models & prediction | All four actual classifiers, majority baseline, verified metrics, corrected confusion matrices, ROC curves and working prediction form | Model_Evaluation.ipynb |
| 06 Conclusions & team | Supported findings, recommendations, limitations, source corrections, BI connection and four editable team profiles | All three notebooks |

### Four models, as confirmed

The model notebook introduction lists three classifiers, but its executable
training and evaluation code includes **Gaussian Naive Bayes**, **Logistic
Regression**, **Decision Tree (max_depth=5)** and **Decision Tree (full)**. All
four are preserved, as confirmed by the user. The majority baseline is kept as
a comparison, not presented as a fifth selectable fitted classifier.

The prediction form requires the original eleven numeric features. **Random
Fill** loads every field from one real held-out dataset row. **Predict** calls
the selected fitted model with the original preprocessing and feature order.
Probabilities are model estimates, not guarantees of website safety. No URL is
visited, and the app does not claim to extract webpage features from a URL.

## Data and observation grains

Use the canonical `PhiUSIIL_Phishing_URL_Dataset.csv` beside the notebooks. No
unrelated or synthetic dataset is used. The source has 235,795 rows and 56 columns:
54 features, FILENAME and label. CSV label 0 means phishing and 1 legitimate.
The model target is `IsPhishing = 1 - label`, so model class 1 means phishing.

- EDA from Plots.ipynb retains all source rows and repeated URLs/domains.
- The statistical notebook retains 235,370 eligible unique URLs for descriptive
  summaries, then samples one URL per consistently labeled exact hostname for
  the 220,023-host main comparison sample.
- Q13 and Q14 use 1,500 hosts per class and 1,999 shuffles, exactly as written.
- The model notebook samples 80% of distinct hosts into training, seed 42;
  the remainder form the test set. No exact host crosses partitions. This is
  host grouping without class stratification, despite the notebook heading.

These different denominators are preserved and labeled. Exact duplicates,
repeated URLs and shared domains are investigated separately. Related sites,
collection artifacts and source selection remain limitations.

## Transparent corrections

The app keeps original notebook questions, code and figures available for audit.
It corrects presentation/interpretation errors without altering the originals:

- A conclusion confuses unique-URL and host-sample counts.
- Rule B is incorrectly described as reducing false alerts; both rules actually
  have zero false alerts, while B misses 159 additional phishing hosts.
- The model confusion figure swaps two titles and reverses three class labels.
- The statistical export cell references model variables moved to the model
  notebook; the adapter exports each notebook's own results.
- Tests are evidence under assumptions, not proof of causality. Tiny p-values
  and zero observed false positives do not establish operational safety.

See [the complete source audit](docs/SOURCE_AUDIT.md). The app contains no new
Fisher, rank-based or other substituted hypothesis tests. Existing EDA confidence
intervals reproduce Plot 23's own code and are identified as descriptive views.

## Project structure

```text
streamlit_app.py             Streamlit entrypoint and six-view navigation
case_study/
  config.py                 Project paths and model identities
  sources.py                Read-only notebook parsing and correction notes
  prepare.py                Exact source execution, verification and artifacts
  charts.py                 Interactive versions of notebook plot recipes
  service.py                Results, pagination, schema validation and inference
  team.py                   Four SQLite team profiles and image validation
  views.py                  The six dashboards
assets/theme.css            Report-style visual system and responsive layout
.streamlit/config.toml      Local server and theme settings
backend/server.py           Optional REST and Power BI connector
artifacts/                  Verified JSON, CSVs, figures, models and manifest
outputs/powerbi/            Matching CSV imports for the existing Power BI project
powerbi/                    Editable PBIP/PBIR report
Department_Of_Phisheries.ipynb  Original preprocessing, questions and tests
Plots.ipynb                 Original EDA
Model_Evaluation.ipynb      Original model training and evaluation
data/team.sqlite3           Created on demand; private local team profiles
tests/                      Service, API and Streamlit application checks
docs/                       Architecture, source audit, BI setup and test report
scripts/build_release.py    Creates the ready-to-run ZIP
```

Team names, register numbers, roles and portraits are editable in Dashboard 6.
Save each section explicitly. Photos can be previewed, replaced or removed;
PNG/JPEG uploads are limited to 3 MB and 12 megapixels. Names remain blank until
you provide them. The local SQLite database persists across app restarts and is
excluded from Git and the release archive. This is a local academic demo; add
appropriate access control before exposing profile editing publicly.

## Optional API and Power BI

The native app does **not** require a separate API process. `server.py` is retained
because it supplies the genuine external Power BI/API connection.

```powershell
python backend/server.py
```

API: **http://127.0.0.1:8765/health**. The service exposes 14 verified CSV tables,
question/EDA/model JSON, feature schemas, Random Fill and actual prediction.

```text
GET  /api/summary
GET  /api/evidence
GET  /api/questions
GET  /api/questions/1
GET  /api/eda
GET  /api/models
GET  /api/feature-schema?model=logistic_regression
GET  /api/random-fill?model=logistic_regression
POST /api/predict
GET  /data/statistical_evidence.csv
GET  /data/model_summary.csv
```

Prediction JSON has exactly `model_id` and `features`, where features contains
the eleven names returned by the schema endpoint. All four model IDs are
`naive_bayes`, `pruned_tree`, `logistic_regression` and `full_tree`.

Open `powerbi/Phisheries.pbip`, set `UseBackend=true`, select Anonymous credentials
for localhost and refresh. For file imports, use `UseBackend=false` and point
`DataFolder` to this checkout's `outputs/powerbi` folder. Preparation regenerates
the same values used by the app. The BI confusion table is specifically the
logistic-regression test matrix; the native website shows all four matrices.

A hosted report embed appears only if a real `POWERBI_EMBED_URL` is configured.
No static screenshot or placeholder iframe is presented as an integration.
See [Power BI setup and external requirements](docs/POWER_BI.md).

## Tests

```powershell
python -m unittest discover -s tests -v
```

The suite checks original heading preservation, all notebook/source fingerprints,
15 test outputs, EDA provenance, all four inference paths, Random Fill coherence,
input errors, raw preview pagination, SQLite photo persistence, all 14 CSV API
endpoints and navigation through all six Streamlit dashboards. Team tests use a
temporary database and neutral generated image fixtures.

See [the test report](docs/TEST_REPORT.md) for executed checks, browser verification
and the specific external features that require your configuration.

## Build the project archive

```powershell
python scripts/build_release.py
```

The archive includes the canonical PhiUSIIL CSV, the three original notebooks,
source code, dependencies, verified model/result artifacts and documentation.
It excludes the duplicate dataset copy, .git, .work, environments, caches,
existing team-profile data and its own output directory.

## Troubleshooting

- **Missing/stale snapshot:** run `python -m case_study.prepare`, then restart or
  reload the app. Never mix a changed notebook with old scores.
- **Dataset not found:** restore the canonical CSV beside the original notebooks.
  The app does not download a replacement dataset.
- **Model-version mismatch:** use the pinned environment and rebuild the snapshot.
- **Preparation score mismatch:** inspect the source audit, package versions and
  original split. Preparation intentionally stops instead of inventing scores.
- **Port in use:** pass `--server.port 8502` to Streamlit, or `--port 8766` to the
  optional API (and update BI source URLs accordingly).
- **Power BI moved folder:** edit DataFolder in Power BI Desktop. Desktop project
  loading/rendering and external tenant access require a compatible installation.

## Sources

[UCI PhiUSIIL Phishing URL Dataset](https://archive.ics.uci.edu/dataset/967/phiusil-phishing-url-dataset),
Arvind Prasad and Shalini Chandra, CC BY 4.0.
[Original study](https://doi.org/10.1016/j.cose.2023.103545).
The three supplied notebooks and uploaded 23CSE351 L8–L14 course material remain
primary analytical references. No A/B participant experiment has been conducted.
