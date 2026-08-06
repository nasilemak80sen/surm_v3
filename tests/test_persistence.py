import unittest
from unittest.mock import patch

from utils.persistence import load_session_record


class PersistenceTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
