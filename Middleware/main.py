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

#load enviorment variables
load_dotenv(Path(__file__).parent.parent / ".env")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#define what databases each user can access
ROLE_PERMISSIONS = {
    "employee": ["hr_policies", "internal_docs", "web_search", "general_llm"],
    "hr":       ["employee_db", "hr_policies", "internal_docs", "web_search", "general_llm"],
    "manager":  ["employee_db", "hr_policies", "internal_docs", "web_search", "general_llm", "analytics"],
    "admin":    ["employee_db", "hr_policies", "internal_docs", "web_search", "general_llm", "analytics", "audit_logs"],
}

#class for request sent to LLM
class ChatRequest(BaseModel):
    message: str
    role: str
    history: list[dict] = []

#class for LLM response
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

#pcik which data set best fits the query
def classify_route(message: str, permitted: list[str]) -> str:
    permitted_str = ", ".join(permitted)
    system_prompt = (
        f"You are a query router. Given a user message, respond with ONLY one of these tags: {permitted_str}. "
        "No explanation, no punctuation — just the tag."
    )
    result = ollama_call(message, system=system_prompt)
    tag = result.split()[0].lower().strip()
    return tag if tag in permitted else permitted[-1]

#define route 
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
    
#added function, that rewrites a query in a simple form to improve response
def rewrite_query(message: str, history: list[dict]) -> str:
    if not history:
        return message
    history_text = "\n".join(f"{h['role'].upper()}: {h['content']}" for h in history[-4:])
    system_prompt = (
        "Given a conversation history and a follow-up question, "
        "rewrite the follow-up as a clear standalone question. "
        "Return only the rewritten question, nothing else."
    )
    prompt = f"History:\n{history_text}\n\nFollow-up: {message}"
    return ollama_call(prompt, system=system_prompt)

#instructions for model to generate an answer to the users query after getting the retrieved data
def generate_answer(message: str, context: str, history: list[dict]) -> str:
    history_text = "\n".join(
        f"{h['role'].upper()}: {h['content']}" for h in history[-6:]  # last 3 exchanges
    )
    system_prompt = (
        "You are an internal enterprise data assistant. "
        "This is a private internal tool — all data shown is authorized for this user. "
        "You MUST present the data from the context directly and clearly. "
        "Never refuse to show data that appears in the context. "
        "Never add warnings, disclaimers, or caveats about privacy. "
        "Just answer the question using the context data in a clean readable format."
    )
    user_content = f"Conversation so far:\n{history_text}\n\nContext:\n{context}\n\nQuestion: {message}" if context else f"Conversation so far:\n{history_text}\n\nQuestion: {message}"
    return ollama_call(user_content, system=system_prompt)

#restricted words for certain users, utlized in the unathorized_intent function
RESTRICTED_KEYWORDS = {
    "employee_db": ["salary", "salaries", "paid", "wage", "compensation", "how many employees", "headcount", "who is in", "who works",
        "department", "manager", "hire date", "hired", "emp_no", "staff", "personnel", "who is the manager"
    ]
}

#check if message utilizes a database out of permission scope
def check_unauthorized_intent(message: str, permitted: list[str]) -> str | None:
    msg = message.lower()
    for restricted_source, keywords in RESTRICTED_KEYWORDS.items():
        if restricted_source not in permitted:
            if any(kw in msg for kw in keywords):
                return f"You do not have access to employee records. Please contact your manager or HR if you need this information."
    return None

#post chat to the model, get response, send it back to user
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    role = req.role.lower()
    if role not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=403, detail=f"Unknown role: {role}")
    permitted = ROLE_PERMISSIONS[role]
    denial = check_unauthorized_intent(req.message, permitted)
    if denial:
        return ChatResponse(reply=denial, route="access_denied")
    rewritten = rewrite_query(req.message, req.history)
    route = classify_route(rewritten, permitted)
    context = retrieve_context(route, rewritten)
    reply = generate_answer(req.message, context, req.history)
    return ChatResponse(reply=reply, route=route)

#check status of the system, if it doesn't say system "okay" then it isn't up and running
@app.get("/health")
async def health():
    return {"status": "okay"}