PLUMBING_KEYS = {"meta", "text", "contained", "implicitRules", "language"}


def strip_plumbing(bundle):
    clean_resources = []
    for entry in bundle["entry"]:
        resource = entry["resource"]
        for key in PLUMBING_KEYS:
            resource.pop(key, None)
        clean_resources.append(resource)
    return clean_resources

def classify_relevance(resources, condition, drug):
    relevant = []
    condition_lower = condition.lower()
    drug_lower = drug.lower()

    for resource in resources:
        rtype = resource["resourceType"]

        # Always keep patient demographics
        if rtype == "Patient":
            relevant.append(resource)

        # Keep conditions that match the condition name
        elif rtype == "Condition":
            text = resource.get("code", {}).get("text", "").lower()
            if condition_lower in text or text in condition_lower:
                relevant.append(resource)

        # Keep observations (labs) that relate to the condition
        elif rtype == "Observation":
            text = resource.get("code", {}).get("text", "").lower()
            # For ankylosing spondylitis: inflammation markers and genetic test
            relevant_labs = ["crp", "c-reactive", "esr", "sedimentation", "hla-b27"]
            if any(lab in text for lab in relevant_labs):
                relevant.append(resource)

        # Keep medications related to the drug or the condition
        elif rtype == "MedicationRequest":
            med = resource.get("medicationCodeableConcept", {})
            text = med.get("text", "").lower()
            # Biologics and NSAIDs used for ankylosing spondylitis
            related_meds = ["humira", "adalimumab", "enbrel", "etanercept",
                "cosentyx", "secukinumab", "naproxen", "ibuprofen",
                "celebrex", "celecoxib"]
            if any(med_name in text for med_name in related_meds):
                relevant.append(resource)

        # Everything else gets dropped

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

    return "\n".join(lines)