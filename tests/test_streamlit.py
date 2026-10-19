import os
from pathlib import Path
import tempfile
import unittest

from streamlit.testing.v1 import AppTest

from case_study.config import ROOT
from case_study.views import PAGES
from case_study import team


class StreamlitDashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.database = Path(cls.temporary.name) / "team.sqlite3"
        cls.previous = os.environ.get("PHISHERIES_TEAM_DB")
        os.environ["PHISHERIES_TEAM_DB"] = str(cls.database)

    @classmethod
    def tearDownClass(cls):
        if cls.previous is None:
            os.environ.pop("PHISHERIES_TEAM_DB", None)
        else:
            os.environ["PHISHERIES_TEAM_DB"] = cls.previous
        cls.temporary.cleanup()

    def app(self):
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=60).run()
        self.assertEqual(len(app.exception), 0, [e.message for e in app.exception])
        return app

    def button(self, app, label):
        return next(button for button in app.button if button.label == label)

    def navigate(self, app, page):
        app.radio(key="navigation").set_value(PAGES[page]).run()
        self.assertEqual(len(app.exception), 0, [e.message for e in app.exception])

    def test_all_six_dashboards_and_question_evidence_link(self):
        app = self.app()
        self.assertEqual(len(app.radio(key="navigation").options), 6)
        for page in PAGES:
            self.navigate(app, page)
        self.navigate(app, "questions")
        for number in range(1, 16):
            app.selectbox(key="question_number").set_value(number).run()
            self.assertEqual(len(app.exception), 0)
        self.button(app, "Open the hypothesis test for Q15").click().run()
        self.assertEqual(app.radio(key="navigation").value, PAGES["evidence"])
        self.assertEqual(app.selectbox(key="evidence_number").value, 15)
        self.button(app, "Return to Q15 and its visualization").click().run()
        self.assertEqual(app.radio(key="navigation").value, PAGES["questions"])

    def test_eda_navigation_and_all_selected_plots(self):
        app = self.app()
        self.navigate(app, "eda")
        self.assertEqual(app.selectbox(key="eda_index").value, 0)
        self.button(app, "Next Plot").click().run()
        self.assertEqual(app.selectbox(key="eda_index").value, 1)
        self.button(app, "Previous Plot").click().run()
        self.assertEqual(app.selectbox(key="eda_index").value, 0)
        for index in range(12):
            app.selectbox(key="eda_index").set_value(index).run()
            self.assertEqual(len(app.exception), 0)

    def test_random_fill_and_predict_with_every_classifier(self):
        app = self.app()
        self.navigate(app, "models")
        options = list(app.selectbox(key="selected_model").options)
        self.assertEqual(len(options), 4)
        for model_id in ["naive_bayes", "pruned_tree", "logistic_regression", "full_tree"]:
            app.selectbox(key="selected_model").set_value(model_id).run()
            self.button(app, "Random Fill").click().run()
            self.button(app, "Predict").click().run()
            self.assertEqual(len(app.exception), 0, [e.message for e in app.exception])
            self.assertEqual(len(app.error), 0)
            self.assertEqual(app.session_state["prediction_result"]["model_id"], model_id)
        app.number_input(key="input_URLLength").set_value(13)
        app.number_input(key="input_DomainLength").set_value(110)
        self.button(app, "Predict").click().run()
        self.assertGreater(len(app.error), 0)

    def test_team_name_register_role_save_and_four_photo_controls(self):
        app = self.app()
        self.navigate(app, "conclusion")
        self.assertEqual(len(app.get("file_uploader")), 4)
        app.text_input(key="team_name_1").set_value("QA member")
        app.text_input(key="team_register_1").set_value("QA-01")
        app.text_input(key="team_role_1").set_value("Verification")
        app.button(key="save_member_1").click().run()
        self.assertEqual(len(app.exception), 0)
        saved = team.members(self.database)[0]
        self.assertEqual(saved["name"], "QA member")
        self.assertEqual(saved["register_number"], "QA-01")
        self.assertEqual(saved["role"], "Verification")


if __name__ == "__main__":
    unittest.main(verbosity=2)
