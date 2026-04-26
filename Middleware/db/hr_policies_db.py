import sqlite3
import os
from dotenv import load_dotenv
load_dotenv()

#path to db
DB_PATH = os.getenv("SQLITE_PATH", "./db/hr_policies.db")

#format and execute the query
def query_hr_policies(message: str) -> str:
    keywords = message.lower().split()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    #execute the query 
    results = []
    for kw in keywords:
        cur.execute("""
            SELECT topic, content FROM policies
            WHERE LOWER(topic) LIKE ? OR LOWER(content) LIKE ?
        """, (f"%{kw}%", f"%{kw}%"))
        results.extend(cur.fetchall())

    conn.close()

    #Deduplicate
    seen = set()
    unique = []
    for topic, content in results:
        if topic not in seen:
            seen.add(topic)
            unique.append((topic, content))

    #catch for no match
    if not unique:
        return "No matching HR policies found."
    
    formatted = ""
    for topic, content in unique[:5]:
        formatted += f"\n---\nPolicy: {topic}\nContent: {content}\n"

    #format and return
    return f"Found {len(unique)} matching policy section(s):{formatted}"