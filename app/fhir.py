import logging
import os

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field

load_dotenv()
log = logging.getLogger(__name__)

PLUMBING_KEYS = {"meta", "text", "contained", "implicitRules", "language"}
CLINICAL_TYPES = {
    "Condition", "Observation", "MedicationRequest",
    "Procedure", "DiagnosticReport", "CarePlan", "AllergyIntolerance",
}


class ResourceRelevance(BaseModel):
    id: str = Field(description="The resource index")
    relevant: bool = Field(description="Whether this resource is relevant to the condition and drug")
    reasoning: str = Field(description="Brief explanation of the classification")


class BatchClassification(BaseModel):
    classifications: list[ResourceRelevance]


def _get_gemini_client():
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def _get_description(resource):
    """Extract a human-readable description from a FHIR resource."""
    rtype = resource["resourceType"]
    if rtype == "MedicationRequest":
        return resource.get("medicationCodeableConcept", {}).get("text", "unknown")
    return resource.get("code", {}).get("text", "unknown")


def strip_plumbing(bundle):
    clean_resources = []
    for entry in bundle["entry"]:
        resource = entry["resource"]
        for key in PLUMBING_KEYS:
            resource.pop(key, None)
        clean_resources.append(resource)
    return clean_resources


async def classify_relevance(resources, condition, drug):
    client = _get_gemini_client()
    relevant = []
    clinical_batches = {}

    for r in resources:
        rtype = r["resourceType"]
        if rtype == "Patient":
            relevant.append(r)
        elif rtype in CLINICAL_TYPES:
            clinical_batches.setdefault(rtype, []).append(r)

    for rtype, batch in clinical_batches.items():
        # Deduplicate by description — classify unique names, map back to all matching resources
        desc_to_resources = {}
        for r in batch:
            desc_to_resources.setdefault(_get_description(r), []).append(r)

        unique_descriptions = list(desc_to_resources.keys())
        log.info("Classifying %d unique %s descriptions (from %d resources)",
                 len(unique_descriptions), rtype, len(batch))

        resource_list = "\n".join(
            f"ID: {i} — {desc}" for i, desc in enumerate(unique_descriptions)
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"""You are a clinical relevance classifier for prior authorization.

Given the condition and drug below, classify each {rtype} resource as relevant or not relevant.

CONDITION: {condition}
DRUG: {drug}

{rtype.upper()} RESOURCES:
{resource_list}

Classify every resource listed above. Be STRICT. A resource is relevant ONLY if it directly relates to:
- The diagnosis of {condition}
- Treatments or medications for {condition}
- Lab results that measure disease activity or treatment response for {condition}
- Imaging or procedures specifically for {condition}
- Documentation of prior therapy failure that would justify prescribing {drug}

Routine physical examinations, general evaluations, history taking, reviews of systems,
and standard encounter procedures are NOT relevant.
Pre-treatment safety screenings (TB, hepatitis, CBC) ARE relevant if they relate to biologic therapy.
When in doubt, mark as NOT relevant.""",
            config={
                "response_mime_type": "application/json",
                "response_json_schema": BatchClassification.model_json_schema(),
            },
        )

        result = BatchClassification.model_validate_json(response.text)

        relevant_ids = {c.id for c in result.classifications if c.relevant}
        for idx_str in relevant_ids:
            try:
                idx = int(idx_str)
                desc = unique_descriptions[idx]
                relevant.extend(desc_to_resources[desc])
            except (ValueError, IndexError):
                continue

    return relevant

def to_natural_language(resources):
    lines = []
    for resource in resources:
        rtype = resource["resourceType"]

        if rtype == "Patient":
            name = resource.get("name", [{}])[0]
            given = " ".join(name.get("given", []))
            family = name.get("family", "")
            birth = resource.get("birthDate", "unknown")
            gender = resource.get("gender", "unknown")
            lines.append(f"Patient: {given} {family}, born {birth}, {gender}.")

        elif rtype == "Condition":
            display = resource.get("code", {}).get("text", "Unknown condition")
            onset = resource.get("onsetDateTime", "unknown date")
            lines.append(f"Diagnosis: {display}, onset {onset}.")

        elif rtype == "Observation":
            display = resource.get("code", {}).get("text", "Unknown observation")
            value = resource.get("valueQuantity", {})
            val = value.get("value", "?")
            unit = value.get("unit", "")
            date = resource.get("effectiveDateTime", "unknown date")
            lines.append(f"Lab result: {display}: {val} {unit} (recorded {date}).")

        elif rtype == "MedicationRequest":
            med = resource.get("medicationCodeableConcept", {})
            display = med.get("text", "Unknown medication")
            status = resource.get("status", "unknown")
            authored = resource.get("authoredOn", "unknown date")
            lines.append(f"Medication: {display}, status: {status} (prescribed {authored}).")

        else:
            display = resource.get("code", {}).get("text", "")
            if display:
                lines.append(f"{rtype}: {display}.")

    return "\n".join(lines)