import psycopg2, os
from dotenv import load_dotenv
load_dotenv()

def get_conn():
    return psycopg2.connect(os.getenv("POSTGRES_URL"))

def query_employee_db(message: str) -> str:
    msg = message.lower()
    conn = get_conn()
    cur = conn.cursor()

    # Try to match a name mentioned in the message
    cur.execute("SELECT first_name, last_name FROM employees")
    all_names = [(r[0].lower(), r[1].lower()) for r in cur.fetchall()]

    name_filter = None
    for first, last in all_names:
        if first in msg or last in msg:
            name_filter = (first, last)
            break

    if name_filter:
        cur.execute("""
            SELECT emp_no, first_name, last_name, title, dept_name,
                   salary, emp_manager, hire_date
            FROM employees
            WHERE LOWER(first_name) = %s AND LOWER(last_name) = %s
        """, name_filter)
    elif "salary" in msg:
        cur.execute("""
            SELECT emp_no, first_name, last_name, title, dept_name, salary
            FROM employees
            ORDER BY salary DESC
            LIMIT 20
        """)
    elif any(w in msg for w in ["department", "dept", "team"]):
        cur.execute("""
            SELECT dept_no, dept_name, COUNT(*) as headcount
            FROM employees
            GROUP BY dept_no, dept_name
            ORDER BY dept_name
        """)
    else:
        cur.execute("""
            SELECT emp_no, first_name, last_name, title, dept_name, salary
            FROM employees
            ORDER BY last_name
            LIMIT 20
        """)

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "No matching employees found."

    result = "\n".join(" | ".join(str(v) for v in row) for row in rows)
    return result