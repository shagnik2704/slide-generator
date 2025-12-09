"""
Style matcher node for adjusting script narration to match sample style.
Loads a sample script and rewrites narration to match its tone, rhythm, and density.
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

# Path to sample script for style reference
SAMPLE_SCRIPT_PATH = os.path.join(
    os.path.dirname(__file__), 
    '..', 
    'sample_scripts', 
    'json', 
    '3cs_prompting.json'
)

def load_sample_narrations() -> str:
    """Load sample script narrations for style reference."""
    try:
        with open(SAMPLE_SCRIPT_PATH, 'r') as f:
            sample = json.load(f)
        
        # Extract just the narrations for style reference
        narrations = []
        for i, slide in enumerate(sample.get('slides', [])[:10]):  # First 10 slides
            narration = slide.get('narration', '')
            if narration:
                narrations.append(f"Slide {i+1}:\n{narration}")
        
        return "\n\n".join(narrations)
    except Exception as e:
        print(f"⚠ Could not load sample script: {e}")
        return ""

# Load sample narrations once at module level
SAMPLE_NARRATIONS = load_sample_narrations()

STYLE_MATCHER_PROMPT = """You are a style editor for Spoken Tutorials.

Your job is to REWRITE the narration to follow Spoken Tutorial principles.

=== SAMPLE SCRIPT NARRATIONS ===

{sample_narrations}

=== SPOKEN TUTORIAL PRINCIPLES (MUST FOLLOW) ===

**1. SIMPLE INDIAN ENGLISH**
- Use simple words that translate easily into Indian languages
- ❌ AVOID: leverage, utilize, facilitate, paradigm, comprehensive, synergy
- ✅ USE: use, help, way, complete, work together
- Write for beginners who may not know English well

**2. STEP-BY-STEP LANGUAGE**
- Every action = "Do this → See this"
- ✅ GOOD: "Click the Submit button. You will see a success message."
- ❌ BAD: "Upon clicking Submit, the system facilitates form submission."

**3. CONCEPTS VIA EXAMPLES**
- Never explain without showing
- ✅ GOOD: "Let's understand with an example. Open your browser."
- ❌ BAD: "The concept of web browsing involves navigating to URLs."

**4. KEEP SLIDES LIGHT**
- 1-2 sentences per slide maximum
- If a slide has more, split or remove content

=== DRAFT SCRIPT TO ADJUST ===

{draft_script}

=== INSTRUCTIONS ===

1. Keep ALL the same slides (same titles)
2. REWRITE narrations using simple Indian English
3. Add step-by-step examples where missing
4. Keep each slide to 3-4 sentences max

Return the complete script with adjusted narrations in the same JSON format.
"""


@retry(
    retry=retry_if_exception_type((ResourceExhausted, ServiceUnavailable, InternalServerError)),
    wait=wait_exponential(multiplier=4, min=4, max=60),
    stop=stop_after_attempt(5)
)
def style_match(state: AgentState):
    """Adjusts script narration to match sample script style."""
    print("Matching style to sample script...")
    json_script = state.get('json_script')
    
    if not json_script or not json_script.get('slides'):
        print("⚠ No script to style-match")
        return {"json_script": json_script}
    
    if not SAMPLE_NARRATIONS:
        print("⚠ No sample narrations loaded - skipping style match")
        return {"json_script": json_script}

    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    
    prompt = STYLE_MATCHER_PROMPT.format(
        sample_narrations=SAMPLE_NARRATIONS,
        draft_script=json.dumps(json_script, indent=2)
    )
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "object",
                    "properties": {
                        "presentation_title": {"type": "string"},
                        "module": {"type": "string"},
                        "episode": {"type": "string"},
                        "learning_objectives": {"type": "array", "items": {"type": "string"}},
                        "duration": {"type": "string"},
                        "outline": {"type": "array", "items": {"type": "string"}},
                        "meta_tags": {"type": "array", "items": {"type": "string"}},
                        "prerequisites": {"type": "string"},
                        "slides": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "narration": {"type": "string"},
                                    "image_prompt": {"type": "string"}
                                },
                                "required": ["title", "narration"]
                            }
                        }
                    },
                    "required": ["presentation_title", "slides"]
                },
                temperature=0.5  # Lower temperature for more consistent style
            )
        )
        
        styled_script = json.loads(response.text)
        print(f"✓ Style-matched script with {len(styled_script.get('slides', []))} slides")
        
        return {"json_script": styled_script}
        
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON parsing failed in style matcher: {e}")
        return {"json_script": json_script}  # Return original on failure
    except Exception as e:
        print(f"ERROR in style matcher: {e}")
        import traceback
        traceback.print_exc()
        return {"json_script": json_script}  # Return original on failure
