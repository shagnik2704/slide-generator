"""
Structure generation node for the 4-node pipeline.
Stage 1: Parses outline and creates metadata + slide skeleton.
"""
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from models.state import AgentState, StructuredOutline

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
- presentation_title: "Spoken Tutorial on [Topic]" (no bold markers)
- module: Extract from outline or use "AI Essentials"
- episode: Number + topic (e.g., "5. 3 Cs of Prompting")
- duration: "3-4 min"
- learning_objectives: FEW SIMPLE objectives (each ≤80 chars, achievable by end of tutorial)
  - Use Bloom's verbs: Define, Explain, Identify, Apply
  - Keep SHORT: "Define what an API is." NOT "Define and explain the comprehensive role of APIs in modern software development."
- prerequisites: Extract EXACTLY from outline if mentioned (e.g., "Episode 2: Basics of Python")
- meta_tags: 8-12 relevant keywords
- outline: List ONLY content topics (not boilerplate slide names)

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

3. VAGUE → IMPROVED → COMPARE: ONLY ONCE
   - This 3-slide pattern should appear ONLY for the main demo
   - Other topics: just explain without the full comparison flow

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

=== EXAMPLE STRUCTURE FOR 4-TOPIC OUTLINE ===
1. Title (boilerplate)
2. LOs (boilerplate)
3. SysReq (boilerplate)
4. Prereq (boilerplate)
5. Topic 1: What + Analogy (content)
6. Topic 2: What + Analogy (content)
7. Real-Life Example: Everyday scenario (example)
8. Topic 3: What + Analogy (content)
9. Main Demo: Vague Example (demo)
10. Main Demo: Improved Example (demo)
11. Main Demo: Comparison (demo)
12. Summary (boilerplate)
13. Assignment (boilerplate)
14. Thank You (boilerplate)

=== USER OUTLINE ===
{outline}

Generate a LEAN structured outline with MINIMAL slides."""


def get_demo_prompt(outline: str) -> str:
    """Prompt for demo tutorials - step-by-step software walkthroughs."""
    return f"""You are creating a STEP-BY-STEP DEMO structure for a Spoken Tutorial (3-5 minutes).

=== METADATA RULES ===
- presentation_title: "Spoken Tutorial on [Action/Task]" (no bold markers)
- module: Extract from outline or use "AI Essentials"
- episode: Number + topic (e.g., "3. Creating an API Key")
- duration: "3-4 min"
- learning_objectives: FEW ACTION-based objectives (each ≤80 chars)
  - Use action verbs: Create, Set up, Configure, Navigate, Generate
  - Example: "Create an API key in Google AI Studio."
- prerequisites: Extract from outline (often includes account setup)
- meta_tags: 8-12 relevant keywords
- outline: List each MAJOR ACTION step

=== SLIDE COUNT (STRICT) ===
- TOTAL: 10-18 slides MAX
- Boilerplate: 7 fixed slides
- Action slides: 3-11 slides

=== DEMO-SPECIFIC RULES ===

1. ONE ACTION PER SLIDE
   - Each slide = ONE clear action the user performs
   - "Open browser" → "Go to URL" → "Click button" = 3 separate slides

2. NO ANALOGIES NEEDED
   - Demo tutorials don't need analogies
   - Focus on WHAT to do, not WHY conceptually

3. USE ACTION VERBS
   - Start each slide with: Open, Click, Type, Select, Navigate, Copy, Paste
   - Example notes: "Click Get API Key in the left panel"

4. INCLUDE VERIFICATION STEPS
   - After key actions, add "Verify: You should see..."
   - Helps learner confirm they did it correctly

5. DESCRIBE SCREEN LOCATIONS
   - Always specify WHERE on screen the element is located
   - Use: "top right corner", "left panel", "center of screen", "bottom of page"
   - Example: "Click Sign In in the top right corner"
   - Example: "On the left panel, click Get API Key"

6. VISUAL CUES = SCREENSHOTS
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

