import psycopg2, os, fitz, requests
from dotenv import load_dotenv
load_dotenv()
from langchain_text_splitters import RecursiveCharacterTextSplitter

def extract_pdf(path):
    doc = fitz.open(path)
    return "\n".join(page.get_text() for page in doc)

def chunk_text(text):
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    return splitter.split_text(text)

def get_embedding(text):
    r = requests.post("http://localhost:11434/api/embeddings", json={
        "model": "nomic-embed-text",
        "prompt": text
    })
    #print(r.json())
    return r.json()["embedding"]

# Load internal doc PDFs
DOC_FILES = {
    "OPM Workforce Reshaping":   "data/opm-workforce-reshaping-march-2017.pdf",
    "SES Exit Survey Results":   "data/ses-exit-survey-results.pdf",
    "Valve Employee Handbook":   "data/Valve_NewEmployeeHandbook.pdf",
}

conn = psycopg2.connect(os.getenv("POSTGRES_URL"))
cur = conn.cursor()
cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
cur.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id SERIAL PRIMARY KEY,
        title TEXT,
        chunk_text TEXT,
        embedding vector(768)
    )
""")

for title, path in DOC_FILES.items():
    print(f"Processing {title}...")
    text = extract_pdf(path)
    chunks = chunk_text(text)
    for i, chunk in enumerate(chunks):
        print(f"  Embedding chunk {i+1}/{len(chunks)}")
        emb = get_embedding(chunk)
        cur.execute(
            "INSERT INTO documents (title, chunk_text, embedding) VALUES (%s, %s, %s)",
            (title, chunk, emb)
        )

conn.commit()
conn.close()
print("Internal docs seeded.")