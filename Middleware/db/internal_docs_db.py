import psycopg2
import os
import requests
from dotenv import load_dotenv
load_dotenv()

#load connection 
def get_conn():
    return psycopg2.connect(os.getenv("POSTGRES_URL"))

#ollama text embedding
def get_embedding(text: str) -> list[float]:
    response = requests.post("http://localhost:11434/api/embeddings", json={
        "model": "nomic-embed-text",
        "prompt": text
    })
    return response.json()["embedding"]

#query the internal documents, adding ranked chunking to improve answers
def query_internal_docs(message: str) -> str:
    embedding = get_embedding(message)
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT title, chunk_text, 
           1 - (embedding <-> %s::vector) as similarity
    FROM documents
    ORDER BY embedding <-> %s::vector
    LIMIT 10
    """, (embedding, embedding))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "No relevant internal documents found."

    filtered = [(title, chunk) for title, chunk, score in rows if score > 0.3]
    return "\n\n".join(f"[{title}]\n{chunk}" for title, chunk in filtered[:5])