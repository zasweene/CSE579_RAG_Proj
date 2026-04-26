import psycopg2, os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

#get connection to the enviorment
def get_conn():
    return psycopg2.connect(os.getenv("POSTGRES_URL"))

#add formatting to help LLM read
def format_rows(rows, headers):
    result = ""
    for row in rows:
        result += "\n---\n"
        for header, value in zip(headers, row):
            result += f"{header}: {value}\n"
    return result

#all querys selected to route to employee db go through here
def query_employee_db(message: str) -> str:
    msg = message.lower()
    conn = get_conn()
    cur = conn.cursor()

    #specify department names and associated words
    dept_names = ["finance", "engineering", "hr", "human resources", "marketing",
                  "sales", "accounting", "operations", "legal", "it", "development",
                  "customer service", "research", "production", "quality management"]

    #check for what department is being asked about (if there is one)
    detected_dept = None
    for dept in dept_names:
        if dept in msg:
            detected_dept = dept
            break

    #select for employee names
    cur.execute("SELECT first_name, last_name FROM employees")
    all_names = [(r[0].lower(), r[1].lower()) for r in cur.fetchall()]
    name_filter = None
    for first, last in all_names:
        if first in msg or last in msg:
            name_filter = (first, last)
            break

    if detected_dept:
        cur.execute("""
            SELECT first_name, last_name, title, dept_name, salary, emp_manager
            FROM employees
            WHERE LOWER(dept_name) LIKE %s
            ORDER BY last_name
        """, (f"%{detected_dept}%",))
        rows = cur.fetchall()
        headers = ["First Name", "Last Name", "Title", "Department", "Salary", "Manager"]

    elif name_filter:
        cur.execute("""
            SELECT emp_no, first_name, last_name, title, dept_name,
                   salary, emp_manager, hire_date
            FROM employees
            WHERE LOWER(first_name) = %s AND LOWER(last_name) = %s
        """, name_filter)
        rows = cur.fetchall()
        headers = ["Employee No", "First Name", "Last Name", "Title",
                   "Department", "Salary", "Manager", "Hire Date"]

    elif "salary" in msg or "highest paid" in msg or "lowest paid" in msg:
        order = "ASC" if "lowest" in msg else "DESC"
        cur.execute(f"""
            SELECT first_name, last_name, title, dept_name, salary
            FROM employees
            ORDER BY salary {order}
            LIMIT 20
        """)
        rows = cur.fetchall()
        headers = ["First Name", "Last Name", "Title", "Department", "Salary"]

    elif any(w in msg for w in ["how many", "count", "headcount", "total"]):
        cur.execute("""
            SELECT dept_name, COUNT(*) as headcount
            FROM employees
            GROUP BY dept_name
            ORDER BY headcount DESC
        """)
        rows = cur.fetchall()
        headers = ["Department", "Headcount"]

    else:
        cur.execute("""
            SELECT first_name, last_name, title, dept_name, salary
            FROM employees
            ORDER BY last_name
            LIMIT 20
        """)
        rows = cur.fetchall()
        headers = ["First Name", "Last Name", "Title", "Department", "Salary"]

    conn.close()

    #catch for no matches
    if not rows:
        return "No matching employees found."

    #format and return
    return f"Found {len(rows)} result(s):{format_rows(rows, headers)}"