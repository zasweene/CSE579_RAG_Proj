from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import joblib
import os

# Define the expected JSON payload from the frontend
class ChatRequest(BaseModel):
    message: str
    role: str

app = FastAPI()

# Enable CORS so your local HTML file can communicate with this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables to hold models in memory
embedder = None
classifier = None

@app.on_event("startup")
async def load_models():
    global embedder, classifier
    print("Loading embedding model (all-MiniLM-L6-v2)...")
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    
    print("Loading trained classifier (Brain)...")
    model_path = "intent_classifier.joblib"
    if os.path.exists(model_path):
        classifier = joblib.load(model_path)
        print("✅ Models loaded successfully! Server is ready.")
    else:
        print("❌ ERROR: Could not find intent_classifier.joblib.")

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    if not classifier or not embedder:
        raise HTTPException(status_code=500, detail="Models not loaded.")
    
    try:
        # 1. Vectorize the incoming text
        vector = embedder.encode([request.message])
        
        # 2. Predict the route using your trained model
        predicted_route = classifier.predict(vector)[0]
        
        # Simulated response (Until you plug in LangChain retrievers later)
        reply = f"System intercepted message. ML Classifier routed query to: {predicted_route.upper()}"
        
        return {
            "reply": reply,
            "route": predicted_route
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Runs the server on localhost port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)