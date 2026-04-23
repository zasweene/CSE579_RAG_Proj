import psycopg2, os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

def get_conn():
    return psycopg2.connect(os.getenv("POSTGRES_URL"))

def query_employee_db(message: str) -> str:
    msg = message.lower()
    conn = get_conn()
    cur = conn.cursor()

    dept_keywords = ["department", "dept", "team", "division", "group", "in finance", 
                     "in engineering", "in hr", "in marketing", "in sales"]
    
    dept_names = ["finance", "engineering", "hr", "human resources", "marketing", 
                  "sales", "accounting", "operations", "legal", "it"]

    detected_dept = None
    for dept in dept_names:
        if dept in msg:
            detected_dept = dept
            break

    # Name query
    cur.execute("SELECT first_name, last_name FROM employees")
    all_names = [(r[0].lower(), r[1].lower()) for r in cur.fetchall()]
    name_filter = None
    for first, last in all_names:
        if first in msg or last in msg:
            name_filter = (first, last)
            break

    # Run appropriate query
    if detected_dept:
        cur.execute("""
            SELECT first_name, last_name, title, dept_name, salary, emp_manager
            FROM employees
            WHERE LOWER(dept_name) LIKE %s
            ORDER BY last_name
        """, (f"%{detected_dept}%",))

    elif name_filter:
        cur.execute("""
            SELECT emp_no, first_name, last_name, title, dept_name,
                   salary, emp_manager, hire_date
            FROM employees
            WHERE LOWER(first_name) = %s AND LOWER(last_name) = %s
        """, name_filter)

    elif "salary" in msg or "highest paid" in msg or "lowest paid" in msg:
        order = "ASC" if "lowest" in msg else "DESC"
        cur.execute(f"""
            SELECT first_name, last_name, title, dept_name, salary
            FROM employees
            ORDER BY salary {order}
            LIMIT 20
        """)

    elif any(w in msg for w in ["how many", "count", "headcount", "total"]):
        cur.execute("""
            SELECT dept_name, COUNT(*) as headcount
            FROM employees
            GROUP BY dept_name
            ORDER BY headcount DESC
        """)

    else:
        cur.execute("""
            SELECT first_name, last_name, title, dept_name, salary
            FROM employees
            ORDER BY last_name
            LIMIT 20
        """)

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "No matching employees found."

    result = "\n".join(" | ".join(str(v) for v in row) for row in rows)
    return f"Found {len(rows)} result(s):\n{result}"