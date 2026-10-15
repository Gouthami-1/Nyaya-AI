from database.database import initialize_database
from services.legal_search import search_legal_provisions

initialize_database()

results = search_legal_provisions(
    "someone physically hurt me",
    limit=5
)

print()
print("SEARCH RESULTS")
print("=" * 50)

for result in results:

    print(
        result["act_name"],
        "— Section",
        result["section_number"]
    )

    print(
        result["section_title"]
    )

    print(
        "Score:",
        result["search_score"]
    )

    print()