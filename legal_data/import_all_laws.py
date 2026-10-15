
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

# Third-party API mirror. Verify legal text against India Code.
API_BASE = "https://indiacode.ecourtsindia.com/api/v1"

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "legal_data"
DB_PATH = DATA_DIR / "legal_corpus.db"

# "all" imports all Acts published with machine-readable text.
# Use "central" to limit the import to Central Acts.
JURISDICTION = "all"

PAGE_SIZE = 100
REQUEST_DELAY = 0.30
TIMEOUT = 45

session = requests.Session()
session.headers.update({
    "User-Agent": "NyayaAI-LegalCorpusImporter/1.0"
})


def request_json(url, params=None):
    """Fetch JSON with retries and basic URL safety checks."""
    allowed_host = "indiacode.ecourtsindia.com"

    for attempt in range(5):
        parsed = urlparse(url)

        if parsed.scheme != "https" or parsed.hostname != allowed_host:
            raise ValueError(f"Unexpected API URL: {url}")

        try:
            response = session.get(
                url,
                params=params,
                timeout=TIMEOUT
            )

            if response.status_code == 429:
                wait = int(response.headers.get("Retry-After", "10"))
                print(f"Rate limited. Waiting {wait} seconds...")
                time.sleep(max(wait, 2))
                continue

            response.raise_for_status()
            time.sleep(REQUEST_DELAY)
            return response.json()

        except (requests.RequestException, ValueError) as exc:
            if attempt == 4:
                raise RuntimeError(
                    f"Could not fetch {url}: {exc}"
                ) from exc

            wait = min(2 ** attempt, 30)
            print(f"Request failed; retrying in {wait}s: {exc}")
            time.sleep(wait)

    raise RuntimeError(f"Request failed: {url}")


def get_text(value):
    """Extract readable text from common API response shapes."""
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, list):
        return "\n".join(
            text for item in value
            if (text := get_text(item))
        ).strip()

    if isinstance(value, dict):
        for key in (
            "body", "text", "content", "plain_text",
            "html", "markdown"
        ):
            if key in value:
                result = get_text(value[key])
                if result:
                    return result

    return ""


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS legal_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                act_id TEXT NOT NULL,
                act_title TEXT NOT NULL,
                jurisdiction TEXT,
                act_year INTEGER,
                section_number TEXT NOT NULL DEFAULT '',
                section_heading TEXT NOT NULL DEFAULT '',
                legal_text TEXT NOT NULL DEFAULT '',
                source_url TEXT,
                text_source TEXT,
                imported_at TEXT NOT NULL,
                UNIQUE(act_id, section_number)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS import_progress (
                act_id TEXT PRIMARY KEY,
                act_title TEXT,
                status TEXT NOT NULL,
                error_message TEXT,
                updated_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_legal_act
            ON legal_documents(act_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_legal_title
            ON legal_documents(act_title)
        """)


def was_imported(act_id):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("""
            SELECT status FROM import_progress
            WHERE act_id = ?
        """, (act_id,)).fetchone()

    return bool(row and row[0] == "done")


def save_act(act, detail):
    metadata = detail.get("act", {})
    if not isinstance(metadata, dict):
        metadata = {}

    act_id = str(act.get("id") or metadata.get("id") or "").strip()
    title = (
        metadata.get("short_title")
        or metadata.get("title")
        or act.get("short_title")
        or act.get("title")
        or act_id
    )

    if not act_id:
        raise ValueError("Act record has no ID")

    jurisdiction = (
        metadata.get("jurisdiction")
        or act.get("jurisdiction")
        or ""
    )

    year = metadata.get("act_year") or act.get("act_year")
    source_url = metadata.get("url") or act.get("url") or ""

    sections = detail.get("sections", [])
    if not isinstance(sections, list):
        sections = []

    records = []

    for section in sections:
        if not isinstance(section, dict):
            continue

        number = str(
            section.get("number")
            or section.get("section_number")
            or ""
        ).strip()

        heading = str(section.get("heading") or "").strip()

        # Different API versions may represent section text differently.
        body = get_text(section.get("text"))
        if not body:
            body = get_text(section.get("body"))
        if not body:
            body = get_text(section.get("content"))

        section_url = section.get("url") or source_url
        text_source = (
            section.get("text_source")
            or metadata.get("text_source")
            or act.get("text_source")
            or "unspecified"
        )

        # Save even if the text is missing, so the section is discoverable.
        records.append((
            act_id, title, jurisdiction, year,
            number, heading, body, section_url,
            text_source
        ))

    # If the API returned no sections, preserve the Act metadata/text
    # rather than silently losing the record.
    if not records:
        body = get_text(detail.get("text"))
        records.append((
            act_id, title, jurisdiction, year,
            "", "Full Act", body, source_url,
            metadata.get("text_source", "unspecified")
        ))

    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        conn.executemany("""
            INSERT INTO legal_documents (
                act_id, act_title, jurisdiction, act_year,
                section_number, section_heading, legal_text,
                source_url, text_source, imported_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(act_id, section_number) DO UPDATE SET
                act_title = excluded.act_title,
                jurisdiction = excluded.jurisdiction,
                act_year = excluded.act_year,
                section_heading = excluded.section_heading,
                legal_text = excluded.legal_text,
                source_url = excluded.source_url,
                text_source = excluded.text_source,
                imported_at = excluded.imported_at
        """, [
            (*record, now) for record in records
        ])

        conn.execute("""
            INSERT INTO import_progress (
                act_id, act_title, status, error_message, updated_at
            )
            VALUES (?, ?, 'done', NULL, ?)
            ON CONFLICT(act_id) DO UPDATE SET
                act_title = excluded.act_title,
                status = 'done',
                error_message = NULL,
                updated_at = excluded.updated_at
        """, (act_id, title, now))

    return len(records), title


def mark_failed(act_id, title, error):
    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO import_progress (
                act_id, act_title, status, error_message, updated_at
            )
            VALUES (?, ?, 'failed', ?, ?)
            ON CONFLICT(act_id) DO UPDATE SET
                act_title = excluded.act_title,
                status = 'failed',
                error_message = excluded.error_message,
                updated_at = excluded.updated_at
        """, (act_id, title, str(error)[:1000], now))


def get_acts():
    params = {"limit": PAGE_SIZE}

    if JURISDICTION == "central":
        params["jurisdiction"] = "central"

    url = f"{API_BASE}/acts"

    while url:
        page = request_json(url, params=params)
        params = None  # Follow the API's own next-page URL.

        acts = page.get("acts", [])
        if not isinstance(acts, list):
            raise RuntimeError(
                "Unexpected API response: missing acts list."
            )

        for act in acts:
            yield act

        next_url = page.get("next")
        if not next_url:
            break

        # Validate the next URL before requesting it.
        parsed = urlparse(next_url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "indiacode.ecourtsindia.com"
        ):
            raise ValueError(f"Unexpected pagination URL: {next_url}")

        url = next_url


def main():
    init_db()

    print(f"Database: {DB_PATH}")
    print(f"Jurisdiction: {JURISDICTION}")
    print("Starting import. This may take a long time.")

    completed = 0
    skipped = 0
    failed = 0
    total_sections = 0

    for act in get_acts():
        act_id = str(act.get("id") or "").strip()
        title = (
            act.get("short_title")
            or act.get("title")
            or act_id
        )

        if not act_id:
            continue

        if was_imported(act_id):
            skipped += 1
            continue

        try:
            detail_url = f"{API_BASE}/acts/{act_id}"
            detail = request_json(
                detail_url,
                params={"include": "text"}
            )

            count, saved_title = save_act(act, detail)
            completed += 1
            total_sections += count

            print(
                f"[{completed}] Saved {saved_title} "
                f"({count} records)"
            )

        except Exception as exc:
            failed += 1
            mark_failed(act_id, title, exc)
            print(f"[FAILED] {title}: {exc}")

    with sqlite3.connect(DB_PATH) as conn:
        act_count = conn.execute("""
            SELECT COUNT(DISTINCT act_id)
            FROM legal_documents
        """).fetchone()[0]

        document_count = conn.execute("""
            SELECT COUNT(*) FROM legal_documents
        """).fetchone()[0]

        text_count = conn.execute("""
            SELECT COUNT(*) FROM legal_documents
            WHERE TRIM(legal_text) != ''
        """).fetchone()[0]

    print("\nIMPORT SUMMARY")
    print(f"Acts stored: {act_count}")
    print(f"Document/section records: {document_count}")
    print(f"Records containing text: {text_count}")
    print(f"New Acts completed this run: {completed}")
    print(f"Previously imported Acts skipped: {skipped}")
    print(f"Failures this run: {failed}")
    print(f"Database file: {DB_PATH}")
    print(
        "\nImported text is NOT automatically legally verified. "
        "Check source URLs and amendments before relying on it."
    )


if __name__ == "__main__":
    main()
