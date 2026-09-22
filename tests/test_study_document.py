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

def test_governance_metadata_and_signoffs_round_trip():
    document = StudyDocument.from_session({
        "study_id": "study-governance",
        "project_name": "Governance Project",
        "field_name": "Governance Field",
        "methodology_version": "SURM-2026.01",
        "prep_name": "Prepared Person",
        "prep_role": "Engineer",
        "prep_date": "22/09/2026",
        "rev_gg_name": "G&G Reviewer",
        "rev_gg_role": "G&G Lead",
        "rev_gg_date": "23/09/2026",
        "rev_re_name": "RE Reviewer",
        "rev_re_role": "RE Lead",
        "rev_re_date": "24/09/2026",
        "rev_pp_name": "PP Reviewer",
        "rev_pp_role": "PP Lead",
        "rev_pp_date": "25/09/2026",
        "endorsed_name": "FDP Lead",
        "endorsed_role": "FDP Lead",
        "endorsed_date": "26/09/2026",
        "workflow_revisions": {"impact_assessment": 3},
        "workflow_snapshots": {
            "impact_assessment": {"revision": 3},
        },
    })

    restored = StudyDocument.from_record({
        "session": document.to_dict(),
        "meta": {},
    })

    assert restored.prep_name == "Prepared Person"
    assert restored.rev_gg_role == "G&G Lead"
    assert restored.rev_re_date == "24/09/2026"
    assert restored.endorsed_name == "FDP Lead"
    assert restored.methodology_version == "SURM-2026.01"
    assert restored.workflow_revisions == {"impact_assessment": 3}


def test_legacy_string_revision_is_coerced():
    document = StudyDocument.from_session({
        "study_id": "string-revision",
        "study_revision": "7.0",
    })

    assert document.study_revision == 7
