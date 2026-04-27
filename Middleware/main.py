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

class ChatRequest(BaseModel):
    message: str
    role: str

# Define roles and permitted databases per the system architecture
ROLE_PERMISSIONS = {
    "Employee": ["hr_policies", "internal_docs", "web_search", "general_llm"],
    "HR": ["employee_db", "hr_policies", "internal_docs", "web_search", "general_llm"],
    "Manager": ["employee_db", "hr_policies", "internal_docs", "web_search", "general_llm", "analytics"],
    "Admin": ["employee_db", "hr_policies", "internal_docs", "web_search", "general_llm", "analytics", "audit_logs"]
}

# Global ML model variables
embedder = None
classifier = None

@app.on_event("startup")
async def load_models():
    global embedder, classifier
    print("Loading embedding model (all-MiniLM-L6-v2)...")
    # Using a fast, lightweight sentence transformer for intent classification
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    
    print("Loading trained intent classifier...")
    model_path = "intent_classifier.joblib"
    if os.path.exists(model_path):
        classifier = joblib.load(model_path)
        print("Models loaded successfully!")
    else:
        print("ERROR: Could not find intent_classifier.joblib. Please run train_classifier.py first.")

PG_HOST = "localhost"
PG_DBNAME = "nexusai"

def retrieve_from_db(route: str, query: str) -> str:
    context = ""
    try:
        if route == "employee_db":
            context = query_employee_db(query)

        elif route == "hr_policies":
           context = query_hr_policies(query)

        elif route == "internal_docs":
            context = query_internal_docs(query)

        elif route == "web_search":
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
                if results:
                    context_lines = [f"Web Result: {r['body']}" for r in results]
                    context = "\n".join(context_lines)
                else:
                    context = "No recent web information found."

        elif route == "general_llm":
            context = "" 

        return f"Context retrieved:\n{context}"

    except Exception as e:
        print(f"Database Error for route {route}: {e}")
        return "System error: Could not retrieve data from the database."

# -------------------------------------------------------------------
# 4. MAIN CHAT ENDPOINT
# -------------------------------------------------------------------
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    if not classifier or not embedder:
        raise HTTPException(status_code=500, detail="ML Models not loaded.")
    
    user_message = request.message
    
    # Normalize incoming role (e.g. 'employee' -> 'Employee', 'hr' -> 'HR')
    role_map = {
        "employee": "Employee", 
        "hr": "HR", 
        "manager": "Manager", 
        "admin": "Admin"
    }
    
    normalized_role = request.role.strip().lower()
    
    if normalized_role not in role_map:
        raise HTTPException(status_code=400, detail=f"Invalid role specified: {request.role}")
        
    user_role = role_map[normalized_role]
    allowed_routes = ROLE_PERMISSIONS[user_role]
    
    try:
        # --- Step 2: ML Route Prediction (Replaces LLM Router) ---
        # Vectorize the user's message
        vector = embedder.encode([user_message])
        # Predict the exact database tag
        predicted_route = classifier.predict(vector)[0]
        
        # --- Step 3: Enforce Access Control ---
        # Crucial security check: The ML model doesn't know about roles.
        # If it predicts a database the user isn't allowed to see, we intercept it.
        if predicted_route not in allowed_routes:
            print(f"⚠️ Access Denied: {user_role} attempted to access {predicted_route}.")
            # Force route to general_llm so it just answers like a normal chatbot
            # without accessing sensitive restricted databases.
            predicted_route = "general_llm"
            
        # --- Step 4: Retrieve Context ---
        context = retrieve_from_db(predicted_route, user_message)
        
        # --- Step 5: Generate Final Answer with Local LLM ---
        # We pass the retrieved data to the LLM to ground its response.
        if predicted_route == "general_llm":
            prompt = user_message
        else:
            prompt = f"Using ONLY the following context, answer the user's question.\n\nContext:\n{context}\n\nQuestion: {user_message}"
        
        print(f"Routing to: {predicted_route} | Generating response...")
        
        response = ollama.chat(model='llama3.2', messages=[
            {
                'role': 'user',
                'content': prompt
            }
        ])
        
        final_answer = response['message']['content']
        
        # --- Step 6: Return to Frontend ---
        return {
            "reply": final_answer,
            "route": predicted_route
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)