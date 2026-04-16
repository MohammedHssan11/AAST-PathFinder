# Semantic Tagging with Gemini (ETL Integration)

While integrating `thefuzz` dynamically improves real-time keyword matching with low latency, a highly recommended architectural upgrade is to move "Semantic Tagging" into the offline ETL pipeline using Gemini.

Instead of writing manual regex aliases (e.g. `business` -> `marketing`), we can instruct Gemini to analyze raw college program descriptions **during ingestion** and tag them with broad, standardized academic indices.

## Example: Updating `normalize_colleges_v2.py`

When processing a raw JSON file containing a program like "BSc in Intelligent Computer Systems", you can leverage the `google-generativeai` client (or `google-genai`) to generate standardized tags before saving to `decision_programs`.

### 1. Build the Gemini Parsing Function
```python
import google.generativeai as genai
import os

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

def generate_semantic_tags(program_name: str, program_description: str) -> list[str]:
    prompt = f\"\"\"
    You are an academic classifier. I have a college program:
    Name: {program_name}
    Description: {program_description}
    
    Classify this program into 1 to 3 broad categories from the following list ONLY:
    [AI, Business, Engineering, Cybersecurity, Software, Healthcare, Design, Law, Language, Logistics]
    
    Output ONLY a comma-separated list.
    \"\"\"
    
    response = model.generate_content(prompt)
    raw_tags = response.text.strip().split(',')
    return [tag.strip().lower() for tag in raw_tags if tag.strip()]
```

### 2. Invoke during Ingestion
Inside the ingestion loop of your setup script:
```python
for raw_prog in raw_college["programs"]:
    # ... extraction logic ...
    
    # Generate static tags once offline
    semantic_tags = generate_semantic_tags(
        program_name=raw_prog.get("name", ""),
        program_description=raw_prog.get("description", "")
    )
    
    # Store these directly in the database (e.g., in a `ProgramTags` relationship table)
    # Then your real-time Recommendation Endpoint can simply query:
    # `if student_interest in program.tags` without needing fuzzy math at all!
```

### Why this is better:
1. **Zero Runtime Latency:** Asking Gemini during a user HTTP request takes 1-3 seconds. Asking it during offline ETL takes virtually 0 seconds of the student's time.
2. **Perfect Catch Rate:** It inherently understands that "Data Mining" maps to "AI", without needing fuzzy string similarities.
3. **Cheaper:** API costs are incurred exactly once per program (when the script runs), not every time a user clicks "Recommend".
