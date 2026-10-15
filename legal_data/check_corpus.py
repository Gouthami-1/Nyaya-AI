import sqlite3
from pathlib import Path

db_path = Path(__file__).with_name("legal_corpus.db")

with sqlite3.connect(db_path) as conn:
    print("Total records:",
          conn.execute(
              "SELECT COUNT(*) FROM legal_documents"
          ).fetchone()[0])

    print("Records with text:",
          conn.execute(
              "SELECT COUNT(*) FROM legal_documents "
              "WHERE TRIM(legal_text) != ''"
          ).fetchone()[0])

    print("\nSample records:")
    rows = conn.execute("""
        SELECT act_title, section_number, section_heading
        FROM legal_documents
        LIMIT 10
    """).fetchall()

    for row in rows:
        print(row)

    print("\nFailed imports:",
          conn.execute(
              "SELECT COUNT(*) FROM import_progress "
              "WHERE status = 'failed'"
          ).fetchone()[0])