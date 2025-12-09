"""
Content Extractor Node - Extracts mandatory teaching elements from outlines.

This node analyzes an outline and extracts structured elements that the 
script generator MUST include:
- Analogies (real-world comparisons - these are gold for teaching)
- Examples (concrete demonstrations)
- Key Terms (vocabulary to emphasize)
- Learning Objectives (what the learner will DO)

The script generator receives these as NON-NEGOTIABLE inclusions.
"""

import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, InternalServerError
from models.state import AgentState

load_dotenv()

EXTRACTOR_PROMPT = """You are a content extractor for educational tutorials.

Your job is to READ the outline carefully and EXTRACT the teaching gems that make content memorable and effective.

=== INPUT OUTLINE ===
{outline}

=== EXTRACTION TASK ===
Find and extract the following elements. Be THOROUGH - do not miss any analogies or examples!

1. **ANALOGIES**: Any comparison to real-world concepts (e.g., "like Russian dolls", "think of it as a recipe")
   - These are CRITICAL for learning. Extract the full analogy, not just a reference.

2. **EXAMPLES**: Concrete demonstrations or scenarios (e.g., "identifying a cat from images", "phone suggesting words")
   - Include the setup and the teaching point.

3. **LEARNING_OBJECTIVES**: What the learner will be able to DO after this tutorial.
   - Start with action verbs: Understand, Explain, Compare, Identify, etc.

4. **HOOK_IDEAS**: Engaging questions or statements that could start the tutorial.

=== OUTPUT FORMAT ===
Return ONLY valid JSON in this exact structure:
{{
    "analogies": [
        {{"name": "short name", "full_text": "the complete analogy as written", "teaching_point": "what it teaches"}}
    ],
    "examples": [
        {{"name": "short name", "full_text": "the complete example", "teaching_point": "what it demonstrates"}}
    ],
    "learning_objectives": ["LO1", "LO2"],
    "hook_ideas": ["hook1", "hook2"],
    "core_concepts": ["concept1", "concept2", "concept3"]
}}

- Return valid JSON only, no markdown formatting.
"""

@retry(
    retry=retry_if_exception_type((ResourceExhausted, ServiceUnavailable, InternalServerError)),
    wait=wait_exponential(multiplier=4, min=4, max=60),
    stop=stop_after_attempt(5)
)
def extract_content(state: AgentState):
    """Extracts mandatory teaching elements from the outline."""
    print("📦 Extracting content elements from outline...")
    
    outline = state.get('outline')
    if not outline:
        print("⚠️ No outline provided, skipping extraction")
        return {"extracted_content": None}
    
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    
    prompt = EXTRACTOR_PROMPT.format(outline=outline)
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,  # Low temperature for accurate extraction
                response_mime_type="application/json"  # Force JSON output
            )
        )
        
        extracted_text = response.text.strip()
        
        # Parse the JSON response
        try:
            extracted_content = json.loads(extracted_text)
        except json.JSONDecodeError:
            # Try to clean up the response if it has markdown formatting
            cleaned = extracted_text.replace("```json", "").replace("```", "").strip()
            extracted_content = json.loads(cleaned)
        
        # Log what we found
        num_analogies = len(extracted_content.get('analogies', []))
        num_examples = len(extracted_content.get('examples', []))
        num_terms = len(extracted_content.get('key_terms', []))
        
        print(f"✓ Extracted: {num_analogies} analogies, {num_examples} examples, {num_terms} key terms")
        
        # Log the analogies specifically (these are gold)
        for analogy in extracted_content.get('analogies', []):
            print(f"  📌 Analogy: {analogy.get('name', 'unnamed')}")
        
        return {
            "extracted_content": extracted_content,
            "original_outline": outline  # Keep original for reference
        }
        
    except Exception as e:
        print(f"ERROR extracting content: {e}")
        import traceback
        traceback.print_exc()
        # Fallback: return empty extraction
        return {
            "extracted_content": {
                "analogies": [],
                "examples": [],
                "key_terms": [],
                "learning_objectives": [],
                "hook_ideas": [],
                "core_concepts": []
            },
            "original_outline": outline
        }


# Keep the old function name as an alias for backward compatibility
def distill_outline(state: AgentState):
    """Alias for extract_content for backward compatibility."""
    return extract_content(state)
