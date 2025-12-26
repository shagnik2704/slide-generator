"""
Structure generation node for the 4-node pipeline.
Stage 1: Parses outline and creates metadata + slide skeleton.
"""
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from src.core.state import AgentState, StructuredOutline

load_dotenv()


def generate_structure(state: AgentState):
    """
    Stage 1: Generate structured outline with metadata and slide skeleton.
    Uses different prompts for conceptual vs demo tutorials.
    """
    print("🔧 Stage 1: Generating structure...")
    outline = state.get('outline', '')
    tutorial_type = state.get('tutorial_type', 'conceptual')
    
    if not outline:
        print("⚠️ No outline provided")
        return {"structured_outline": {}}
    
   #  llm = ChatOpenAI(model="gpt-5-mini")
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    structured_llm = llm.with_structured_output(StructuredOutline)
    
    # Select prompt based on tutorial type
    if tutorial_type == "demo":
        prompt = get_demo_prompt(outline)
    else:
        prompt = get_conceptual_prompt(outline)
    
    try:
        result = structured_llm.invoke(prompt)
        structured_outline = result.model_dump()
        
        slide_count = len(structured_outline.get('slides', []))
        print(f"✓ Stage 1 complete: {slide_count} slides in skeleton ({tutorial_type} mode)")
        
        return {"structured_outline": structured_outline}
        
    except Exception as e:
        print(f"❌ Stage 1 failed: {e}")
        import traceback
        traceback.print_exc()
        return {"structured_outline": {}}


def get_conceptual_prompt(outline: str) -> str:
    """Prompt for conceptual tutorials - explains concepts with analogies."""
    return f"""You are creating a LEAN STRUCTURE for a Spoken Tutorial script (3-4 minutes).

=== METADATA RULES ===
- presentation_title: "Spoken Tutorial on [Topic]" (no bold markers).
- module: Extract from outline.
- episode: Number + topic (e.g., "5. 3 Cs of Prompting")
- duration: "3-4 min"
- learning_objectives: FEW SIMPLE objectives (each ≤80 chars, achievable by end of tutorial)
  - Use Bloom's verbs: Define, Explain, Identify, Apply
  - Keep SHORT: "Define what an API is." NOT "Define and explain the comprehensive role of APIs in modern software development."
- prerequisites: Based on the concept,add one line at the end "Please refer to our website for more detail"
- meta_tags: 8-12 relevant keywords
- outline: Extract ONLY topics from the user's outline (DO NOT invent new topics)

=== STRICT TOPIC RULE (CRITICAL) ===
- Use ONLY topics provided in the user's outline
- DO NOT add, invent, or infer new topics not explicitly mentioned
- If the user lists 3 topics, create slides for those 3 topics only
- The Vague → Improved → Compare demo should use the user's existing topics, not create new ones

=== SLIDE COUNT (STRICT) ===
- TOTAL: 1-20 slides MAX
- Boilerplate: 7 fixed slides
- Content: 3-13 slides ONLY

=== LEAN CONTENT RULES ===

1. ANALOGY REQUIRED FOR EVERY TOPIC
   - EVERY content topic MUST include a relatable analogy
   - Combine definition + analogy in ONE slide: "What is X? Think of it like Y..."
   - Use everyday analogies: restaurant, library, traffic, school, etc.

2. NO SEPARATE SECTION HEADERS
   - Blend topic intro into the first content slide
   - Skip slides that just say "Now let's look at..."

3. VAGUE → IMPROVED → COMPARE: OPTIONAL
   - Only include this pattern if the topic naturally involves comparison (e.g., prompting, writing, communication)
   - Skip for purely definitional topics (e.g., "What is an API?")
   - If included, use ONE set only for the main comparison point

4. SKIP BENEFIT/DETAIL SLIDES
   - Don't create separate slides for "Why X matters" or "Benefits of X"
   - Integrate into the main explanation

=== SLIDE STRUCTURE ===

BOILERPLATE (slide_type="boilerplate"):
1. Title Slide
2. Learning Objectives Slide
3. System Requirements Slide
4. Pre-requisite Slide

CONTENT (3-13 slides total):
- Each topic = 1-2 slides MAX
- Slide 1: What + Analogy (REQUIRED - every concept must have an analogy)
- Slide 2: Demo/Application (only if needed)
- ONE set of Vague → Improved → Compare for main concept

REAL-LIFE EXAMPLE (slide_type="example") - REQUIRED:
- Include ONE "Real-Life Example" slide showing an everyday scenario
- Connect the concept to something the learner uses daily
- Show BOTH user action AND what happens behind the scenes
- Example pattern:
  "Open any grocery app on your phone.
   Tap the search bar and type 'tomato'.
   The app sends a request to the API.
   The API searches for matching products.
   The server sends back a list of results.
   You see the tomato products on your screen."

BOILERPLATE (ending):
- Summary Slide
- Assignment Slide
- Thank You Slide

=== EXAMPLE STRUCTURE FOR 3-TOPIC OUTLINE ===
1. Title (boilerplate)
2. LOs (boilerplate)
3. SysReq (boilerplate)
4. Prereq (boilerplate)
5. Topic 1: What + Analogy (content)
6. Topic 2: What + Analogy (content)
7. Real-Life Example: Everyday scenario (example)
8. Topic 3: What + Analogy (content)
9. Summary (boilerplate)
10. Assignment (boilerplate)
11. Thank You (boilerplate)

NOTE: If topic involves comparison (prompting, writing), add:
- Vague Example (demo)
- Improved Example (demo)
- Comparison (demo)

=== USER OUTLINE ===
{outline}

Generate a LEAN structured outline with MINIMAL slides."""


def get_demo_prompt(outline: str) -> str:
    """Prompt for demo tutorials - step-by-step software walkthroughs."""
    return f"""You are creating a STEP-BY-STEP DEMO structure for a Spoken Tutorial.

=== METADATA RULES ===
- presentation_title: "Spoken Tutorial on [Action/Task]" (no bold markers)
- module: Extract from outline
- episode: Number + topic (e.g., "3. Creating an API Key")
- duration: "3-4 min"
- learning_objectives: FEW ACTION-based objectives (each ≤80 chars)
  - Use action verbs for example: Create, Set up, Configure, Navigate, Generate
  - Example: "Create an API key in Google AI Studio."
- prerequisites: Mention required concept knowledge (not specific tutorial names). Add at the end: "For pre-requisite tutorials,please visit this website."
- meta_tags: 8-12 relevant keywords

=== SLIDE COUNT (STRICT) ===
- TOTAL: 10-18 slides MAX
- Boilerplate: 7 fixed slides
- Action slides: 3-11 slides

=== DEMO-SPECIFIC RULES ===

1. ONE ACTION PER SLIDE
   - Each slide = ONE clear action the user performs
   - "Open browser" → "Go to URL" → "Click button" = 3 separate slides

2. USE ACTION VERBS
   - Start each slide with: Open, Click, Type, Select, Navigate, Copy, Paste
   - Example notes: "Click Get API Key in the left panel"

3. DESCRIBE SCREEN LOCATIONS
   - Always specify WHERE on screen the element is located
   - Examples: "top right corner", "left panel", "center of screen", "bottom of page"
   - Example: "Click Sign In in the top right corner"
   - Example: "On the left panel, click Get API Key"

4. VISUAL CUES = SCREENSHOTS
   - slide_type should be "demo" for action slides
   - Image prompts should describe what the screen shows

=== SLIDE STRUCTURE ===

BOILERPLATE (slide_type="boilerplate"):
1. Title Slide
2. Learning Objectives Slide
3. System Requirements Slide (browser, account needed)
4. Pre-requisite Slide

ACTION SLIDES (slide_type="demo"):
- Each action = 1 slide
- Format: "[Action verb] [target]"
- Examples:
  - "Open AI Studio website"
  - "Sign in with Google account"
  - "Click Get API Key"
  - "Select Create API Key"
  - "Copy the generated key"
  - "Store key securely"

BOILERPLATE (ending):
- Summary Slide
- Assignment Slide
- Thank You Slide

=== EXAMPLE DEMO STRUCTURE ===
1. Title (boilerplate)
2. LOs (boilerplate)
3. SysReq (boilerplate) - "Browser, Google account"
4. Prereq (boilerplate) - "A Google account"
5. Open AI Studio (demo)
6. Sign In (demo)
7. Navigate to API Keys (demo)
8. Create New Key (demo)
9. Copy API Key (demo)
10. Verify Key Works (demo)
11. Summary (boilerplate)
12. Assignment (boilerplate)
13. Thank You (boilerplate)

=== USER OUTLINE ===
{outline}

Generate a clear STEP-BY-STEP demo structure."""

