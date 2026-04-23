import csv, psycopg2, os
from dotenv import load_dotenv
load_dotenv()

with open("data/employees.csv") as f:
    reader = csv.DictReader(f)
    EMPLOYEES = [
        (r["emp_no"], r["birth_date"], r["first_name"], r["last_name"],
         r["sex"], r["hire_date"], r["salary"], r["dept_no"],
         r["dept_name"], r["emp_manager"], r["title_id"], r["title"])
        for r in reader
    ]

conn = psycopg2.connect(os.getenv("POSTGRES_URL"))
cur = conn.cursor()
cur.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        emp_no      INT PRIMARY KEY,
        birth_date  DATE,
        first_name  TEXT,
        last_name   TEXT,
        sex         TEXT,
        hire_date   DATE,
        salary      INT,
        dept_no     TEXT,
        dept_name   TEXT,
        emp_manager TEXT,
        title_id    TEXT,
        title       TEXT
    )
""")
cur.executemany("""
    INSERT INTO employees (emp_no, birth_date, first_name, last_name, sex,
        hire_date, salary, dept_no, dept_name, emp_manager, title_id, title)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    ON CONFLICT (emp_no) DO NOTHING
""", EMPLOYEES)
conn.commit()
conn.close()
print("Employees seeded.")