
from database.database import get_connection

with get_connection() as conn:
    print("DATABASE:")
    print(conn.execute("PRAGMA database_list").fetchall())

    print("\nVERIFICATION STATUS:")
    rows = conn.execute("""
        SELECT verification_status, COUNT(*)
        FROM legal_provisions
        GROUP BY verification_status
    """).fetchall()

    for row in rows:
        print(tuple(row))
