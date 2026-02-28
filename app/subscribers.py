import json
import logging
import os

from pathlib import Path
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field

from .pubsub import get_pubsub
from .fhir import strip_plumbing, classify_relevance, to_natural_language

from sqlalchemy import select
from .db import SessionLocal
from .models_prior_auth import PriorAuthRequest, PriorAuthAnswer, PriorAuthStatus

log = logging.getLogger(__name__)
load_dotenv()


class PriorAuthQA(BaseModel):
    answer: str = Field(description="1-3 sentence answer to the question")
    supporting_record_ids: list[str] = Field(description="Lines from the patient history that support this answer")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0")


def _get_gemini_client():
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


async def fetch_fhir_from_hospital(case_id):
    """Fetch FHIR records from hospital EHR."""
    fhir_path = Path(__file__).parent.parent / "data" / "sample_patient.json"
    with open(fhir_path) as f:
        return json.load(f)


async def answer_questions_with_llm(patient_summary, questions):
    """Answer prior auth questions using Gemini structured output."""
    client = _get_gemini_client()

    answers = []
    for question in questions:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"""You are a clinical documentation specialist assisting with prior authorization.

Given the patient's medical history below, answer the following question.

PATIENT HISTORY:
{patient_summary}

QUESTION: {question}""",
            config={
                "response_mime_type": "application/json",
                "response_json_schema": PriorAuthQA.model_json_schema(),
            },
        )

        parsed = PriorAuthQA.model_validate_json(response.text)
        answers.append({
            "question": question,
            "answer": parsed.answer,
            "supporting_record_ids": parsed.supporting_record_ids,
            "confidence": parsed.confidence,
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
    relevant = await classify_relevance(resources, data["condition"], data["drug"])
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
    log.info("Notifier: saving %d answers for request %s",
             len(data["answers"]), data["request_id"])

    async with SessionLocal() as db:
        result = await db.execute(
            select(PriorAuthRequest).where(PriorAuthRequest.id == data["request_id"])
        )
        pa_request = result.scalar_one()
        pa_request.status = PriorAuthStatus.COMPLETED.value

        for a in data["answers"]:
            db.add(PriorAuthAnswer(
                request_id=data["request_id"],
                question=a["question"],
                answer=a["answer"],
                supporting_record_ids=a["supporting_record_ids"],
                confidence=a["confidence"],
            ))

        await db.commit()
        log.info("Notifier: request %s saved as COMPLETED", data["request_id"])


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