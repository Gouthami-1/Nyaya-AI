import json
import sys
from pathlib import Path

# --------------------------------------------------
# PROJECT PATH
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from database.database import (
    get_connection,
    initialize_database
)


# --------------------------------------------------
# DATA FILE
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

DATA_FILE = BASE_DIR / "provisions.json"


# --------------------------------------------------
# LOAD JSON
# --------------------------------------------------

def load_provisions():

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Legal data file not found:\n{DATA_FILE}"
        )

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

    except json.JSONDecodeError as error:

        raise ValueError(
            f"Invalid JSON in provisions.json:\n{error}"
        )

    if not isinstance(data, list):

        raise ValueError(
            "provisions.json must contain a JSON array."
        )

    return data


# --------------------------------------------------
# VALIDATE PROVISION
# --------------------------------------------------


def validate_provision(item, index):
    required_fields = [
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
        "verification_status"
    ]

    if not isinstance(item, dict):
        raise ValueError(
            f"Provision {index + 1} must be a JSON object."
        )

    missing = [
        field for field in required_fields
        if field not in item
    ]

    if missing:
        raise ValueError(
            f"Provision {index + 1} is missing: "
            + ", ".join(missing)
        )

    allowed_statuses = {"verified", "needs_review"}

    if item["verification_status"] not in allowed_statuses:
        raise ValueError(
            f"Provision {index + 1} has an invalid "
            "verification_status."
        )

    source_url = item["source_url"]

    if not isinstance(source_url, str):
        raise ValueError(
            f"Provision {index + 1} has an invalid source URL."
        )

    if not source_url.startswith("https://"):
        raise ValueError(
            f"Provision {index + 1} must use an HTTPS source URL."
        )

    for field in [
        "act_name",
        "section_number",
        "section_title",
        "legal_text",
        "explanation"
    ]:
        if not isinstance(item[field], str) or not item[field].strip():
            raise ValueError(
                f"Provision {index + 1} has an empty or invalid {field}."
            )



# --------------------------------------------------
# IMPORT
# --------------------------------------------------

def import_provisions():

    print()
    print("Initializing database...")

    initialize_database()

    print("Loading legal provisions...")

    provisions = load_provisions()

    imported = 0
    updated = 0

    with get_connection() as conn:

        for index, item in enumerate(provisions):

            validate_provision(
                item,
                index
            )

            existing = conn.execute(
                """
                SELECT id
                FROM legal_provisions

                WHERE act_name = ?
                  AND act_year = ?
                  AND section_number = ?
                """,
                (
                    item["act_name"],
                    item["act_year"],
                    item["section_number"]
                )
            ).fetchone()

            values = (

                item["act_name"],
                item["act_year"],
                item["section_number"],
                item["section_title"],
                item["legal_text"],
                item["explanation"],
                item["keywords"],
                item["category"],
                item["jurisdiction"],
                item["source_url"],
                item["verified_date"],
                item["effective_from"],
                item["effective_until"],
                item["verification_status"]
            )

            # ------------------------------------------
            # UPDATE EXISTING
            # ------------------------------------------

            if existing:

                conn.execute(
                    """
                    UPDATE legal_provisions

                    SET
                        act_name = ?,
                        act_year = ?,
                        section_number = ?,
                        section_title = ?,
                        legal_text = ?,
                        explanation = ?,
                        keywords = ?,
                        category = ?,
                        jurisdiction = ?,
                        source_url = ?,
                        verified_date = ?,
                        effective_from = ?,
                        effective_until = ?,
                        verification_status = ?

                    WHERE id = ?
                    """,

                    values + (
                        existing["id"],
                    )
                )

                updated += 1

            # ------------------------------------------
            # INSERT NEW
            # ------------------------------------------

            else:

                conn.execute(
                    """
                    INSERT INTO legal_provisions (

                        act_name,
                        act_year,
                        section_number,
                        section_title,
                        legal_text,
                        explanation,
                        keywords,
                        category,
                        jurisdiction,
                        source_url,
                        verified_date,
                        effective_from,
                        effective_until,
                        verification_status

                    )

                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?
                    )
                    """,

                    values
                )

                imported += 1

    # --------------------------------------------------
    # RESULT
    # --------------------------------------------------

    print()
    print("========================================")
    print("       NYAYA AI LEGAL IMPORT")
    print("========================================")
    print(f"New provisions : {imported}")
    print(f"Updated        : {updated}")
    print(f"Total records  : {len(provisions)}")
    print("========================================")
    print()


# --------------------------------------------------
# RUN
# --------------------------------------------------

if __name__ == "__main__":

    import_provisions()