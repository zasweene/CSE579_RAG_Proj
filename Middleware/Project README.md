# **Semantic RAG Multiplexer: Intent-Based Query Routing**

## **Overview**

This project implements a high-speed "Traffic Controller" for Enterprise Retrieval-Augmented Generation (RAG) systems. Traditional RAG architectures struggle with multi-database environments, and using LLMs to route queries introduces severe latency.

To solve this, we built a Semantic Multiplexer: a machine-learning-driven middleware that intercepts user queries, embeds them, and classifies their intent to route them to the correct data silo in milliseconds.

## **Architecture**

1. **Frontend UI:** A vanilla JavaScript/HTML/CSS chat interface that captures user roles and queries.  
2. **Middleware (FastAPI):** A high-performance Python server that hosts the ML pipeline and intercepts messages.  
3. **The Router Brain:** \- Uses all-MiniLM-L6-v2 (SentenceTransformers) to convert natural language into dense vector embeddings.  
   * Uses a Scikit-Learn LinearSVC model trained on 500 synthetic enterprise queries to classify the intent into one of five categories: hr\_policies, crm\_leads, internal\_docs, employee\_db, or web\_search.

## **Performance Metrics**

* **Routing Latency:** \~50 milliseconds (Compared to 1.5 \- 3.0 seconds for standard LLM routing).  
* **Classification Accuracy:** 94% overall accuracy and F1-score on a hidden test set.

## **Project Structure**

project/  
├── venv/                      \# Virtual environment  
├── generate\_dataset.py        \# Script using local Llama 3 to build the synthetic dataset  
├── intent\_training\_data.csv   \# The generated 500-row balanced dataset  
├── train\_classifier.py        \# Script to vectorize text and train the LinearSVC model  
├── intent\_classifier.joblib   \# The saved, trained ML model ("The Brain")  
├── main.py                    \# FastAPI server bridging the UI and the ML model  
├── rag-chatbot-ui.html        \# The frontend chat interface  
├── requirements.txt           \# Dependencies  
└── README.md                  \# Project documentation

## **Quick Start Guide**

### **1\. Setup the Environment**

Ensure you have Python 3.9+ installed. Navigate to the project directory and create a virtual environment:

python \-m venv venv  
\# Windows  
.\\venv\\Scripts\\activate  
\# Mac/Linux  
source venv/bin/activate

### **2\. Install Dependencies**

pip install \-r requirements.txt

### **3\. Run the Backend Server**

python main.py

*Wait for the console to display: ✅ Models loaded successfully\! Server is ready.*

### **4\. Launch the Frontend**

Simply double-click the rag-chatbot-ui.html file to open it in any modern web browser. Select a role, type a query, and watch the ML router tag your request in real-time.