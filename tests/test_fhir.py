import pytest
from app.fhir import strip_plumbing, classify_relevance, to_natural_language

def test_strip_plumbing_extracts_resources():
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "fullUrl": "urn:uuid:abc123",
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-001",
                    "name": "Jane Doe",
                },
                "request": {"method": "POST", "url": "Patient"},
            },
            {
                "fullUrl": "urn:uuid:def456",
                "resource": {
                    "resourceType": "Condition",
                    "id": "cond-001",
                    "code": {"text": "Type 2 diabetes"},
                },
                "request": {"method": "POST", "url": "Condition"},
            },
        ],
    }

    result = strip_plumbing(bundle)

    assert len(result) == 2
    assert result[0]["resourceType"] == "Patient"
    assert result[1]["resourceType"] == "Condition"
    # fullUrl and request should NOT be in the results
    assert "fullUrl" not in result[0]
    assert "request" not in result[0]

def test_strip_plumbing_removes_meta():
    bundle = {
        "resourceType": "Bundle",
        "entry": [
            {
                "fullUrl": "urn:uuid:abc",
                "resource": {
                    "resourceType": "Patient",
                    "id": "p1",
                    "meta": {"profile": ["http://hl7.org/fhir/us/core/..."]},
                    "name": [{"family": "Doe"}],
                },
                "request": {"method": "POST", "url": "Patient"},
            },
        ],
    }

    result = strip_plumbing(bundle)

    assert "meta" not in result[0]
    assert result[0]["name"] == [{"family": "Doe"}]

@pytest.mark.asyncio
async def test_classify_relevance_ankylosing_spondylitis(monkeypatch):
    """Unit test with mocked Gemini response."""
    from unittest.mock import MagicMock
    from app.fhir import classify_relevance

    # Fake Gemini response — indices match unique descriptions
    fake_json = '{"classifications": [' \
        '{"id": "0", "relevant": true, "reasoning": "AS diagnosis"}, ' \
        '{"id": "1", "relevant": false, "reasoning": "Not related"}' \
    ']}'

    fake_response = MagicMock()
    fake_response.text = fake_json

    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response

    # Patch genai.Client to return our fake
    import app.fhir
    monkeypatch.setattr(app.fhir, "_get_gemini_client", lambda: fake_client)
    
    resources = [
        {"resourceType": "Patient", "id": "p1", "name": [{"family": "Beal", "given": ["Jeremy"]}]},
        {"resourceType": "Condition", "id": "cond-1", "code": {"text": "Ankylosing spondylitis"}},
        {"resourceType": "Condition", "id": "cond-2", "code": {"text": "Seasonal allergies"}},
    ]

    result = await classify_relevance(resources, "Ankylosing spondylitis", "Humira (adalimumab)")
    result_ids = [r["id"] for r in result]

    assert "p1" in result_ids       # Patient — always kept
    assert "cond-1" in result_ids   # AS — mock said relevant
    assert "cond-2" not in result_ids  # Allergies — mock said not relevant

def test_to_natural_language():
    resources = [
        {"resourceType": "Patient", "name": [{"family": "Beal", "given": ["Jeremy"]}], "birthDate": "1990-05-15", "gender": "male"},
        {"resourceType": "Condition", "code": {"text": "Ankylosing spondylitis"}, "onsetDateTime": "2018-03-10"},
        {"resourceType": "Observation", "code": {"text": "C-reactive protein"}, "valueQuantity": {"value": 15.2, "unit": "mg/L"}, "effectiveDateTime": "2025-01-10"},
        {"resourceType": "MedicationRequest", "medicationCodeableConcept": {"text": "Celebrex 200mg"}, "status": "active", "authoredOn": "2019-06-01"},
    ]

    result = to_natural_language(resources)

    assert "Jeremy Beal" in result
    assert "Ankylosing spondylitis" in result
    assert "15.2" in result
    assert "Celebrex" in result