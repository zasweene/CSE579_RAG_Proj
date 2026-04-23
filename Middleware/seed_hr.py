import sqlite3, os, fitz
from dotenv import load_dotenv
load_dotenv()

def extract_pdf(path):
    doc = fitz.open(path)
    return "\n".join(page.get_text() for page in doc)

def chunk_text(text, size=300, overlap=50):
    words = text.split()
    chunks = []
    for i in range(0, len(words), size - overlap):
        chunks.append(" ".join(words[i:i+size]))
    return chunks

# Load HR policy PDFs
HR_FILES = {
    "Childbirth & Flexibilities Policy": "data/handbook-on-flexibilities-for-childbirth-adoption-and-foster-care-2025.pdf",
}

conn = sqlite3.connect(os.getenv("SQLITE_PATH", "./db/hr_policies.db"))
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS policies (id INTEGER PRIMARY KEY, topic TEXT, content TEXT)")

for topic, path in HR_FILES.items():
    text = extract_pdf(path)
    for chunk in chunk_text(text):
        cur.execute("INSERT INTO policies (topic, content) VALUES (?, ?)", (topic, chunk))

conn.commit()
conn.close()
print("HR policies seeded.")