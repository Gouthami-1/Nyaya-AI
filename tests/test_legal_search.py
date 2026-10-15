
import pytest

import database.database as db
from database.database import get_connection, initialize_database
from services.legal_search import (
    search_legal_provisions,
    format_legal_results,
)


@pytest.fixture
def temporary_database(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "test.db")
    initialize_database()

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO legal_provisions (
                act_name, act_year, section_number, section_title,
                legal_text, explanation, keywords, category,
                jurisdiction, source_url, verified_date,
                effective_from, effective_until, verification_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "TEST ACT — NOT REAL LAW", 2025, "TEST-1",
            "Dummy threat provision",
            "Dummy text for testing only.",
            "Dummy explanation for automated testing.",
            "threat message online",
            "cybercrime", "Test jurisdiction",
            "https://www.gov.in/test",
            "2025-01-01", "", "", "verified"
        ))

        conn.execute("""
            INSERT INTO legal_provisions (
                act_name, act_year, section_number, section_title,
                legal_text, explanation, keywords, category,
                jurisdiction, source_url, verified_date,
                effective_from, effective_until, verification_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "UNVERIFIED TEST ACT", 2025, "TEST-2",
            "Unverified provision",
            "This must not be returned.",
            "Not verified", "threat message",
            "cybercrime", "Test jurisdiction",
            "https://www.gov.in/unverified",
            "2025-01-01", "", "", "pending"
        ))


def test_returns_verified_matches_only(temporary_database):
    results = search_legal_provisions("threat message online")

    assert results
    assert all(
        result["verification_status"] == "verified"
        for result in results
    )


def test_category_filter(temporary_database):
    results = search_legal_provisions(
        "threat message", category="cybercrime"
    )

    assert results
    assert all(result["category"] == "cybercrime" for result in results)


def test_short_query_returns_no_results(temporary_database):
    assert search_legal_provisions("ab") == []


def test_no_match_is_not_invented(temporary_database):
    results = search_legal_provisions(
        "completely unrelated agricultural machinery"
    )
    assert results == []
    assert "No verified matching" in format_legal_results(results)


def test_source_is_returned(temporary_database):
    results = search_legal_provisions("threat message")

    assert results
    assert results[0]["source_url"].startswith("https://")


def test_limit_is_bounded(temporary_database):
    results = search_legal_provisions("threat message", limit=1000)
    assert len(results) <= 20
