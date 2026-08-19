import unittest
import tempfile
from unittest.mock import patch

from utils.db import SQLiteDB
from utils.persistence import load_session_record
from utils.session import DEFAULT_SESSION_STATE


class PersistenceTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
