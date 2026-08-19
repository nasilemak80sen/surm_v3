import unittest

from utils.study_document import StudyDocument


class StudyDocumentTests(unittest.TestCase):
    def test_legacy_record_does_not_invent_or_drop_saved_identity(self):
        document = StudyDocument.from_record({
            "session": {"study_revision": 4},
            "meta": {
                "project_name": "Alpha",
                "field_name": "Beta",
                "project_phase": "PGR1",
            },
        })

        self.assertEqual(document.project_name, "Alpha")
        self.assertEqual(document.field_name, "Beta")
        self.assertEqual(document.project_phase, "PGR1")
        self.assertEqual(document.study_revision, 4)
        self.assertEqual(document.team_members, [])

    def test_document_round_trip_preserves_relationship_entities(self):
        source = {
            "study_id": "study-1",
            "project_name": "Alpha",
            "field_name": "Beta",
            "resolution_list": {"Fault seal": {"Pressure study": "Y"}},
            "risk_register": [{"Risk": "Poor placement"}],
        }

        document = StudyDocument.from_session(source)
        restored = StudyDocument.from_session(document.to_dict())

        self.assertEqual(restored.study_id, "study-1")
        self.assertEqual(restored.resolution_list, source["resolution_list"])
        self.assertEqual(restored.risk_register, source["risk_register"])


if __name__ == "__main__":
    unittest.main()