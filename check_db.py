import sqlite3

connection = sqlite3.connect("nyaya.db")

tables = connection.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()

print("TABLES:")
for table in tables:
    print("-", table[0])

count = connection.execute(
    "SELECT COUNT(*) FROM legal_provisions"
).fetchone()[0]

print()
print("LEGAL PROVISIONS:", count)

connection.close()