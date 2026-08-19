import unittest

from utils.analytics import build_relationships, build_study_analytics
from utils.workflow import completion_percent, current_stage, validate_stage


def study_fixture():
    return {
        "project_name": "Alpha",
        "uncertainties": [
            {"name": "Fault seal", "selected": True, "discipline": "Geology"},
            {"name": "Ignored", "selected": False, "discipline": "Geophysics"},
        ],
        "key_decisions": [{"Key Decision": "Well placement", "Weight (1-3)": 3}],
        "impact_assessment": [{"Uncertainty": "Fault seal", "Well placement": "H"}],
        "key_uncertainties": [{"Uncertainty": "Fault seal", "Include in Plan": True, "Rank": 1, "Impact (Weighted)": 2.8}],
        "resolution_list": {"Fault seal": {"Pressure transient analysis": "Y"}},
        "resolution_planner": [{"Resolution Action": "Pressure transient analysis", "Status": "In Progress"}],
        "risk_register": [{"Risk": "Poor well positioning", "Uncertainty/Causes": "1. Fault seal"}],
    }


class WorkflowAnalyticsTests(unittest.TestCase):
    def test_stage_validation_protects_downstream_pages(self):
        session = {"uncertainties": [], "key_decisions": []}
        allowed, reason = validate_stage(session, "key_decisions")
        self.assertFalse(allowed)
        self.assertIn("uncertainty", reason)
        self.assertEqual(current_stage(session).key, "uncertainties")

    def test_relationships_trace_uncertainty_to_decision_and_risk(self):
        relationships = build_relationships(study_fixture())
        targets = {item["target"] for item in relationships}
        self.assertEqual(targets, {"Well placement", "Poor well positioning"})

    def test_analytics_reports_progress_and_status(self):
        analytics = build_study_analytics(study_fixture())
        self.assertEqual(analytics["completion"], 100)
        self.assertEqual(analytics["resolution_status"], {"In Progress": 1})
        self.assertEqual(analytics["critical_uncertainties"], ["Fault seal"])
        self.assertEqual(completion_percent(study_fixture()), 100)


if __name__ == "__main__":
    unittest.main()