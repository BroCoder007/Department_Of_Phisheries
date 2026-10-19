# Verification report

Date: 19 October 2026. Environment: Windows, Python 3.14.6, Streamlit 1.53.1,
scikit-learn 1.9.0. Other tested versions are in requirements-lock.txt.

## Automated application checks

Command:

```powershell
python -u -m unittest discover -s tests -v
```

Final result: **14 tests passed in 8.091 seconds**. The suite covers:

1. Every original question heading is preserved verbatim and there are at least 15.
2. All three original source hashes and all 15 saved statistical comparisons verify.
3. Every artifact fingerprint, dataset/class count and statistical CSV agrees.
4. The 12 selected EDA plots are traceable to the 23-plot source catalog.
5. Each of four actual models predicts three real held-out samples consistently
   with its original reference predictions; probabilities and explanations exist.
6. Missing, extra, invalid, nonfinite and inconsistent features are rejected;
   unknown models and missing artifact dependencies produce clear errors.
7. Dataset preview pagination, class filtering and literal search work.
8. Four neutral SQLite profiles support saved names/photos, replacement, removal,
   persistence and rejection of malformed images in an isolated test database.
9. All 14 CSV routes return byte-identical verified tables; question, evidence,
   EDA and model endpoints respond; unknown/path-traversal routes return 404.
10. All four classifiers perform real HTTP prediction; invalid payloads return 422.
11. All six Streamlit dashboards load, all 15 questions can be selected, and
    question-to-test and return links preserve question numbering.
12. EDA Previous/Next controls and direct selection cover all 12 charts.
13. All four model selections complete Random Fill and Predict in AppTest;
    inconsistent domain/URL lengths show an input error.
14. Four photo controls appear and name/register/role fields save through the UI.

Streamlit AppTest emits its expected bare-mode ScriptRunContext warning; there
were no failed assertions or app exceptions. API tests bind an ephemeral local
port and shut down the server on completion. Team tests use temporary databases.

## Notebook reproduction

`python -m case_study.prepare` completed successfully. It executes the original
preprocessing/statistical cells and original model procedure, checks all 15
statistics and p-value displays against saved outputs, and verifies the entire
model comparison table and confusion counts. Exact host overlap between model
partitions is zero. All original notebook hashes remain unchanged.

Original source figures are preserved; selected interactive charts use the
source's recipes. The notebook discrepancies and corrections are documented in
SOURCE_AUDIT.md and displayed in the app. No extra hypothesis tests, alternate
models, random example scores or unrelated datasets were introduced.

## Browser checks

The actual local Streamlit site was inspected in the in-app browser:

- Desktop at 1366 × 900: navigation, report typography, readable content and charts.
- Phone at 390 × 844: sidebar collapses, heading wraps and metrics form two columns.
- EDA: original class-distribution chart renders with the correct title and labels.
- Prediction: Random Fill populates the real eleven-feature vector; Predict returns
  a model label, probabilities and explanation. A logistic-regression sample
  returned Legitimate with the model's estimated phishing probability 0.0010%.
  This is a checked example, not a promised prediction for the next random sample.
- Team: a neutral solid-color PNG was uploaded, previewed and saved through the
  browser. It was then removed through the saved-photo checkbox and Save button.
  All four actual project profiles remain blank with no saved portraits.

Screenshot records are in docs/images: overview-desktop.png, overview-mobile.png,
prediction-desktop.png and eda-desktop.png. Browser checks complement the
automated suite; they are not a claim of exhaustive compatibility on every device.

## Power BI connection

All 14 backend CSV exports were checked against the artifact files. The existing
PBIP project supports file import and the local backend source. **38 project and
report documents** passed Microsoft's published JSON schemas, and all visual
field/measure references and container bounds passed static validation.

Power BI Desktop engine loading, DAX rendering, tenant access, report publishing
and authenticated embedding were **not verified** in this environment. No service
workspace, report identity or credentials were supplied. The app shows an embed
only when a genuine supported Power BI URL is configured; otherwise it supplies
the tested data/API integration and setup documentation. See POWER_BI.md.

## Release checks

`python scripts/build_release.py` packages the source, canonical dataset,
unchanged notebooks, fitted artifacts, BI project, dependency files and docs.
The builder checks the ZIP CRCs and all source/dataset hashes inside the archive.
Local team data, test fixtures, environments, caches and duplicate dataset copies
are excluded. The environment packages themselves are not bundled: install the
recorded dependencies before starting an extracted copy.

The 21.3 MB archive was extracted into a separate folder. From that folder, the
service verified its sources, loaded all 15 questions and 12 EDA views, ran all
four model inferences and started the Streamlit app through AppTest successfully.
