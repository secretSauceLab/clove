from dotenv import load_dotenv
load_dotenv()

from app.fhir import strip_plumbing, classify_relevance, to_natural_language
from app.subscribers import answer_questions_with_llm
import json, asyncio

PATIENTS = [
    {
        "file": "data/sample_patient.json",
        "condition": "Rheumatoid arthritis",
        "drug": "Humira (adalimumab)",
        "questions": [
            "Does the patient have a confirmed diagnosis of rheumatoid arthritis?",
            "Has the patient tried and failed conventional DMARD therapy?",
            "Is there clinical justification for biologic therapy?",
        ],
    },
    {
        "file": "data/diabetes_patient.json",
        "condition": "Prediabetes",
        "drug": "Metformin",
        "questions": [
            "Does the patient have a confirmed diagnosis of prediabetes or type 2 diabetes?",
            "What is the patient's most recent HbA1c level?",
            "Are there contraindications to Metformin such as impaired kidney function?",
        ],
    },
    {
        "file": "data/asthma_patient.json",
        "condition": "Asthma",
        "drug": "Dupixent (dupilumab)",
        "questions": [
            "Does the patient have a confirmed diagnosis of moderate-to-severe asthma?",
            "Has the patient tried and failed inhaled corticosteroids?",
            "Is there evidence of an eosinophilic or allergic asthma phenotype?",
        ],
    },
]

async def test_patient(patient):
    print(f"\n{'='*60}")
    print(f"PATIENT: {patient['file']}")
    print(f"CONDITION: {patient['condition']} | DRUG: {patient['drug']}")
    print(f"{'='*60}")

    bundle = json.load(open(patient["file"]))
    print(f"Total resources: {len(bundle['entry'])}")

    resources = strip_plumbing(bundle)
    relevant = await classify_relevance(resources, patient["condition"], patient["drug"])
    print(f"Relevant: {len(relevant)}")

    summary = to_natural_language(relevant)
    print(f"Summary length: {len(summary)} chars")

    answers = await answer_questions_with_llm(summary, patient["questions"])
    for a in answers:
        print(f"\n  Q: {a['question']}")
        print(f"  A: {a['answer']}")
        print(f"  Confidence: {a['confidence']}")

    print(f"\n  PASS")

async def main():
    for patient in PATIENTS:
        await test_patient(patient)
    print(f"\n{'='*60}")
    print("ALL PATIENTS PASSED")

asyncio.run(main())
