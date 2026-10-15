
import argparse
import csv
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from database.database import get_connection, initialize_database


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = ROOT / "legal_data" / "legal_provisions.csv"

REQUIRED = [
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
    "verified_date",
    "effective_from",
    "effective_until",
    "verification_status",
]


def valid_source_url(value):
    parsed = urlparse(value)
    return (
        parsed.scheme == "https"
        and parsed.hostname is not None
        and (
            parsed.hostname == "indiacode.nic.in"
            or parsed.hostname.endswith(".gov.in")
            or parsed.hostname == "gov.in"
        )
    )


def validate_row(row, line_number):
    errors = []

    for field in REQUIRED:
        if not (row.get(field) or "").strip():
            errors.append(f"Line {line_number}: missing {field}")

    if errors:
        return errors

    try:
        year = int(row["act_year"])
        if year < 1700 or year > date.today().year + 2:
            raise ValueError
    except ValueError:
        errors.append(f"Line {line_number}: invalid act_year")

    for field in ("verified_date", "effective_from", "effective_until"):
        value = row[field].strip()
        if value:
            try:
                date.fromisoformat(value)
            except ValueError:
                errors.append(
                    f"Line {line_number}: {field} must be YYYY-MM-DD"
                )

    if not valid_source_url(row["source_url"].strip()):
        errors.append(
            f"Line {line_number}: source_url must use HTTPS "
            "and an allowed government domain"
        )

    if row["verification_status"].strip().lower() not in (
        "verified", "pending", "rejected"
    ):
        errors.append(
            f"Line {line_number}: verification_status must be "
            "verified, pending or rejected"
        )

    if row["effective_from"] and row["effective_until"]:
        if row["effective_from"] > row["effective_until"]:
            errors.append(
                f"Line {line_number}: effective_from is after effective_until"
            )

    return errors


def import_csv(csv_path):
    initialize_database()
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    inserted = 0
    skipped = 0
    errors = []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("CSV file has no header row")

        missing = set(REQUIRED) - set(reader.fieldnames)
        if missing:
            raise ValueError(
                "CSV is missing columns: " + ", ".join(sorted(missing))
            )

        with get_connection() as conn:
            for line_number, row in enumerate(reader, start=2):
                problems = validate_row(row, line_number)

                if problems:
                    errors.extend(problems)
                    skipped += 1
                    continue

                try:
                    cursor = conn.execute("""
                        INSERT INTO legal_provisions (
                            act_name, act_year, section_number,
                            section_title, legal_text, explanation,
                            keywords, category, jurisdiction, source_url,
                            verified_date, effective_from, effective_until,
                            verification_status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(act_name, act_year, section_number)
                        DO UPDATE SET
                            section_title = excluded.section_title,
                            legal_text = excluded.legal_text,
                            explanation = excluded.explanation,
                            keywords = excluded.keywords,
                            category = excluded.category,
                            jurisdiction = excluded.jurisdiction,
                            source_url = excluded.source_url,
                            verified_date = excluded.verified_date,
                            effective_from = excluded.effective_from,
                            effective_until = excluded.effective_until,
                            verification_status = excluded.verification_status
                    """, (
                        row["act_name"].strip(),
                        int(row["act_year"]),
                        row["section_number"].strip(),
                        row["section_title"].strip(),
                        row["legal_text"].strip(),
                        row["explanation"].strip(),
                        row["keywords"].strip(),
                        row["category"].strip().lower(),
                        row["jurisdiction"].strip(),
                        row["source_url"].strip(),
                        row["verified_date"].strip(),
                        row["effective_from"].strip(),
                        row["effective_until"].strip(),
                        row["verification_status"].strip().lower(),
                    ))

                    inserted += 1

                except Exception as exc:
                    errors.append(f"Line {line_number}: {exc}")
                    skipped += 1

    print(f"Imported or updated: {inserted}")
    print(f"Skipped: {skipped}")

    for error in errors:
        print("ERROR:", error)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import Indian legal provisions into Nyaya AI"
    )
    parser.add_argument(
        "--file",
        default=str(DEFAULT_CSV),
        help="Path to the legal provisions CSV"
    )
    args = parser.parse_args()

    import_csv(args.file)
