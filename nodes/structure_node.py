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
    
    Input: User outline (raw text)
    Output: StructuredOutline with metadata + slide skeleton
    """
    print("🔧 Stage 1: Generating structure...")
    outline = state.get('outline', '')
    
    if not outline:
        print("⚠️ No outline provided")
        return {"structured_outline": {}}
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    structured_llm = llm.with_structured_output(StructuredOutline)
    
    prompt = f"""You are creating a LEAN STRUCTURE for a Spoken Tutorial script (3-4 minutes).

=== METADATA RULES ===
- presentation_title: "Spoken Tutorial on [Topic]" (no bold markers)
- module: Extract from outline or use "AI Essentials"
- episode: Number + topic (e.g., "5. 3 Cs of Prompting")
- duration: "3-4 min"
- learning_objectives: 3-4 SIMPLE objectives (each ≤80 chars, achievable by end of tutorial)
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

1. ONE ANALOGY PER TOPIC
   - Don't separate definition, explanation, and analogy into different slides
   - Combine: "What is X? Think of it like Y..." in ONE slide

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
- Slide 1: What + Analogy (combined)
- Slide 2: Demo/Application (only if needed)
- ONE set of Vague → Improved → Compare for main concept

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
7. Topic 3: What + Analogy (content)
8. Main Demo: Vague Example (demo)
9. Main Demo: Improved Example (demo)
10. Main Demo: Comparison (demo)
11. Topic 4: Application (content)
12. Summary (boilerplate)
13. Assignment (boilerplate)
14. Thank You (boilerplate)

=== USER OUTLINE ===
{outline}

Generate a LEAN structured outline with MINIMAL slides."""

    try:
        result = structured_llm.invoke(prompt)
        structured_outline = result.model_dump()
        
        slide_count = len(structured_outline.get('slides', []))
        print(f"✓ Stage 1 complete: {slide_count} slides in skeleton")
        
        return {"structured_outline": structured_outline}
        
    except Exception as e:
        print(f"❌ Stage 1 failed: {e}")
        import traceback
        traceback.print_exc()
        return {"structured_outline": {}}
