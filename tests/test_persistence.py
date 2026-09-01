import unittest
import tempfile
from unittest.mock import patch

import streamlit as st

from utils.db import SQLiteDB
from utils.persistence import load_session_record
from utils.session import DEFAULT_SESSION_STATE, create_new_study, init_session


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        st.session_state.clear()

    def test_durable_session_keys_are_registered(self):
        self.assertIn("project_name", DEFAULT_SESSION_STATE)
        self.assertIn("field_name", DEFAULT_SESSION_STATE)
        self.assertIn("team_members", DEFAULT_SESSION_STATE)

    def test_load_session_record_uses_project_and_field(self):
        with patch("utils.persistence.load_session", return_value=True) as mock_load:
            result = load_session_record({"project_name": "Alpha", "field_name": "Beta"})

        self.assertTrue(result)
        mock_load.assert_called_once_with("Alpha", "Beta")

    def test_load_session_record_rejects_missing_metadata(self):
        with patch("utils.persistence.load_session", return_value=True) as mock_load:
            result = load_session_record({"project_name": "", "field_name": "Beta"})

        self.assertFalse(result)
        mock_load.assert_not_called()

    def test_create_new_study_clears_existing_workspace(self):
        init_session()
        original_id = st.session_state["study_id"]
        st.session_state["project_name"] = "Existing Study"
        st.session_state["field_name"] = "Existing Field"
        st.session_state["uncertainties"][0]["selected"] = True
        st.session_state["study_mode"] = "loaded"

        create_new_study()

        self.assertNotEqual(st.session_state["study_id"], original_id)
        self.assertEqual(st.session_state["project_name"], "")
        self.assertEqual(st.session_state["field_name"], "")
        self.assertFalse(st.session_state["uncertainties"][0]["selected"])
        self.assertEqual(st.session_state["study_mode"], "new")
        self.assertEqual(st.session_state["current_page"], "📋 Overview")

    def test_sqlite_round_trip_preserves_study_payload_and_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            database = SQLiteDB()
            database.db_path = f"{directory}\\roundtrip.db"
            database.init()
            payload = {
                "project_name": "Alpha",
                "field_name": "Beta",
                "project_phase": "PGR1",
                "team_members": [{"Name": "Engineer", "Function / Role": "RE", "Date": "19/08/2026"}],
                "key_decisions": [{"Key Decision": "Well placement", "Weight (1-3)": 3, "Description": ""}],
            }
            record = {
                "session": payload,
                "meta": {
                    "project_phase": "PGR1",
                    "completion": 50,
                    "auto_saved": False,
                    "saved_at": "2026-08-19T00:00:00",
                },
            }

            self.assertTrue(database.save("Alpha", "Beta", record))
            loaded = database.load("Alpha", "Beta")

        self.assertEqual(loaded["session"], payload)
        self.assertEqual(loaded["meta"]["project_name"], "Alpha")
        self.assertEqual(loaded["meta"]["field_name"], "Beta")
        self.assertEqual(loaded["meta"]["project_phase"], "PGR1")

    def test_sqlite_list_includes_lifecycle_revision_and_last_editor(self):
        with tempfile.TemporaryDirectory() as directory:
            database = SQLiteDB()
            database.db_path = f"{directory}\\repository.db"
            database.init()
            record = {
                "session": {
                    "project_name": "Alpha",
                    "field_name": "Beta",
                    "study_lifecycle": "In Review",
                    "study_revision": 3,
                    "study_change_log": [{
                        "revision": 3,
                        "saved_at": "2026-09-01T12:30:00",
                        "actor": "Engineer A",
                        "action": "save",
                    }],
                },
                "meta": {
                    "project_phase": "PGR2",
                    "completion": 75,
                    "auto_saved": False,
                    "saved_at": "2026-09-01T12:30:00",
                    "study_id": "study-alpha",
                    "study_owner": "Engineer A",
                },
            }
            self.assertTrue(database.save("Alpha", "Beta", record))
            summaries = database.list_all()

        self.assertEqual(summaries[0]["study_lifecycle"], "In Review")
        self.assertEqual(summaries[0]["study_revision"], 3)
        self.assertEqual(summaries[0]["last_edited_by"], "Engineer A")
        self.assertEqual(summaries[0]["last_edited_at"], "2026-09-01T12:30:00")


if __name__ == "__main__":
    unittest.main()
