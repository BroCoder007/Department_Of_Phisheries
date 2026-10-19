"""The six Streamlit dashboards. All numerical content comes from the snapshot."""

import html
import io
import json
import math
import os
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from .charts import style, PHISH, LEGIT, INK
from .config import ROOT, ARTIFACTS, NOTEBOOKS
from .service import InputError
from . import team

PAGES = {
    "overview": "01  Problem & dataset",
    "eda": "02  Exploratory analysis",
    "questions": "03  Analysis questions",
    "evidence": "04  Statistical evidence",
    "models": "05  Models & prediction",
    "conclusion": "06  Conclusions & team",
}


def go_to(page, question=None):
    st.session_state["navigation"] = PAGES[page]
    if question is not None:
        st.session_state["question_number" if page == "questions" else "evidence_number"] = question
    st.query_params["view"] = page


def hero(number, title, description):
    st.markdown(f'<div class="study-eyebrow">Department of Phisheries / Study {number:02d}</div>'
                f'<div class="study-title">{html.escape(title)}</div>'
                f'<div class="study-deck">{html.escape(description)}</div><hr class="study-rule">', unsafe_allow_html=True)


def figure(specification, key):
    st.plotly_chart(go.Figure(specification), width="stretch", key=key,
                    config={"displaylogo": False, "toImageButtonOptions": {"format": "png", "scale": 2}})


def source_footer(text):
    st.markdown(f'<div class="source-line">{html.escape(text)}</div>', unsafe_allow_html=True)


def original_view(item, notebook_name):
    with st.expander("Source notebook, original figure and implementation"):
        st.caption(f"{notebook_name} · code cell references are zero-based in the audit.")
        for name in item.get("original_figures", []):
            path = ARTIFACTS / name
            if path.is_file():
                st.image(path.read_bytes(), width="stretch")
        if item.get("original_interpretation"):
            st.caption("Original wording is retained below for traceability. Use the qualified interpretation above where a correction is noted.")
            st.markdown(item["original_interpretation"])
        st.code(item.get("code", ""), language="python")
        if item.get("saved_output"):
            st.text(item["saved_output"])


def move_selection(key, delta, maximum, minimum=1):
    st.session_state[key] = max(minimum, min(maximum, st.session_state.get(key, minimum) + delta))


def question_selector(service, key):
    options = [q["number"] for q in service.questions]
    titles = {q["number"]: q["heading"] for q in service.questions}
    st.selectbox("Choose a question", options, format_func=titles.get, key=key)
    number = st.session_state[key]
    left, center, right = st.columns([1, 2, 1])
    left.button("Previous question", disabled=number == options[0], key=key + "_previous",
                on_click=move_selection, args=(key, -1, options[-1]))
    center.caption(f"Question {number:02d} of {len(options):02d}")
    right.button("Next question", disabled=number == options[-1], key=key + "_next",
                 on_click=move_selection, args=(key, 1, options[-1]))
    st.progress(number / len(options))
    return service.question(number)


def overview(service):
    data = service.study
    hero(1, "A closer look at suspicious URLs.",
         "A Foundations of Data Science investigation of URL and webpage indicators. The decision: which observations deserve attention during review, and what does the evidence actually support?")
    a, b, c, d = st.columns(4)
    a.metric("Source records", f"{data['raw_rows']:,}")
    b.metric("Source features", str(data["feature_count"]))
    c.metric("Eligible unique URLs", f"{data['unique_urls']:,}")
    d.metric("Hosts used for testing", f"{data['inference_hosts']:,}")
    st.caption(f"The source has {data['feature_count']} features plus FILENAME and label. Descriptive EDA retains raw rows; formal comparisons use the sample named in each result.")
    st.subheader("The research question")
    st.write("Can familiar address and webpage features help us review suspected phishing without mistaking a strong dataset association for a universally safe blocking rule?")
    main, aside = st.columns([2, 1], gap="large")
    with main:
        st.markdown("#### What we investigate")
        st.write("We inspect data quality, compare the recorded classes, test the original 15 questions and evaluate the errors made by two simple review rules. Four classifiers provide a supporting comparison.")
    with aside:
        st.markdown("#### Dataset")
        st.write("PhiUSIIL Phishing URL (Website), by Arvind Prasad and Shalini Chandra. UCI Machine Learning Repository, CC BY 4.0.")
        st.markdown("[Open the dataset source](https://archive.ics.uci.edu/dataset/967/phiusil-phishing-url-dataset)")
        st.caption("CSV labels: 0 = Phishing, 1 = Legitimate. Model target reverses this: 1 = Phishing.")
    chart = go.Figure(go.Bar(x=list(data["raw_class_counts"]), y=list(data["raw_class_counts"].values()),
                             marker_color=[PHISH, LEGIT], text=list(data["raw_class_counts"].values()), textposition="outside"))
    style(chart, "Recorded classes in the source dataset", "CSV class", "Raw records", 340)
    chart.update_yaxes(range=[0, max(data["raw_class_counts"].values()) * 1.16])
    figure(chart.to_plotly_json(), "overview_classes")
    st.divider()
    st.subheader("Cleaning decisions, with a record of the changes")
    st.write("The main notebook removes exact duplicates, trims URL whitespace, excludes conflicting URL labels and keeps the first same-label URL repeat. It preserves path case. A separate lowercase hostname supports grouping; distinct pages on the same host remain in the descriptive URL table.")
    st.dataframe(pd.DataFrame(data["quality"]), hide_index=True, width="stretch")
    st.write("For the main hypothesis tests, mixed-label hosts are excluded and one URL is randomly selected per remaining exact hostname. This reduces repeated-host weighting. It does not establish that related subdomains or campaigns are independent.")
    with st.expander("Repeated observations: why the notebooks use different grains"):
        st.dataframe(pd.DataFrame([
            {"Audit": "Repeated source URL rows beyond first occurrence", "Records": data["repeated_url_rows"]},
            {"Audit": "Repeated source Domain rows beyond first occurrence", "Records": data["repeated_domain_rows"]},
            {"Audit": "Duplicate feature rows after excluding FILENAME", "Records": data["duplicate_rows_without_filename"]},
            {"Audit": "Eligible hosts containing multiple distinct URLs", "Records": data["hosts_with_multiple_urls"]},
        ]), hide_index=True, width="stretch")
        st.write("Plots.ipynb retains repeated URLs/domains for raw-record EDA. The statistical notebook deliberately chooses unique URLs and a host sample. Repetition is an observation-grain decision, not automatic evidence that a row is invalid.")
    st.markdown("#### Missing values and unusual values")
    st.write(f"There are {data['missing_cells']:,} missing cells in the supplied dataset. The original checks reject invalid labels, infinite numeric values and negative count values. The IQR screen flags unusual values; flagged observations remain in the analysis.")
    st.dataframe(pd.DataFrame(data["outliers"]), hide_index=True, width="stretch")
    st.subheader("Inspect the source records")
    filters = st.columns([1, 1, 2])
    class_filter = filters[0].selectbox("Recorded class", ["All", "Phishing (0)", "Legitimate (1)"])
    page_size = filters[1].selectbox("Rows per page", [25, 50, 100])
    search = filters[2].text_input("Find text in URL or domain", placeholder="A literal substring; URLs are never visited")
    label = None if class_filter == "All" else 0 if class_filter == "Phishing (0)" else 1
    _, count = service.preview(1, page_size, label, search)
    pages = max(1, math.ceil(count / page_size))
    if st.session_state.get("preview_page", 1) > pages:
        st.session_state["preview_page"] = pages
    page = st.number_input("Page", min_value=1, max_value=pages, step=1, key="preview_page")
    preview, count = service.preview(page, page_size, label, search)
    show_all = st.checkbox("Show all source columns")
    columns = list(preview.columns) if show_all else ["FILENAME", "URL", "Domain", "TLD", "URLLength", "IsHTTPS", "label"]
    st.dataframe(preview[columns], hide_index=True, width="stretch",
                 column_config={"URL": st.column_config.TextColumn("URL (text only)")})
    st.caption(f"Page {page:,} / {pages:,} · {count:,} matching raw records. No URL is opened by this application.")
    st.download_button("Download this preview page", preview[columns].to_csv(index=False).encode(),
                       "phiusil_preview.csv", "text/csv")
    with st.expander("Feature dictionary"):
        st.dataframe(pd.DataFrame(data["dictionary"]), hide_index=True, width="stretch")
    source_footer("Primary source: Department_Of_Phisheries.ipynb · raw inspection, cleaning, unique URLs and host sampling reproduced from its code.")


def eda(service):
    hero(2, "Read the shape of the data.",
         "Twelve selected views from Plots.ipynb, preserving its samples, transformations and class mapping. These views use raw source records, with repeated URLs and domains retained.")
    options = list(range(len(service.eda)))
    st.selectbox("Select a notebook plot", options,
                 format_func=lambda i: f"Plot {service.eda[i]['number']} — {service.eda[i]['title']}", key="eda_index")
    index = st.session_state.eda_index
    a, b, c = st.columns([1, 2, 1])
    a.button("Previous Plot", disabled=index == 0, on_click=move_selection,
             args=("eda_index", -1, len(options) - 1, 0))
    b.caption(f"Plot {index + 1:02d} of {len(options):02d} · original notebook Plot {service.eda[index]['number']}")
    c.button("Next Plot", disabled=index == len(options) - 1, on_click=move_selection,
             args=("eda_index", 1, len(options) - 1, 0))
    st.progress((index + 1) / len(options))
    plot = service.eda[index]
    figure(plot["figure"], f"eda_{plot['number']}")
    st.caption(plot["sample_note"])
    st.markdown("#### How to read this view")
    st.markdown(plot["interpretation"])
    if plot["number"] == 8:
        st.info("The class-aligned similarity score is a feature-provenance warning. This chart does not prove how it was constructed or that leakage occurred.")
    if plot["number"] == 24:
        st.caption("Source clarification: the original title reverses its high/low color description. This view uses a correctly labeled 0–1 colorbar; the source rates are unchanged.")
    if plot["table"]:
        with st.expander("Underlying calculated values"):
            st.dataframe(pd.DataFrame(plot["table"]), hide_index=True, width="stretch")
    related = plot["linked_questions"]
    st.caption("Related analysis: " + ", ".join(f"Q{q}" for q in related))
    st.button(f"Continue to Q{related[0]}", on_click=go_to, args=("questions", related[0]))
    original_view(plot, "Plots.ipynb")
    source_footer("Selected for analytical relevance; all 23 original figures were inspected. Redundant and technique-only examples remain in the original notebook.")


def questions(service):
    hero(3, "The original questions, one at a time.",
         "The wording and numbering below come directly from Department_Of_Phisheries.ipynb. Each view connects the actual calculation to its chart and statistical evidence.")
    question = question_selector(service, "question_number")
    st.subheader(question["heading"])
    st.caption("Columns: " + " · ".join(question["columns"]))
    st.markdown("#### Method and justification")
    st.write(question["method"])
    st.caption("Sample: " + question["test"]["Scope"])
    st.dataframe(pd.DataFrame(question["tables"]), hide_index=True, width="stretch")
    figure(question["figure"], f"question_{question['number']}")
    if question["number"] == 15:
        st.dataframe(pd.DataFrame(service.study["rule_summary"]), hide_index=True, width="stretch")
        st.info(f"Correction to the source narrative: Rule B avoids {service.study['avoided_alerts']:,} false alerts here and misses {service.study['extra_missed']:,} more phishing hosts. Use the observed error counts above.")
    st.markdown("#### Result and interpretation")
    st.write(question["interpretation"])
    st.caption(question["assumptions"])
    st.button(f"Open the hypothesis test for Q{question['number']}", type="primary",
              on_click=go_to, args=("evidence", question["number"]))
    original_view(question, "Department_Of_Phisheries.ipynb")
    source_footer(f"Original heading preserved · source markdown cell {question['source_cell']} · test verified against the notebook's saved statistic and p-value display.")


def evidence(service):
    hero(4, "From observation to evidence.",
         "The same 15 questions and their original hypotheses, methods, statistics and decisions. Reproduced results were checked against every saved notebook test output.")
    with st.expander("All tests at a glance"):
        frame = pd.DataFrame([q["test"] for q in service.questions])
        st.dataframe(frame[["Question", "Feature", "Test", "Statistic", "PValueDisplay", "Decision"]], hide_index=True, width="stretch")
        st.download_button("Download verified test evidence", (ARTIFACTS / "bi/statistical_evidence.csv").read_bytes(),
                           "statistical_evidence.csv", "text/csv")
    q = question_selector(service, "evidence_number")
    result = q["test"]
    st.subheader(q["heading"])
    st.markdown("#### The hypotheses, as stated in the notebook")
    st.markdown(q["null"])
    st.markdown(q["alternative"])
    a, b, c, d = st.columns(4)
    a.metric("Test statistic", f"{result['Statistic']:,.4f}")
    b.metric("p-value", result["PValueDisplay"])
    c.metric("Significance level", f"{result['alpha']:.2f}")
    df = result.get("DegreesOfFreedom")
    d.metric("Degrees of freedom", "Not used" if df is None else f"{df:,.2f}")
    st.caption("Below numerical precision means floating-point underflow, not an exact probability of zero. All p-values are raw exploratory values; no adjustment is introduced.")
    st.markdown(f"#### Statistical decision: {result['Decision']}")
    st.write(q["method"])
    if result.get("MinimumExpectedCount") is not None:
        st.write(f"The smallest expected contingency-table count is {result['MinimumExpectedCount']:,.2f}; the notebook checks that it is at least 5.")
    st.markdown("#### Observed result → test → decision → interpretation")
    st.dataframe(pd.DataFrame(q["tables"]), hide_index=True, width="stretch")
    st.write(q["interpretation"])
    st.caption("Assumptions: " + q["assumptions"])
    st.write("A small p-value does not measure practical importance, the probability that H0 is true, or whether a particular new URL is phishing. These comparisons do not establish causation.")
    st.button(f"Return to Q{q['number']} and its visualization", on_click=go_to, args=("questions", q["number"]))
    with st.expander("Trace this test to the original implementation"):
        st.code(q["code"], language="python")
        st.text(q["saved_output"])
    source_footer("Source: Department_Of_Phisheries.ipynb · df recovered from the same SciPy result where applicable; no new test, hypothesis or p-value substituted.")


FEATURE_LABELS = {
    "URLLength": "URL length · characters", "DomainLength": "Domain length · characters",
    "NoOfSubDomain": "Number of subdomains", "NoOfImage": "Images", "NoOfCSS": "CSS files",
    "NoOfJS": "JavaScript files", "IsHTTPS": "HTTPS scheme", "HasTitle": "Page title",
    "HasFavicon": "Favicon", "HasSocialNet": "Social links", "HasExternalFormSubmit": "External form submission",
}


def fill_inputs(service, model_id):
    sample = service.random_fill(model_id)
    for feature, value in sample["features"].items():
        st.session_state["input_" + feature] = value
    st.session_state["input_origin"] = sample["source"]
    st.session_state.pop("prediction_result", None)


def models(service):
    hero(5, "A supporting model comparison.",
         "Four classifiers actually trained in Model_Evaluation.ipynb, with the majority baseline kept for context. Every reported table value matches the saved notebook evaluation.")
    table = pd.DataFrame(service.study["model_comparison"])
    metrics = ["Model", "Accuracy", "BalancedAccuracy", "Precision", "Recall", "F1", "FalsePositiveRate"]
    st.dataframe(table[metrics], hide_index=True, width="stretch",
                 column_config={key: st.column_config.NumberColumn(key, format="%.4f") for key in metrics[1:]})
    st.caption("Metrics are fractions, displayed at the notebook's four-decimal precision. Precision/recall refer to phishing = 1. Four classifiers plus baseline are preserved, including Naive Bayes added in the executable notebook code.")
    options = [m["id"] for m in service.study["models"]]
    names = {m["id"]: m["name"] for m in service.study["models"]}
    if "selected_model" not in st.session_state:
        st.session_state["selected_model"] = "logistic_regression"
    model_id = st.selectbox("Select a notebook model", options, format_func=names.get, key="selected_model")
    model = next(m for m in service.study["models"] if m["id"] == model_id)
    left, right = st.columns(2)
    matrix = go.Figure(go.Heatmap(z=model["confusion"], x=["Legitimate", "Phishing"], y=["Legitimate", "Phishing"],
                                 texttemplate="%{z:,}", colorscale=[[0, "#edf0e8"], [1, "#286153"]], showscale=False))
    style(matrix, "Verified test confusion matrix", "Predicted class", "Recorded class", 390)
    matrix.update_yaxes(autorange="reversed")
    with left:
        figure(matrix.to_plotly_json(), "model_confusion_" + model_id)
    roc = go.Figure()
    colors = ["#b78038", "#4f8261", "#2e7197", "#8c678b"]
    for card, color in zip(service.study["models"], colors):
        roc.add_trace(go.Scatter(x=card["roc"]["fpr"], y=card["roc"]["tpr"], mode="lines",
                                name=f"{card['name']} · AUC {card['auc']:.4f}", line=dict(color=color)))
    roc.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Random classifier reference",
                            line=dict(color="#8c978e", dash="dash")))
    style(roc, "Notebook ROC comparison", "False-positive rate", "Phishing recall", 470)
    roc.update_layout(legend=dict(orientation="h", y=-0.3, yanchor="top", font=dict(size=10)), margin=dict(b=100))
    with right:
        figure(roc.to_plotly_json(), "model_roc")
    st.caption("Correction: the original confusion figure swaps the logistic/pruned subplot titles and reverses labels on three matrices. The matrices above use each model's own predictions and target mapping 0 = legitimate, 1 = phishing.")
    with st.expander("Training design, original reports and model details"):
        st.dataframe(pd.DataFrame(service.study["model_partitions"]), hide_index=True, width="stretch")
        st.write(service.study["model_verification"]["split"])
        st.write(model["preprocessing"])
        st.json(model["parameters"])
        st.write(f"Exact host overlap: {service.study['model_verification']['train_test_host_overlap']}. Shared normalized source Domain values: {service.study['model_verification']['shared_source_domain_values']}.")
        st.caption("Grouping exact hosts reduces one leakage path. Related subdomains/campaigns and collection artifacts remain possible; this is not a future-dated external validation.")
        st.text(service.study["model_source_reports"])
        st.markdown("**Original model figures, retained for audit**")
        for path in service.study["model_original_figures"]:
            if (ARTIFACTS / path).is_file():
                st.image((ARTIFACTS / path).read_bytes(), width="stretch")
        st.code(service.study["model_code"], language="python")
    st.divider()
    st.subheader("Try an actual model prediction")
    st.write("Enter the model's eleven numerical webpage features, or fill them together from one real held-out dataset row. This interface does not fetch a URL or extract features from a website.")
    if "input_origin" not in st.session_state or any("input_" + field["name"] not in st.session_state for field in service.study["schema"]):
        fill_inputs(service, model_id)
    st.button("Random Fill", on_click=fill_inputs, args=(service, model_id))
    st.caption("Inputs: " + st.session_state.get("input_origin", "Manual entry"))
    with st.form("prediction_form"):
        columns = st.columns(3)
        for index, field in enumerate(service.schema(model_id)):
            with columns[index % 3]:
                label = FEATURE_LABELS[field["name"]]
                key = "input_" + field["name"]
                if field["kind"] == "binary":
                    st.selectbox(label, [0, 1], format_func=lambda v: "Present / yes (1)" if v else "Absent / no (0)", key=key)
                else:
                    st.number_input(label, min_value=field["minimum"], max_value=field["maximum"], step=1,
                                     key=key, help=f"Observed dataset range: {field['minimum']}–{field['maximum']}")
        submitted = st.form_submit_button("Predict", type="primary")
    if submitted:
        values = {field["name"]: st.session_state["input_" + field["name"]] for field in service.schema(model_id)}
        try:
            with st.spinner("Running the fitted notebook model…"):
                st.session_state["prediction_result"] = service.predict(model_id, values)
        except (InputError, ValueError) as error:
            st.session_state.pop("prediction_result", None)
            st.error(str(error))
    result = st.session_state.get("prediction_result")
    if result and result["model_id"] == model_id:
        st.markdown("### Model prediction: " + result["prediction"])
        st.write(f"Estimated phishing probability: **{result['phishing_probability']:.4%}**. Estimated legitimate probability: **{result['legitimate_probability']:.4%}**.")
        st.caption("These are the selected model's estimates, not independently calibrated real-world safety probabilities.")
        for text in result["explanation"]:
            st.write("• " + text)
        st.caption(result["scope"])
        st.download_button("Download this prediction", json.dumps(result, indent=2).encode(), "model_prediction.json", "application/json")
    source_footer("Model_Evaluation.ipynb · original features, order, split, preprocessing and parameters retained · inference runs on fitted serialized models.")


def bi_section():
    with st.expander("Power BI connection and verified data exports"):
        st.write("The native website works independently. The existing server.py is retained as the genuine local Power BI data connector and an optional inference API.")
        st.code("python backend/server.py", language="powershell")
        st.write("Open powerbi/Phisheries.pbip, keep UseBackend=true while the server runs, use Anonymous credentials for localhost, and refresh. With UseBackend=false, use the regenerated outputs/powerbi folder.")
        st.markdown("[Local backend health](http://127.0.0.1:8765/health) · [Verified statistical evidence API](http://127.0.0.1:8765/api/evidence)")
        st.caption("The links work when the optional backend is running. This is import/refresh, not a live streaming report. Publishing to Power BI Service requires your workspace/report configuration and a hosted source or gateway.")
        embed = os.environ.get("POWERBI_EMBED_URL", "")
        if embed:
            parsed = urlsplit(embed)
            if parsed.scheme == "https" and parsed.hostname == "app.powerbi.com" and parsed.path.startswith(("/reportEmbed", "/view")):
                st.caption("Configured report embed: access and authentication are controlled by your Power BI tenant. External report access was not verified locally.")
                components.iframe(embed, height=650, scrolling=True)
            else:
                st.error("POWERBI_EMBED_URL must be an HTTPS Power BI reportEmbed or view URL on app.powerbi.com.")
        else:
            st.write("No hosted report is configured. The working integration is the tested CSV/JSON backend; no placeholder iframe is shown.")


def conclusion(service):
    data = service.study
    hero(6, "What the investigation supports.",
         "Observed findings, practical recommendations and future work are kept distinct. The project remains a statistical case study, with classifiers as supporting evidence.")
    q1, q3, q15 = service.question(1), service.question(3), service.question(15)
    st.subheader("A contextual review dashboard is the justified next step")
    st.write(f"Cleaning retains {data['unique_urls']:,} unique URLs from {data['raw_rows']:,} source rows. The main test sample contains {data['inference_hosts']:,} consistently labeled exact hosts. Plots.ipynb deliberately keeps all source rows for descriptive EDA, so its denominators differ.")
    st.markdown("#### Findings demonstrated by the supplied data")
    st.write(f"Phishing URL lengths average {q1['test']['Estimate']:.2f} more characters in the host sample. The distributions still overlap. The subdomain-count gap is only {q3['test']['Estimate']:.3f}, illustrating why a tiny p-value alone is not a useful rule.")
    st.write("Feature-presence rates and page-content counts differ strongly between the recorded classes. The raw-record EDA also shows class-aligned URL structure and supplied feature scores. These observations warrant a source and feature-provenance audit before making wider claims.")
    st.write(f"The paired rule test changes correctness by {q15['test']['Estimate']:.3f} percentage points for B minus A. Rule B misses {data['extra_missed']:,} more phishing hosts and avoids {data['avoided_alerts']:,} false alerts here. This corrects the source narrative claiming a false-alarm reduction.")
    st.markdown("#### The supporting models")
    st.dataframe(pd.DataFrame(data["model_comparison"])[["Model", "Accuracy", "Precision", "Recall", "F1"]],
                 hide_index=True, width="stretch")
    st.write("All four classifier results reproduce the saved notebook table. Strong internal test scores do not establish safety on future web traffic. Exact hosts are separated, but related domains and collection artifacts remain possible.")
    st.markdown("#### Practical recommendation")
    st.write("Display indicators with their denominators, show the costs of missed phishing and unnecessary review, and use the evidence to support human investigation. These notebooks do not establish a universal automatic blocking policy.")
    st.markdown("#### Limitations and future work")
    st.write("The benchmark is observational and has no dates, user outcomes or financial-loss data. Multiple exploratory tests increase false-discovery risk. Q13–Q14 concern their declared subsamples; Q15 uses a large-sample paired t approximation. Related sites may remain dependent.")
    st.write("Collect an independently sourced, dated sample; audit feature construction and page retrieval; improve grouping of related sites; agree on operational error costs; and run the proposed randomized participant study of contextual warnings. That A/B user experiment has not been conducted.")
    with st.expander("Transparent corrections and source verification"):
        for correction in data["corrections"]:
            st.markdown("**" + correction["source"] + "**")
            st.write(correction["issue"])
            st.caption(correction["correction"])
        st.dataframe(pd.DataFrame(data["statistical_verification"]), hide_index=True, width="stretch")
        st.json({"model_verification": data["model_verification"], "source_hashes": service.manifest["notebooks"],
                 "environment": service.manifest["environment"]})
    bi_section()
    st.divider()
    st.subheader("The project team")
    st.caption("Four editable sections. Names and portraits stay neutral until you supply them. Changes are saved in this project's local SQLite database.")
    members = team.members()
    saved_id = st.session_state.pop("team_saved_id", None)
    if saved_id:
        st.success(f"Member {saved_id:02d} saved.")
    columns = st.columns(4)
    for column, member in zip(columns, members):
        with column:
            st.markdown(f"#### Member {member['id']:02d}")
            if member["photo"]:
                st.image(member["photo"], width="stretch")
            else:
                st.markdown('<div class="portrait-placeholder">Portrait to be added</div>', unsafe_allow_html=True)
            with st.container():
                revision = st.session_state.get(f"photo_revision_{member['id']}", 0)
                name = st.text_input("Name", value=member["name"], key=f"team_name_{member['id']}", placeholder="Your name")
                register = st.text_input("Register number (optional)", value=member["register_number"], key=f"team_register_{member['id']}")
                role = st.text_input("Role (optional)", value=member["role"], key=f"team_role_{member['id']}")
                upload = st.file_uploader("Upload or replace photo", type=["jpg", "jpeg", "png"], key=f"team_photo_{member['id']}_{revision}")
                if upload:
                    try:
                        preview = team.prepare_photo(upload.getvalue())
                        st.image(preview, caption="New photo preview", width="stretch")
                    except ValueError as error:
                        st.error(str(error))
                remove = st.checkbox("Remove saved photo", key=f"remove_photo_{member['id']}_{revision}")
                if st.button("Save member", key=f"save_member_{member['id']}"):
                    try:
                        team.save_member(member["id"], name, register, role,
                                         upload.getvalue() if upload else None, remove_photo=remove)
                        st.session_state[f"photo_revision_{member['id']}"] = revision + 1
                        st.session_state["team_saved_id"] = member["id"]
                        st.rerun()
                    except ValueError as error:
                        st.error(str(error))
    with st.expander("Project files and references"):
        for path in NOTEBOOKS.values():
            st.download_button("Download " + path.name, path.read_bytes(), path.name, "application/x-ipynb+json", key="download_" + path.stem)
        st.markdown("[UCI PhiUSIIL dataset](https://archive.ics.uci.edu/dataset/967/phiusil-phishing-url-dataset) · [Original study](https://doi.org/10.1016/j.cose.2023.103545)")
        st.write("Course: 23CSE351 Foundations of Data Science. The original questions and course methods are retained. See README.md, docs/SOURCE_AUDIT.md and docs/TEST_REPORT.md for setup, provenance and checks.")
    source_footer("Prepared from all three original notebooks · no unrelated dataset, fabricated outcome or completed user experiment is presented.")
