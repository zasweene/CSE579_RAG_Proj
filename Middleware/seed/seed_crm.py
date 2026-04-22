import psycopg2, os
from dotenv import load_dotenv
load_dotenv()

LEADS = [
    ("John Doe", "Acme Corp", "open", 45000, "Alice Johnson", "2024-11-01", "Interested in enterprise plan"),
    ("Jane Roe", "Globex",    "negotiation", 120000, "Bob Smith", "2024-11-10", "Finalizing contract terms"),
    # add more rows...
]

conn = psycopg2.connect(os.getenv("POSTGRES_URL"))
cur = conn.cursor()
cur.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id SERIAL PRIMARY KEY,
        contact_name TEXT, company TEXT, stage TEXT,
        deal_value INT, owner TEXT, last_contact DATE, notes TEXT
    )
""")
cur.executemany(
    "INSERT INTO leads (contact_name, company, stage, deal_value, owner, last_contact, notes) VALUES (%s,%s,%s,%s,%s,%s,%s)",
    LEADS
)
conn.commit()
conn.close()
print("CRM leads seeded.")