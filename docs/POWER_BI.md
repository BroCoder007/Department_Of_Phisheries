# Power BI connection

The Streamlit site works without a Power BI account. The bonus integration is a
real local CSV/JSON API, alongside the existing editable PBIP project. No hosted
report, tenant credentials or published workspace were available during development.

## Local report and backend

1. Prepare the three-notebook snapshot:

   ```powershell
   python -m case_study.prepare
   ```

2. Start the optional connector in a separate terminal:

   ```powershell
   python backend/server.py
   ```

3. Visit `http://127.0.0.1:8765/health`. Its status should be `ready`.
4. Open `powerbi/Phisheries.pbip` in compatible Power BI Desktop.
5. Under **Transform data → Edit parameters**, use either:
   - `UseBackend = true`: keep the connector running; select Anonymous credentials
     for the localhost web source, then refresh.
   - `UseBackend = false`: set `DataFolder` to the absolute path of
     `outputs/powerbi` in this checkout, then refresh.

Preparation copies the same 14 verified CSV tables into `outputs/powerbi` that
the API serves from `artifacts/bi`. Their contents are tested for agreement.
The four-classifier comparison comes from Model_Evaluation.ipynb. To preserve
the existing BI table grain, `model_confusion.csv` is the logistic-regression
test matrix; all four matrices and ROC curves are available in the website/API.

Example endpoints:

- `/api/summary`: input fingerprint, record counts, test/model counts and scope.
- `/api/evidence`: all 15 actual test results as JSON.
- `/data/statistical_evidence.csv`: Power Query-ready test evidence.
- `/data/model_summary.csv`: four classifiers and the majority baseline.
- `/data/feature_rates.csv`: class-specific feature counts and rates.

P-values are saved results, not recalculated by report filters. Tables with
different observation grains must not be joined in a way that duplicates counts.
The connector is an import/refresh source, not DirectQuery or streaming.

## Optional hosted embed

The conclusion dashboard supports `POWERBI_EMBED_URL` when a real report exists:

```powershell
$env:POWERBI_EMBED_URL = "https://app.powerbi.com/reportEmbed?reportId=YOUR_REPORT_ID&groupId=YOUR_WORKSPACE_ID&autoAuth=true"
python -m streamlit run streamlit_app.py
```

Use your actual organization report/workspace IDs and Power BI's supported
secure-embed URL. Tenant sign-in, sharing permissions, licensing and report
access are controlled by Power BI. Do not place passwords or access tokens in
the repository or URL. The app allows HTTPS `app.powerbi.com/reportEmbed` or
`/view` links; no iframe is displayed when an embed is not configured.

For a report published to Power BI Service, localhost is not a hosted data
source. Configure an appropriate gateway or hosted API and its credentials.
Embedding and Power BI Desktop rendering require your external configuration;
they are not claimed as locally verified features.

Official format/integration references:

- [Power BI Desktop projects](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview)
- [Securely embed a report](https://learn.microsoft.com/en-us/power-bi/collaborate-share/service-embed-secure)
- [Streamlit application testing](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest)
