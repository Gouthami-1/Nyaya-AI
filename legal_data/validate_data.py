
import json
from pathlib import Path
from urllib.parse import urlparse

DATA_FILE = Path(__file__).parent / "provisions.json"

REQUIRED_FIELDS = [
    "act_name",
    "act_year",
    "section_number",
    "section_title",
    "legal_text",
    "explanation",
    "keywords",
    "category",
    "jurisdiction",
    "source_url",
    "verification_status",
]

def validate_data():
    if not DATA_FILE.exists():
        print(f"ERROR: File not found: {DATA_FILE}")
        return

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            records = json.load(file)
    except json.JSONDecodeError as error:
        print(f"ERROR: Invalid JSON: {error}")
        return

    if not isinstance(records, list):
        print("ERROR: The JSON root must be a list.")
        return

    errors = []
    warnings = []
    seen_sections = set()

    for index, record in enumerate(records, start=1):
        label = (
            f"Record {index}: "
            f"{record.get('act_name', 'Unknown Act')} "
            f"Section {record.get('section_number', 'Unknown')}"
        )

        if not isinstance(record, dict):
            errors.append(f"Record {index} is not an object.")
            continue

        for field in REQUIRED_FIELDS:
            if not str(record.get(field, "")).strip():
                errors.append(f"{label}: missing {field}.")

        section_key = (
            str(record.get("act_name", "")).strip().lower(),
            str(record.get("section_number", "")).strip().lower(),
            str(record.get("act_year", "")).strip(),
        )

        if section_key in seen_sections:
            errors.append(f"{label}: duplicate section record.")
        seen_sections.add(section_key)

        source_url = record.get("source_url", "")
        parsed_url = urlparse(source_url)

        if parsed_url.scheme != "https" or not parsed_url.netloc:
            errors.append(f"{label}: source URL must be a valid HTTPS URL.")
        elif parsed_url.netloc.lower() != "www.indiacode.nic.in":
            warnings.append(f"{label}: source is not hosted on India Code.")

        if source_url.rstrip("/") == "https://www.indiacode.nic.in":
            warnings.append(f"{label}: source is only the India Code homepage.")

        status = str(record.get("verification_status", "")).strip().lower()

        if status == "verified":
            if not record.get("verified_date"):
                warnings.append(f"{label}: verified without a verification date.")

            warnings.append(
                f"{label}: check the exact statutory wording manually; "
                "a status label cannot prove legal accuracy."
            )
        elif status not in {"needs_review", "unverified", "pending"}:
            warnings.append(
                f"{label}: unfamiliar verification status '{status}'."
            )

        for field in ("legal_text", "section_title", "explanation"):
            if len(str(record.get(field, "")).strip()) < 10:
                warnings.append(f"{label}: {field} looks unusually short.")

    print(f"\nRecords checked: {len(records)}")
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")

    for error in errors:
        print(f"ERROR: {error}")

    for warning in warnings:
        print(f"WARNING: {warning}")

    if not errors:
        print("\nJSON structure checks passed.")
        print("This does NOT mean the legal content is verified.")

if __name__ == "__main__":
    validate_data()
