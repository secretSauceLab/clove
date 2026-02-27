from dotenv import load_dotenv
load_dotenv()

from app.fhir import strip_plumbing, classify_relevance, to_natural_language
from app.subscribers import fetch_fhir_from_hospital, answer_questions_with_llm
import asyncio


async def main():
    bundle = await fetch_fhir_from_hospital(1)
    print(f"Total resources: {len(bundle['entry'])}")

    resources = strip_plumbing(bundle)
    print(f"After stripping plumbing: {len(resources)}")

    relevant = await classify_relevance(resources, "Rheumatoid arthritis", "Humira (adalimumab)")
    print(f"Relevant: {len(relevant)}")
    print()

    for r in relevant:
        print(f"  {r['resourceType']}: {r.get('code', r.get('medicationCodeableConcept', {})).get('text', r.get('id', '?'))}")

    summary = to_natural_language(relevant)
    print(f"\nNATURAL LANGUAGE SUMMARY:\n{summary}")

    questions = [
        "Does the patient have a confirmed diagnosis of rheumatoid arthritis?",
        "Has the patient tried and failed conventional DMARD therapy?",
        "Is there clinical justification for biologic therapy?",
    ]

    answers = await answer_questions_with_llm(summary, questions)
    for a in answers:
        print(f"\nQ: {a['question']}")
        print(f"A: {a['answer']}")
        print(f"Records: {a['supporting_record_ids']}")
        print(f"Confidence: {a['confidence']}")

asyncio.run(main())