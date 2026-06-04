import sqlite3

conn = sqlite3.connect("data/intermediate/imdb.db")

print("Total films:")
print(conn.execute("SELECT COUNT(*) FROM title_basics").fetchone())

print("Films Horror:")
print(
    conn.execute(
        "SELECT COUNT(*) FROM title_basics WHERE genres LIKE '%Horror%'"
    ).fetchone()
)

print("Apercu Horror:")
for row in conn.execute(
    "SELECT tconst, primaryTitle, startYear, genres FROM title_basics WHERE genres LIKE '%Horror%' LIMIT 10"
):
    print(row)

print("Top Horror par votes:")
for row in conn.execute(
    "SELECT b.tconst, b.primaryTitle, r.averageRating, r.numVotes FROM title_basics b JOIN title_ratings r ON b.tconst = r.tconst WHERE b.genres LIKE '%Horror%' ORDER BY r.numVotes DESC LIMIT 10"
):
    print(row)

conn.close()
