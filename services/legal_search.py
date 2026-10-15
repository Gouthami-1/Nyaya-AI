import re
from datetime import date

from database.database import (
    get_connection,
    initialize_database
)


# ============================================================
# TEXT HELPERS
# ============================================================

def _normalise(text):
    return re.sub(
        r"\s+",
        " ",
        str(text or "")
    ).strip().lower()


def _tokens(text):
    return re.findall(
        r"[a-zA-Z0-9]+",
        _normalise(text)
    )


STOP_WORDS = {
    "i", "me", "my", "mine",
    "a", "an", "the",
    "is", "are", "was", "were", "am",
    "someone", "somebody", "person", "people",
    "he", "she", "they", "them", "their",
    "on", "in", "at", "to", "of", "for",
    "and", "or", "but", "with",
    "this", "that", "it", "its",
    "has", "have", "had",
    "do", "does", "did",
    "who", "what", "when", "where", "why", "how",
    "can", "could", "would", "should"
}


def _meaningful_tokens(text):

    return [
        word
        for word in _tokens(text)
        if word not in STOP_WORDS
        and len(word) >= 3
    ]


# ============================================================
# LEGAL WORD FAMILIES
# ============================================================

WORD_FAMILIES = [

    {
        "steal",
        "steals",
        "stole",
        "stolen",
        "stealing",
        "theft"
    },

    {
        "threat",
        "threaten",
        "threatens",
        "threatened",
        "threatening",
        "threats"
    },

    {
        "harass",
        "harassment",
        "harassing",
        "harassed"
    },

    {
        "scam",
        "scams",
        "scammed",
        "scamming",
        "fraud",
        "fraudulent"
    },

    {
        "cheat",
        "cheats",
        "cheated",
        "cheating",
        "cheating"
    },

    {
        "stalk",
        "stalks",
        "stalked",
        "stalking",
        "stalker",
        "stalkers"
    },

    {
        "injury",
        "injuries",
        "injured",
        "hurt",
        "hurts"
    },

    {
        "threatening",
        "threatened",
        "threaten",
        "threat",
        "threats"
    }
]


def _words_related(word1, word2):

    word1 = word1.lower()
    word2 = word2.lower()

    if word1 == word2:
        return True

    for family in WORD_FAMILIES:

        if word1 in family and word2 in family:
            return True

    return False


def _text_contains_related_word(
    query_word,
    text
):

    for database_word in _tokens(text):

        if _words_related(
            query_word,
            database_word
        ):
            return True

    return False


# ============================================================
# DATE CHECK
# ============================================================

def _is_effective(row, as_of):

    start = row["effective_from"] or ""
    end = row["effective_until"] or ""

    return (
        (not start or start <= as_of)
        and
        (not end or as_of <= end)
    )


# ============================================================
# LEGAL SEARCH
# ============================================================

def search_legal_provisions(
    query,
    limit=10,
    category=None,
    as_of=None
):

    query = str(query or "").strip()

    if len(query) < 3:
        return []

    if len(query) > 2000:
        query = query[:2000]

    try:
        limit = int(limit)

    except (TypeError, ValueError):

        limit = 10

    limit = max(
        1,
        min(limit, 20)
    )

    as_of = (
        as_of
        or date.today().isoformat()
    )

    words = _meaningful_tokens(query)

    if not words:
        return []

    initialize_database()

    # ========================================================
    # IMPORTANT
    #
    # We intentionally retrieve verified provisions directly
    # from SQLite instead of relying on FTS for the first pass.
    #
    # This allows:
    #
    # stole -> stolen -> stealing -> theft
    #
    # to be handled by Python ranking.
    # ========================================================

    with get_connection() as conn:

        sql = """
            SELECT *
            FROM legal_provisions
            WHERE verification_status = 'verified'
        """

        params = []

        if category:

            sql += """
                AND lower(category) = lower(?)
            """

            params.append(category)

        rows = conn.execute(
            sql,
            params
        ).fetchall()

    # ========================================================
    # RANK PROVISIONS
    # ========================================================

    query_lower = _normalise(query)

    results = []

    for row in rows:

        item = dict(row)

        # Check effective date
        if not _is_effective(
            item,
            as_of
        ):
            continue

        act_name = _normalise(
            item["act_name"]
        )

        section_number = _normalise(
            item["section_number"]
        )

        title = _normalise(
            item["section_title"]
        )

        legal_text = _normalise(
            item["legal_text"]
        )

        explanation = _normalise(
            item["explanation"]
        )

        keywords = _normalise(
            item["keywords"]
        )

        category_text = _normalise(
            item["category"]
        )

        # All searchable text
        searchable = " ".join([
            act_name,
            section_number,
            title,
            legal_text,
            explanation,
            keywords,
            category_text
        ])

        score = 0
        matched_words = 0

        # ----------------------------------------------------
        # WORD MATCHING
        # ----------------------------------------------------

        for word in words:

            # Strong match in title
            if _text_contains_related_word(
                word,
                title
            ):

                score += 8
                matched_words += 1

                continue

            # Strong match in keywords
            if _text_contains_related_word(
                word,
                keywords
            ):

                score += 7
                matched_words += 1

                continue

            # Match in explanation
            if _text_contains_related_word(
                word,
                explanation
            ):

                score += 4
                matched_words += 1

                continue

            # Match in legal text
            if _text_contains_related_word(
                word,
                legal_text
            ):

                score += 3
                matched_words += 1

                continue

            # Match in category
            if _text_contains_related_word(
                word,
                category_text
            ):

                score += 2
                matched_words += 1

                continue

            # Match anywhere else
            if _text_contains_related_word(
                word,
                searchable
            ):

                score += 1
                matched_words += 1

        # ----------------------------------------------------
        # EXACT PHRASE BONUS
        # ----------------------------------------------------

        if query_lower in searchable:

            score += 10

        # ----------------------------------------------------
        # EXACT SECTION BONUS
        # ----------------------------------------------------

        if query_lower == section_number:

            score += 20

        # ----------------------------------------------------
        # SKIP COMPLETELY UNRELATED RESULTS
        # ----------------------------------------------------

        if matched_words == 0:
            continue

        item["search_score"] = score
        item["matched_words"] = matched_words

        results.append(item)

    # ========================================================
    # SORT
    # ========================================================

    results.sort(
        key=lambda item: (
            item["search_score"],
            item["matched_words"],
            item["verified_date"]
        ),
        reverse=True
    )

    return results[:limit]


# ============================================================
# FORMAT RESULTS
# ============================================================

def format_legal_results(results):

    if not results:

        return (
            "No verified matching legal provision "
            "was found in the current database. "
            "Do not infer or invent a section."
        )

    blocks = []

    for item in results:

        blocks.append(

            f"Act: "
            f"{item['act_name']} "
            f"({item['act_year']})\n"

            f"Section: "
            f"{item['section_number']} — "
            f"{item['section_title']}\n"

            f"Category: "
            f"{item['category']}\n"

            f"Explanation: "
            f"{item['explanation']}\n"

            f"Legal text: "
            f"{item['legal_text']}\n"

            f"Official source: "
            f"{item['source_url']}\n"

            f"Verified on: "
            f"{item['verified_date']}\n"

            f"Jurisdiction: "
            f"{item['jurisdiction']}\n"
        )

    return "\n---\n".join(blocks)


# ============================================================
# APP COMPATIBILITY
# ============================================================

def retrieve_legal_sources(
    query,
    limit=6
):

    results = search_legal_provisions(
        query,
        limit=limit
    )

    sources = []

    for item in results:

        sources.append({

            "act_name":
                item.get(
                    "act_name",
                    ""
                ),

            "act_year":
                item.get(
                    "act_year",
                    ""
                ),

            "section_number":
                item.get(
                    "section_number",
                    ""
                ),

            "section_title":
                item.get(
                    "section_title",
                    ""
                ),

            "legal_text":
                item.get(
                    "legal_text",
                    ""
                ),

            "explanation":
                item.get(
                    "explanation",
                    ""
                ),

            "keywords":
                item.get(
                    "keywords",
                    ""
                ),

            "category":
                item.get(
                    "category",
                    ""
                ),

            "jurisdiction":
                item.get(
                    "jurisdiction",
                    "India"
                ),

            "source_url":
                item.get(
                    "source_url",
                    ""
                ),

            "verified_date":
                item.get(
                    "verified_date",
                    ""
                ),

            "effective_from":
                item.get(
                    "effective_from",
                    ""
                ),

            "effective_until":
                item.get(
                    "effective_until",
                    ""
                ),

            "verification_status":
                item.get(
                    "verification_status",
                    ""
                ),

            "search_score":
                item.get(
                    "search_score",
                    0
                )
        })

    return sources