import ollama
import pandas as pd
import time

# Define our target labels and the specific context for the LLM
CATEGORIES = {
    "employee_db": "specific employees, looking up PTO balances, salary information, or individual performance reviews.",
    "crm_leads": "sales pipelines, active deals, client names, contract values, or quarterly sales targets.",
    "hr_policies": "company-wide rules, standard benefits, parental leave, expense report guidelines, or remote work policies.",
    "internal_docs": "company history, engineering architecture diagrams, general project guidelines, or standard operating procedures.",
    "web_search": "current real-world events, today's stock prices, recent news, or general facts outside the company."
}

# Parameters
QUESTIONS_PER_CATEGORY = 100
BATCH_SIZE = 20  # Ask for 20 questions per API call to avoid token limits/repetition

def generate_questions(category_name, category_context, num_questions):
    """Calls local Llama 3 to generate questions for a specific category."""
    prompt = f"""
    You are an AI generating training data for a text classification model.
    Generate {num_questions} distinct, realistic, and varied questions that an employee at a tech company might ask.
    These questions MUST specifically require searching a database containing information about: {category_context}
    
    CRITICAL INSTRUCTIONS:
    1. Output strictly the questions, one per line.
    2. Do NOT use any numbering or bullet points.
    3. Do NOT include any introductory or concluding text (e.g., no "Here are your questions:").
    4. Make the phrasing natural (some short, some long, some formal, some casual).
    """

    try:
        response = ollama.chat(model='llama3', messages=[
            {'role': 'system', 'content': 'You are a strict data generation assistant that outputs only raw text lines.'},
            {'role': 'user', 'content': prompt}
        ])
        
        # Split by newlines, strip whitespace, and filter out empty lines
        raw_text = response['message']['content']
        questions = [q.strip() for q in raw_text.split('\n') if q.strip()]
        
        # Clean up any accidental numbering the LLM might have stubbornly included
        clean_questions = [q.lstrip('0123456789.-* ') for q in questions]
        return clean_questions

    except Exception as e:
        print(f"Error generating for {category_name}: {e}")
        return []

def main():
    print("Starting synthetic dataset generation via local Llama 3...")
    dataset = []

    for label, context in CATEGORIES.items():
        print(f"\nGenerating data for: {label}...")
        collected_for_label = 0
        
        while collected_for_label < QUESTIONS_PER_CATEGORY:
            print(f"  -> Requesting batch ({collected_for_label}/{QUESTIONS_PER_CATEGORY})...")
            new_questions = generate_questions(label, context, BATCH_SIZE)
            
            for q in new_questions:
                if q and len(q) > 10:  # Basic quality check
                    dataset.append({"query": q, "label": label})
                    collected_for_label += 1
                    
                    if collected_for_label >= QUESTIONS_PER_CATEGORY:
                        break
            
            # Small sleep to prevent overwhelming the local API/CPU
            time.sleep(1) 

    # Convert to DataFrame
    df = pd.DataFrame(dataset)
    
    # Shuffle the dataset so it isn't perfectly ordered by category
    df = df.sample(frac=1).reset_index(drop=True)
    
    # Save to CSV
    output_filename = "intent_training_data.csv"
    df.to_csv(output_filename, index=False)
    
    print(f"\n✅ Success! Generated {len(df)} labeled queries.")
    print(f"Dataset saved locally as '{output_filename}'.")
    print(df['label'].value_counts())

if __name__ == "__main__":
    main()