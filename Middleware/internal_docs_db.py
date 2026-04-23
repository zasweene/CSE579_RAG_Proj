import psycopg2
import os
import requests
from dotenv import load_dotenv
load_dotenv()

def get_conn():
    return psycopg2.connect(os.getenv("POSTGRES_URL"))

def get_embedding(text: str) -> list[float]:
    """Get embedding from Ollama nomic-embed-text model."""
    response = requests.post("http://localhost:11434/api/embeddings", json={
        "model": "nomic-embed-text",
        "prompt": text
    })
    return response.json()["embedding"]

def query_internal_docs(message: str) -> str:
    """
    Table schema expected (pgvector):
      documents(id, title, chunk_text, embedding vector(768))
    """
    embedding = get_embedding(message)
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT title, chunk_text
        FROM documents
        ORDER BY embedding <-> %s::vector
        LIMIT 5
    """, (embedding,))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "No relevant internal documents found."

    return "\n\n".join(f"[{title}]\n{chunk}" for title, chunk in rows)