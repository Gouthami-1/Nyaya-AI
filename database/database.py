import sqlite3
from pathlib import Path
from contextlib import contextmanager


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "nyaya.db"


@contextmanager
def get_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        str(DATABASE_PATH),
        timeout=10
    )

    connection.row_factory = sqlite3.Row

    try:
        connection.execute("PRAGMA foreign_keys = ON")
        yield connection
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def initialize_database():

    with get_connection() as conn:

        # -----------------------------------------
        # LEGAL PROVISIONS
        # -----------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS legal_provisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                act_name TEXT NOT NULL,
                act_year INTEGER NOT NULL,
                section_number TEXT NOT NULL,
                section_title TEXT NOT NULL,
                legal_text TEXT NOT NULL,
                explanation TEXT NOT NULL DEFAULT '',
                keywords TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT 'general',
                jurisdiction TEXT NOT NULL DEFAULT 'India',
                source_url TEXT NOT NULL DEFAULT '',
                verified_date TEXT NOT NULL DEFAULT '',
                effective_from TEXT NOT NULL DEFAULT '',
                effective_until TEXT NOT NULL DEFAULT '',
                verification_status TEXT NOT NULL DEFAULT 'pending',

                UNIQUE(
                    act_name,
                    act_year,
                    section_number
                )
            )
        """)

        # -----------------------------------------
        # CHAT HISTORY
        # -----------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_chat_conversation
            ON chat_messages(conversation_id, id)
        """)

        # -----------------------------------------
        # FULL TEXT SEARCH
        # -----------------------------------------

        try:

            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS
                legal_provisions_fts
                USING fts5(
                    act_name,
                    section_number,
                    section_title,
                    legal_text,
                    explanation,
                    keywords,
                    category,
                    content='legal_provisions',
                    content_rowid='id'
                )
            """)

            # INSERT trigger
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS
                legal_provisions_ai
                AFTER INSERT ON legal_provisions
                BEGIN

                    INSERT INTO legal_provisions_fts(
                        rowid,
                        act_name,
                        section_number,
                        section_title,
                        legal_text,
                        explanation,
                        keywords,
                        category
                    )
                    VALUES(
                        new.id,
                        new.act_name,
                        new.section_number,
                        new.section_title,
                        new.legal_text,
                        new.explanation,
                        new.keywords,
                        new.category
                    );

                END
            """)

            # DELETE trigger
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS
                legal_provisions_ad
                AFTER DELETE ON legal_provisions
                BEGIN

                    INSERT INTO legal_provisions_fts(
                        legal_provisions_fts,
                        rowid,
                        act_name,
                        section_number,
                        section_title,
                        legal_text,
                        explanation,
                        keywords,
                        category
                    )
                    VALUES(
                        'delete',
                        old.id,
                        old.act_name,
                        old.section_number,
                        old.section_title,
                        old.legal_text,
                        old.explanation,
                        old.keywords,
                        old.category
                    );

                END
            """)

            # UPDATE trigger
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS
                legal_provisions_au
                AFTER UPDATE ON legal_provisions
                BEGIN

                    INSERT INTO legal_provisions_fts(
                        legal_provisions_fts,
                        rowid,
                        act_name,
                        section_number,
                        section_title,
                        legal_text,
                        explanation,
                        keywords,
                        category
                    )
                    VALUES(
                        'delete',
                        old.id,
                        old.act_name,
                        old.section_number,
                        old.section_title,
                        old.legal_text,
                        old.explanation,
                        old.keywords,
                        old.category
                    );

                    INSERT INTO legal_provisions_fts(
                        rowid,
                        act_name,
                        section_number,
                        section_title,
                        legal_text,
                        explanation,
                        keywords,
                        category
                    )
                    VALUES(
                        new.id,
                        new.act_name,
                        new.section_number,
                        new.section_title,
                        new.legal_text,
                        new.explanation,
                        new.keywords,
                        new.category
                    );

                END
            """)

            # Rebuild search index
            conn.execute("""
                INSERT INTO legal_provisions_fts(
                    legal_provisions_fts
                )
                VALUES('rebuild')
            """)

        except sqlite3.OperationalError as error:

            print(
                "FTS5 search index unavailable:",
                error
            )


def init_db():
    """Compatibility function used by app.py."""
    initialize_database()


def search_provisions(query, limit=10):

    from services.legal_search import (
        search_legal_provisions
    )

    return search_legal_provisions(
        query,
        limit=limit
    )


def save_message(
    conversation_id,
    role,
    content
):

    with get_connection() as conn:

        conn.execute("""
            INSERT INTO chat_messages(
                conversation_id,
                role,
                content
            )
            VALUES (?, ?, ?)
        """, (
            conversation_id,
            role,
            content
        ))


def get_history(conversation_id):

    with get_connection() as conn:

        rows = conn.execute("""
            SELECT
                role,
                content
            FROM chat_messages
            WHERE conversation_id = ?
            ORDER BY id ASC
        """, (
            conversation_id,
        )).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def delete_history(conversation_id):

    with get_connection() as conn:

        conn.execute("""
            DELETE FROM chat_messages
            WHERE conversation_id = ?
        """, (
            conversation_id,
        ))