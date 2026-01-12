"""
Script generation node for the Spoken Tutorial Generator agent.
Uses LangChain's ChatGoogleGenerativeAI with few-shot sample scripts.
"""
import os
import json
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from src.core.state import AgentState

load_dotenv()

# Path to sample scripts
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
SAMPLE_SCRIPTS_DIR = project_root / "data" / "sample_scripts" / "json"


# Pydantic schema for structured output
class Slide(BaseModel):
    title: str
    narration: str
    image_prompt: Optional[str] = ""


class Script(BaseModel):
    presentation_title: str
    module: str
    episode: str
    learning_objectives: List[str]
    duration: str
    outline: List[str]
    meta_tags: List[str]
    prerequisites: str
    slides: List[Slide]


# def _load_sample_script(filename: str) -> dict:
#     """Load a sample script from the json folder."""
#     path = os.path.join(SAMPLE_SCRIPTS_DIR, filename)
#     try:
#         with open(path, 'r') as f:
#             return json.load(f)
#     except Exception as e:
#         print(f"⚠️ Could not load sample script {filename}: {e}")
#         return {}


# def _format_sample_for_prompt(sample: dict) -> str:
#     """Format all slides for inclusion in the prompt."""
#     if not sample:
#         return ""
    
#     slides = sample.get("slides", [])
    
#     # Extract all slides with title and narration
#     all_slides = [
#         {"title": s.get("title", ""), "narration": s.get("narration", "")}
#         for s in slides if s.get("narration")
#     ]
    
#     formatted = {
#         "title": sample.get("presentation_title", ""),
#         "slides": all_slides
#     }
    
#     return json.dumps(formatted, indent=2)


def generate_script(state: AgentState):
    """Generates a presentation script from outline using LangChain."""
    print("Generating script...")
    outline = state.get('outline')


    # Initialize LangChain model with structured output
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
    )
    
    # Use structured output for guaranteed schema
    structured_llm = llm.with_structured_output(Script)
    
    # Few-shot prompt with structure and content rules
    prompt = f"""

=== STRUCTURE (REQUIRED) ===
1. Metadata: Module, Episode, Learning Objectives, Duration (3-4 min), Outline, Meta Tags, Prerequisites
2. Use Bloom's Taxonomy: Remember → Understand → Apply → Analyze → Evaluate → Create
3. Slide Structure:
   - Title Slide (welcome)
   - Learning Objectives
   - System Requirements
   - Prerequisites
   - Content Slides (main teaching)
   - Summary
   - Assignment (one small task)
   - Thank You (EduPyramids credit)

4. VISUAL CUES FOR BOILERPLATE SLIDES:
   Set image_prompt to the slide type for these slides:
   - Title Slide → image_prompt: "Title Slide"
   - Learning Objectives → image_prompt: "Learning Objectives Slide"
   - System Requirements → image_prompt: "System Requirements Slide"
   - Prerequisites → image_prompt: "Pre-requisite Slide"
   - Summary → image_prompt: "Summary Slide"
   - Assignment → image_prompt: "Assignment Slide"
   - Thank You → image_prompt: "EduPyramids logo"

=== BOILERPLATE NARRATION FORMAT ===
Title Slide MUST be exactly:
   "Welcome to this Spoken Tutorial on ..."
   (Just one sentence, nothing more)

Learning Objectives Slide MUST use this bulleted format:
   "In this tutorial, you will learn,
   • Why prompting matters, and
   • How clear instructions improve AI's outcomes."
   
   Rules:
   - Start with "In this tutorial, you will learn,"
   - Use bullet points (•) for each objective
   - Add "and" after the second-to-last item
   - End the last item with a period
   - Keep each bullet SHORT (under 80 chars)

System Requirements Slide:
    Keep it simple, whatever you think is required for the tutorial.
   (Keep it very brief - 1-2 sentences max)

Prerequisites Slide:
   Keep it simple, whatever you think is required for the tutorial.
   (Brief, simple requirements - 1-2 sentences max)

Thank You Slide MUST be exactly:
   "This Spoken Tutorial is brought to you by
   EduPyramids Educational Services Private Limited, SINE, IIT Bombay.
   Thank you for joining."

5. OUTLINE in metadata should ONLY list CONTENT topics:
   Example (correct):
   - What is AI Automation?
   - Example: Email Sorting with AI
   - What is AI Augmentation?
   - Comparing Automation and Augmentation
   
   NOT (wrong):
   - Introduction, Learning Objectives, Prerequisites, Summary, Thank You

=== LEARNING OBJECTIVES STYLE ===
- Limit to 3-4 objectives (not 5-6)
- VARY sentence starters: "Learn...", "Understand...", "Apply...", "Identify...", "Compare..."
- Do NOT repeat "You will also learn" multiple times
- Each objective must be COMPLETE: "difference between X and Y" (not just "difference between X")
- Use action verbs from Bloom's Taxonomy

=== ANALOGIES ===
Use simple, everyday analogies:
- "Think of AI like a child - follows instructions literally."
- "It's like giving directions to a friend."


=== NARRATIVE FLOW FOR CONTENT SLIDES (follow this rhythm) ===

1. QUESTION - Start with a hook
   "Can an AI be fair if its data is not fair?"
   "What happens when we give vague instructions?"

2. EXPLAIN - 2-3 short sentences on the concept
   "AI learns patterns from the data it sees."
   "When data has bias, the AI learns that bias."

3. TRANSITION - Signal what's coming next
   "Now, let us see how this works."
   "Next, we will view a real-life example."

4. EXAMPLE - Show a concrete case
   "Old records show more male doctors."
   "We ask the AI: 'Show me a doctor.'"
   "Notice how the pattern appears."

5. REFLECT - Prompt the learner to think
   "You saw the output. Now reflect."
   "Did the AI choose this on its own?"
   "Pause the screen now."

6. APPLY - Connect to next topic or action
   "Now that we saw the data, let us check the output."
   "We now learn simple checks to fix this."

=== SLIDE DENSITY FOR CONTENT SLIDES (CRITICAL) ===
Each content slide should have MAX 4-5 sentences in narration.
If a topic needs more, SPLIT into multiple slides.
- ✅ Good: 4 short sentences per slide
- ❌ Bad: 10+ sentences crammed into one slide

=== DEMO-FOCUSED STYLE (CRITICAL) ===
Use ACTION VERBS and step-by-step instructions:
- "Open any AI tool."
- "Type this in the message box."
- "Now click Submit."
- "See the difference?"
- "Compare the two outputs."

NOT passive descriptions:
- ❌ "The AI might show different results."
- ✅ "Notice how the AI shows different results."

=== SENTENCE LENGTH - HARD LIMIT (CRITICAL) ===
EVERY sentence MUST be ≤ 80 characters. NO EXCEPTIONS.
If a sentence is too long, SPLIT it into multiple shorter sentences.
This applies to ALL slides including boilerplate slides.

Write SHORT, PUNCHY sentences (5-10 words ideal):
- ✅ "A weak prompt gets a weak answer." (36 chars)
- ✅ "The AI can't read your mind." (28 chars)
- ✅ "See the difference?" (18 chars)
- ❌ "When you explain your thoughts clearly, the AI gives better results." (69 chars - too long!)

=== WRITING STYLE ===
- Simple Indian English (easy to translate)
- Short sentences (5-10 words ideal)
- No arrows, hyphens, or symbols in narration
- EACH SENTENCE ON A NEW LINE (for TTS audio generation)
  ✅ "AI learns from data.\nThis data comes from the real world."
  ❌ "AI learns from data. This data comes from the real world."


=== BOLD TERMS (for transliteration) ===
Use **bold** for terms that should be transliterated, not translated.
IMPORTANT: Apply this ONLY in the 'narration' field.
DO NOT use bold markers in 'title', 'module', or 'episode' fields.

Terms to bold (in narration only):
- AI tools: **AI**, **ML**, **ChatGPT**, **Gemini**, **Claude**, **Python**
- Technical terms: **API**, **LLM**, **Deep Learning**, **Neural Network**, **tokens**, **prompt**
- Organizations: **EduPyramids**, **SINE**, **IIT Bombay**
- UI elements: **Enter**, **Submit**, **click**, **button**

=== YOUR OUTLINE ===
{outline}

Generate a complete script matching the examples above."""
    
    try:
        result = structured_llm.invoke(prompt)
        script_data = result.model_dump()
        print(f"✓ Generated script with {len(script_data.get('slides', []))} slides")
        
        return {"json_script": script_data}
        
    except Exception as e:
        print(f"ERROR generating script: {e}")
        import traceback
        traceback.print_exc()
        return {"json_script": {}}
