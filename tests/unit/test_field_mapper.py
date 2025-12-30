import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from planproof.pipeline.field_mapper import map_fields


def _block(text, index, page=1):
    return {
        "content": text,
        "page_number": page,
        "index": index,
    }


def test_extract_application_ref_pp_regex():
    extracted = {
        "text_blocks": [
            _block("Planning Portal Reference: PP-14469287", 0),
        ]
    }

    result = map_fields(extracted)

    assert result["fields"]["application_ref"] == "PP-14469287"
    assert result["fields"]["application_ref_confidence"] == 0.9


def test_postcode_ranking_prefers_site_location():
    extracted = {
        "text_blocks": [
            _block("Birmingham City Council PO Box 28 B1 1TU", 0),
            _block("Site location", 1),
            _block("Postcode: B8 1BG", 2),
        ]
    }

    result = map_fields(extracted)

    assert result["fields"]["postcode"] == "B8 1BG"
    assert result["fields"]["postcode"] != "B1 1TU"


def test_address_assembly_from_labeled_fields():
    extracted = {
        "text_blocks": [
            _block("Site location", 0),
            _block("Property Name: Unit M", 1),
            _block("Address Line 1: Dorset Road", 2),
            _block("Address Line 2: Saltley Business Park", 3),
            _block("Town/City: Birmingham", 4),
            _block("Postcode: B8 1BG", 5),
        ]
    }

    result = map_fields(extracted)

    assert (
        result["fields"]["site_address"]
        == "Unit M, Dorset Road, Saltley Business Park, Birmingham, B8 1BG"
    )


def test_reject_council_contact_as_applicant_email_phone():
    extracted = {
        "text_blocks": [
            _block("planning.registration@birmingham.gov.uk", 0),
            _block("0121 464 3669", 1),
        ]
    }

    result = map_fields(extracted)
    fields = result["fields"]

    assert "applicant_email" not in fields
    assert "applicant_phone" not in fields


def test_reject_disclaimer_blocks_for_site_address():
    extracted = {
        "text_blocks": [
            _block("Disclaimer: for information only", 0),
            _block("Disclaimer: 10 Downing Street", 1),
        ]
    }

    result = map_fields(extracted)
    fields = result["fields"]

    assert "site_address" not in fields
