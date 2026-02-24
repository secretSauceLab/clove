# app/subscribers.py
import asyncio
import json
import logging
import os

from dotenv import load_dotenv
from google import genai

from .pubsub import get_pubsub, PubSubMessage
from .fhir import strip_plumbing, classify_relevance, to_natural_language

log = logging.getLogger(__name__)
load_dotenv()


async def fetch_fhir_from_hospital(case_id):
    """
    Fetch FHIR records from hospital EHR.
    TODO: Replace with real HTTP call to hospital FHIR server.
    """
    await asyncio.sleep(0.3)
    return {
        "resourceType": "Bundle",
        "entry": [
            {"fullUrl": "urn:uuid:p1", "resource": {"resourceType": "Patient", "id": "p1", "name": [{"family": "Martinez", "given": ["Sofia"]}], "birthDate": "1968-07-22", "gender": "female"}, "request": {"method": "POST", "url": "Patient"}},
            {"fullUrl": "urn:uuid:c1", "resource": {"resourceType": "Condition", "id": "cond-001", "code": {"text": "Ankylosing spondylitis"}, "onsetDateTime": "2015-04-10"}, "request": {"method": "POST", "url": "Condition"}},
            {"fullUrl": "urn:uuid:c2", "resource": {"resourceType": "Condition", "id": "cond-002", "code": {"text": "Seasonal allergies"}, "onsetDateTime": "2005-03-01"}, "request": {"method": "POST", "url": "Condition"}},
            {"fullUrl": "urn:uuid:o1", "resource": {"resourceType": "Observation", "id": "obs-001", "code": {"text": "C-reactive protein"}, "valueQuantity": {"value": 15.2, "unit": "mg/L"}, "effectiveDateTime": "2025-01-10"}, "request": {"method": "POST", "url": "Observation"}},
            {"fullUrl": "urn:uuid:o2", "resource": {"resourceType": "Observation", "id": "obs-002", "code": {"text": "ESR Westergren"}, "valueQuantity": {"value": 38, "unit": "mm/hr"}, "effectiveDateTime": "2025-01-10"}, "request": {"method": "POST", "url": "Observation"}},
            {"fullUrl": "urn:uuid:o3", "resource": {"resourceType": "Observation", "id": "obs-003", "code": {"text": "Body Mass Index"}, "valueQuantity": {"value": 26.1, "unit": "kg/m2"}, "effectiveDateTime": "2025-01-10"}, "request": {"method": "POST", "url": "Observation"}},
            {"fullUrl": "urn:uuid:m1", "resource": {"resourceType": "MedicationRequest", "id": "med-001", "medicationCodeableConcept": {"text": "Celebrex 200mg"}, "status": "active", "authoredOn": "2016-01-15"}, "request": {"method": "POST", "url": "MedicationRequest"}},
            {"fullUrl": "urn:uuid:m2", "resource": {"resourceType": "MedicationRequest", "id": "med-002", "medicationCodeableConcept": {"text": "Lisinopril 10mg"}, "status": "active", "authoredOn": "2019-08-10"}, "request": {"method": "POST", "url": "MedicationRequest"}},
            {"fullUrl": "urn:uuid:i1", "resource": {"resourceType": "Immunization", "id": "imm-001", "vaccineCode": {"text": "Influenza seasonal"}, "occurrenceDateTime": "2024-10-01"}, "request": {"method": "POST", "url": "Immunization"}},
        ],
    }


async def answer_questions_with_llm(patient_summary, questions):
    """Answer prior auth questions using Gemini given a patient summary."""
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    answers = []
    for question in questions:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"""You are a clinical documentation specialist assisting with prior authorization.

Given the patient's medical history below, answer the following question.

PATIENT HISTORY (each record has an ID in parentheses):
{patient_summary}

QUESTION: {question}

Respond in this exact JSON format and nothing else:
{{
    "answer": "Your 1-3 sentence answer here",
    "supporting_record_ids": ["list", "of", "record", "ids", "from", "the", "history"],
    "confidence": 0.0 to 1.0
}}""",
        )

        try:
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            parsed = json.loads(text)
            answers.append({
                "question": question,
                "answer": parsed["answer"],
                "supporting_record_ids": parsed.get("supporting_record_ids", []),
                "confidence": parsed.get("confidence", 0.5),
            })
        except (json.JSONDecodeError, KeyError):
            answers.append({
                "question": question,
                "answer": response.text,
                "supporting_record_ids": [],
                "confidence": 0.5,
            })

    return answers


async def handle_prior_auth_requested(message):
    data = message.data
    log.info("FHIR Fetcher: processing request %s", data["request_id"])

    bundle = await fetch_fhir_from_hospital(data["case_id"])
    log.info("FHIR Fetcher: got %d records", len(bundle["entry"]))

    pubsub = get_pubsub()
    await pubsub.publish("fhir-records-ready", {**data, "bundle": bundle})


async def handle_fhir_records_ready(message):
    data = message.data
    log.info("Classifier: processing request %s", data["request_id"])

    resources = strip_plumbing(data["bundle"])
    relevant = classify_relevance(resources, data["condition"], data["drug"])
    patient_summary = to_natural_language(relevant)

    log.info("Classifier: %d resources -> %d relevant", len(resources), len(relevant))

    pubsub = get_pubsub()
    await pubsub.publish("records-classified", {
        "request_id": data["request_id"],
        "case_id": data["case_id"],
        "questions": data["questions"],
        "patient_summary": patient_summary,
    })


async def handle_records_classified(message):
    data = message.data
    log.info("QA Engine: answering %d questions", len(data["questions"]))

    answers = await answer_questions_with_llm(
        data["patient_summary"],
        data["questions"],
    )

    for a in answers:
        log.info("  Q: %s", a["question"])
        log.info("  A: %s", a["answer"])

    pubsub = get_pubsub()
    await pubsub.publish("prior-auth-answered", {
        "request_id": data["request_id"],
        "case_id": data["case_id"],
        "answers": answers,
    })


async def handle_prior_auth_answered(message):
    data = message.data
    log.info("Notifier: request %s completed with %d answers",
             data["request_id"], len(data["answers"]))


def setup_pipeline():
    pubsub = get_pubsub()

    pubsub.create_topic("prior-auth-requested")
    pubsub.create_topic("fhir-records-ready")
    pubsub.create_topic("records-classified")
    pubsub.create_topic("prior-auth-answered")

    pubsub.subscribe("prior-auth-requested", handle_prior_auth_requested)
    pubsub.subscribe("fhir-records-ready", handle_fhir_records_ready)
    pubsub.subscribe("records-classified", handle_records_classified)
    pubsub.subscribe("prior-auth-answered", handle_prior_auth_answered)

    log.info("Prior auth pipeline ready")