import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.model_selection import train_test_split
from sklearn.svm import LinearSVC
from sklearn.metrics import classification_report
import joblib
import time

def main():
    print("Loading dataset...")
    try:
        df = pd.read_csv("intent_training_data.csv")
    except FileNotFoundError:
        print("Error: Could not find intent_training_data.csv. Run the generation script first.")
        return

    print(f"Dataset loaded with {len(df)} rows.")
    
    # 1. Load the embedding model (Downloads automatically the first time)
    # all-MiniLM-L6-v2 is the industry standard for fast, lightweight sentence embeddings
    print("Loading sentence transformer model (all-MiniLM-L6-v2)...")
    embedder = SentenceTransformer('all-MiniLM-L6-v2')

    # 2. Vectorize the text
    print("Converting text queries to dense vectors. This takes a few seconds...")
    start_time = time.time()
    X = embedder.encode(df['query'].tolist(), show_progress_bar=True)
    y = df['label'].tolist()
    print(f"Vectorization complete in {time.time() - start_time:.2f} seconds.")

    # 3. Train/Test Split (80% training, 20% testing for our evaluation)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 4. Train the ML Classifier
    print("Training Linear Support Vector Classifier (SVM)...")
    clf = LinearSVC(random_state=42, dual=False) 
    clf.fit(X_train, y_train)

    # 5. Evaluate the Model (This is what goes in your final report!)
    print("\n--- Model Evaluation ---")
    predictions = clf.predict(X_test)
    report = classification_report(y_test, predictions)
    print(report)

    # 6. Save the model to disk
    model_filename = "intent_classifier.joblib"
    joblib.dump(clf, model_filename)
    print(f"\n✅ Training complete! Classifier saved locally as '{model_filename}'.")

if __name__ == "__main__":
    main()