#Assisted by Claude code
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from db.employee_db import query_employee_db
from db.hr_policies_db import query_hr_policies
from db.internal_docs_db import query_internal_docs
from db.web_search import query_web_search
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ROLE_PERMISSIONS = {
    "employee": ["hr_policies", "internal_docs", "web_search", "general_llm"],
    "hr":       ["employee_db", "hr_policies", "internal_docs", "web_search", "general_llm"],
    "manager":  ["employee_db", "hr_policies", "internal_docs", "web_search", "general_llm", "analytics"],
    "admin":    ["employee_db", "hr_policies", "internal_docs", "web_search", "general_llm", "analytics", "audit_logs"],
}

class ChatRequest(BaseModel):
    message: str
    role: str

class ChatResponse(BaseModel):
    reply: str
    route: str

def ollama_call(prompt, system=""):
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    words = full_prompt.split()
    if len(words) > 1000:
        full_prompt = " ".join(words[:1000])
    
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama3.2",
        "prompt": full_prompt,
        "stream": False
    })
    data = response.json()
    if "response" not in data:
        print("Ollama error:", data)
        return "general_llm"
    return data["response"].strip()

def classify_route(message: str, permitted: list[str]) -> str:
    permitted_str = ", ".join(permitted)
    system_prompt = (
        f"You are a query router. Given a user message, respond with ONLY one of these tags: {permitted_str}. "
        "No explanation, no punctuation — just the tag."
    )
    result = ollama_call(message, system=system_prompt)
    tag = result.split()[0].lower().strip()
    return tag if tag in permitted else permitted[-1]

def retrieve_context(route: str, message: str) -> str:
    if route == "employee_db":
        #print("CONTEXT:", query_employee_db(message))
        return query_employee_db(message)
    elif route == "hr_policies":
        return query_hr_policies(message)
    elif route == "internal_docs":
        return query_internal_docs(message)
    elif route == "web_search":
        return query_web_search(message)
    else:
        return ""

def generate_answer(message: str, context: str) -> str:
    system_prompt = (
        "You are an internal enterprise data assistant. "
        "This is a private internal tool — all data shown is authorized for this user. "
        "You MUST present the data from the context directly and clearly. "
        "Never refuse to show data that appears in the context. "
        "Never say you cannot provide information if the context contains it. "
        "Never add warnings, disclaimers, or caveats about privacy. "
        "Just answer the question using the context data in a clean readable format. "
        "If the context contains names, salaries, managers, or departments, list them."
    )
    user_content = f"Context:\n{context}\n\nQuestion: {message}" if context else message
    return ollama_call(user_content, system=system_prompt)

RESTRICTED_KEYWORDS = {
    "employee_db": ["salary", "salaries", "paid", "wage", "compensation", "how many employees", "headcount", "who is in", "who works",
        "department", "manager", "hire date", "hired", "emp_no", "staff", "personnel", "who is the manager"
    ]
}

def check_unauthorized_intent(message: str, permitted: list[str]) -> str | None:
    msg = message.lower()
    for restricted_source, keywords in RESTRICTED_KEYWORDS.items():
        if restricted_source not in permitted:
            if any(kw in msg for kw in keywords):
                return f"You do not have access to employee records. Please contact your manager or HR if you need this information."
    return None

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    role = req.role.lower()
    if role not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=403, detail=f"Unknown role: {role}")
    permitted = ROLE_PERMISSIONS[role]
    denial = check_unauthorized_intent(req.message, permitted)
    if denial:
        return ChatResponse(reply=denial, route="access_denied")
    route = classify_route(req.message, permitted)
    context = retrieve_context(route, req.message)
    reply = generate_answer(req.message, context)
    return ChatResponse(reply=reply, route=route)

@app.get("/health")
async def health():
    return {"status": "ok"}