from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import joblib
import ollama
import os
from duckduckgo_search import DDGS
import psycopg2
import sqlite3
import uvicorn
from db.employee_db import query_employee_db
from db.hr_policies_db import query_hr_policies
from db.internal_docs_db import query_internal_docs

app = FastAPI(title="NexusAI Middleware")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#initiate 
class ChatRequest(BaseModel):
    message: str
    role: str

#define the access control permissions for the user roles
ROLE_PERMISSIONS = {
    "Employee": ["hr_policies", "internal_docs", "web_search", "general_llm"],
    "HR": ["employee_db", "hr_policies", "internal_docs", "web_search", "general_llm"],
    "Manager": ["employee_db", "hr_policies", "internal_docs", "web_search", "general_llm", "analytics"],
    "Admin": ["employee_db", "hr_policies", "internal_docs", "web_search", "general_llm", "analytics", "audit_logs"]
}

#define vars
embedder = None
classifier = None

#set up enviorment: load embedder and classifier
@app.on_event("startup")
async def load_models():
    global embedder, classifier
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    
    model_path = "intent_classifier.joblib"
    if os.path.exists(model_path):
        classifier = joblib.load(model_path)
    else:
        print("ERROR: Could not find intent_classifier.joblib. Please run train_classifier.py first.")

#define more vars
PG_HOST = "localhost"
PG_DBNAME = "nexusai"

#rretrieve from backend data stores
def retrieve_from_db(route: str, query: str) -> str:
    context = ""
    try:
        #call query function within the db code for each non-web route
        if route == "employee_db":
            context = query_employee_db(query)

        elif route == "hr_policies":
           context = query_hr_policies(query)

        elif route == "internal_docs":
            context = query_internal_docs(query)

        #fall back on web search if ML doesn't find relevant route
        elif route == "web_search":
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
                if results:
                    context_lines = [f"Web Result: {r['body']}" for r in results]
                    context = "\n".join(context_lines)
                else:
                    context = "No recent web information found."

        #fall back for no relevant data
        elif route == "general_llm":
            context = "" 
        #return context information
        return f"Context retrieved:\n{context}"

    #catch errors
    except Exception as e:
        print(f"Database Error for route {route}: {e}")
        return "System error: Could not retrieve data from the database."

#chat interface components
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    if not classifier or not embedder:
        raise HTTPException(status_code=500, detail="ML Models not loaded.")
    
    #get user request
    user_message = request.message
    
    #map to role variables
    role_map = {
        "employee": "Employee", 
        "hr": "HR", 
        "manager": "Manager", 
        "admin": "Admin"
    }
    
    #make all same style (lowercase, no trailing space/newline)
    normalized_role = request.role.strip().lower()
    
    #error out on incorrect role
    if normalized_role not in role_map:
        raise HTTPException(status_code=400, detail=f"Invalid role specified: {request.role}")
        
    #define route and role vars
    user_role = role_map[normalized_role]
    allowed_routes = ROLE_PERMISSIONS[user_role]
    
    try:
        #get embedding and predict the route using ML model
        vector = embedder.encode([user_message])
        predicted_route = classifier.predict(vector)[0]
        
        #error catch for non-existent route
        if predicted_route not in allowed_routes:
            print(f"Access Denied: {user_role} attempted to access {predicted_route}.")
            predicted_route = "general_llm"
        
        #run function to get data from database
        context = retrieve_from_db(predicted_route, user_message)

        #Run Llama prompt using full context generated above
        if predicted_route == "general_llm":
            prompt = user_message
        else:
            #prompt Llama 3.2 include context and original user message to give full scope
            prompt = f"Using ONLY the following context, answer the user's question.\n\nContext:\n{context}\n\nQuestion: {user_message}"
        
        #map response
        response = ollama.chat(model='llama3.2', messages=[
            {
                'role': 'user',
                'content': prompt
            }
        ])
        
        #link message and content
        final_answer = response['message']['content']
        
        #return
        return {
            "reply": final_answer,
            "route": predicted_route
        }
        
    #catch error
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#main call, link to frontend
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)