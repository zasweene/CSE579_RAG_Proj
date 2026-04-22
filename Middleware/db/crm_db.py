import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()

def get_conn():
    return psycopg2.connect(os.getenv("POSTGRES_URL"))

def query_crm_db(message: str) -> str:
    """
    Table schema expected:
      leads(id, contact_name, company, stage, deal_value, owner, last_contact, notes)
    """
    msg = message.lower()
    conn = get_conn()
    cur = conn.cursor()

    # Filter by stage if mentioned
    stage_map = {
        "open": "open",
        "closed": "closed",
        "negotiation": "negotiation",
        "prospect": "prospect",
        "qualified": "qualified",
    }
    stage_filter = next((v for k, v in stage_map.items() if k in msg), None)

    if stage_filter:
        cur.execute("""
            SELECT contact_name, company, stage, deal_value, owner, last_contact
            FROM leads
            WHERE LOWER(stage) = %s
            ORDER BY deal_value DESC
            LIMIT 20
        """, (stage_filter,))
    else:
        cur.execute("""
            SELECT contact_name, company, stage, deal_value, owner, last_contact
            FROM leads
            ORDER BY last_contact DESC
            LIMIT 20
        """)

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "No CRM leads found."

    result = "Contact | Company | Stage | Value | Owner | Last Contact\n"
    result += "-" * 70 + "\n"
    for row in rows:
        result += " | ".join(str(v) for v in row) + "\n"

    return result