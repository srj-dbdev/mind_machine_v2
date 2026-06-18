from database.db import get_connection

conn = get_connection()

cur = conn.cursor()

cur.execute("""
INSERT INTO topics (topic, source)
VALUES (%s, %s)
""", (
    "AI Agents are replacing workflows",
    "Manual Test"
))

conn.commit()

cur.execute("SELECT * FROM topics")

rows = cur.fetchall()

for row in rows:
    print(row)

cur.close()
conn.close()