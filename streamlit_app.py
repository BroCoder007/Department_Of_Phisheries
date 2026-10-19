"""Run with: python -m streamlit run streamlit_app.py"""

from pathlib import Path
import subprocess
import sys

import streamlit as st

st.set_page_config(page_title="Department of Phisheries", layout="wide", initial_sidebar_state="auto")

ROOT = Path(__file__).resolve().parent
st.markdown("<style>" + (ROOT / "assets/theme.css").read_text(encoding="utf-8") + "</style>", unsafe_allow_html=True)

try:
    from case_study import views
    from case_study.service import StudyService, SnapshotError, snapshot_signature
except ModuleNotFoundError as error:
    st.error(f"A required dependency is missing: {error.name}")
    st.code("python -m pip install -r requirements.txt")
    st.stop()


@st.cache_resource(show_spinner=False)
def load_verified(signature):
    return StudyService()


with st.sidebar:
    st.markdown('<div class="side-kicker">23CSE351 / Foundations of Data Science</div><div class="side-brand">Department<br>of Phisheries</div>', unsafe_allow_html=True)
    st.markdown("A notebook-led investigation of phishing URL indicators.")
    st.divider()
    if "navigation" not in st.session_state:
        selected = st.query_params.get("view", "overview")
        st.session_state["navigation"] = views.PAGES.get(selected, views.PAGES["overview"])
    navigation = st.radio("Study contents", list(views.PAGES.values()), key="navigation", label_visibility="collapsed")
    st.divider()
    st.markdown("**The evidence comes first.**\n\nPreprocessing, original questions and statistical reasoning lead the study. Models support the investigation.")

try:
    service = load_verified(snapshot_signature())
except (SnapshotError, FileNotFoundError, ValueError) as error:
    views.hero(1, "Prepare the notebook evidence.", "This app displays verified notebook calculations. It does not substitute example statistics when a source or prepared result is missing.")
    st.error(str(error))
    st.code("python -m pip install -r requirements.txt\npython -m case_study.prepare\npython -m streamlit run streamlit_app.py", language="powershell")
    if st.button("Prepare notebook results", type="primary"):
        try:
            with st.spinner("Reproducing the trusted local notebooks and checking their outputs…"):
                process = subprocess.run([sys.executable, "-u", "-m", "case_study.prepare"], cwd=ROOT,
                                         capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            st.error("Preparation exceeded five minutes. Run python -m case_study.prepare in a terminal to inspect progress.")
            st.stop()
        if process.returncode == 0:
            load_verified.clear()
            st.rerun()
        else:
            st.error("Preparation failed. No replacement scores were published.")
            st.code(process.stdout + process.stderr)
    st.stop()

page = next(key for key, label in views.PAGES.items() if label == navigation)
st.query_params["view"] = page
with st.sidebar:
    st.caption(f"{len(service.questions)} original questions · {len(service.eda)} selected EDA views\n\n{len(service.study['models'])} classifiers reproduced and verified")

try:
    getattr(views, page)(service)
except (ValueError, OSError, SnapshotError) as error:
    st.error("This view could not be completed: " + str(error))
    st.caption("Check the local files and configuration. Other dashboards remain available from the sidebar.")
