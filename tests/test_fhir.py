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

def test_classify_relevance_ankylosing_spondylitis():
    resources = [
        {"resourceType": "Patient", "id": "p1", "name": [{"family": "Beal", "given": ["Jeremy"]}]},
        {"resourceType": "Condition", "id": "cond-1", "code": {"text": "Ankylosing spondylitis"}},
        {"resourceType": "Condition", "id": "cond-2", "code": {"text": "Seasonal allergies"}},
        {"resourceType": "Observation", "id": "obs-1", "code": {"text": "C-reactive protein"}, "valueQuantity": {"value": 15.2, "unit": "mg/L"}},
        {"resourceType": "Observation", "id": "obs-2", "code": {"text": "HLA-B27 antigen"}, "valueQuantity": {"value": "positive"}},
        {"resourceType": "Observation", "id": "obs-3", "code": {"text": "Body Mass Index"}, "valueQuantity": {"value": 26.1, "unit": "kg/m2"}},
        {"resourceType": "MedicationRequest", "id": "med-1", "medicationCodeableConcept": {"text": "Celebrex 200mg"}},
        {"resourceType": "MedicationRequest", "id": "med-2", "medicationCodeableConcept": {"text": "Lisinopril 10mg"}},
        {"resourceType": "Immunization", "id": "imm-1", "vaccineCode": {"text": "Influenza seasonal"}},
    ]

    result = classify_relevance(resources, "Ankylosing spondylitis", "Humira (adalimumab)")

    result_ids = [r["id"] for r in result]

    assert "p1" in result_ids       # Patient — always kept
    assert "cond-1" in result_ids   # AS diagnosis — relevant
    assert "cond-2" not in result_ids  # Allergies — not relevant
    assert "obs-1" in result_ids    # CRP — inflammation marker
    assert "obs-2" in result_ids    # HLA-B27 — genetic marker
    assert "obs-3" not in result_ids   # BMI — not relevant
    assert "med-1" in result_ids    # Celebrex — related NSAID
    assert "med-2" not in result_ids   # Lisinopril — blood pressure med
    assert "imm-1" not in result_ids   # Flu shot — not relevant

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