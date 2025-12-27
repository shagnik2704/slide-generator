"""
Optimiser node for improving script based on feedback.
Uses LangChain's ChatGoogleGenerativeAI.
Implements SURGICAL EDITS - only fixes problematic slides, not the entire script.
"""
import os
import json
from copy import deepcopy
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from src.core.state import AgentState

load_dotenv()


# Schema for individual slide fixing
class FixedSlide(BaseModel):
    """A single fixed slide."""
    index: int = Field(description="0-indexed position of this slide")
    title: Optional[str] = None
    narration: str
    image_prompt: Optional[str] = ""


class FixedSlidesList(BaseModel):
    """List of fixed slides."""
    slides: List[FixedSlide]


# Legacy schema for full-script fallback
class Slide(BaseModel):
    title: Optional[str] = None
    narration: str
    image_prompt: Optional[str] = ""


class Script(BaseModel):
    presentation_title: str = ""
    module: str = ""
    episode: str = ""
    learning_objectives: List[str] = Field(default_factory=list)
    duration: str = ""
    outline: List[str] = Field(default_factory=list)
    meta_tags: List[str] = Field(default_factory=list)
    prerequisites: str = ""
    slides: List[Slide]


def optimise_script(state: AgentState):
    """
    Optimises the script based on evaluation feedback.
    Uses SURGICAL EDITS when problematic_slides are identified.
    Falls back to full-script optimization if no specific slides identified.
    """
    json_script = state.get('json_script')
    feedback = state.get('evaluation_feedback', '')
    problematic_indices = state.get('problematic_slides', [])
    
    if not json_script or not json_script.get('slides'):
        return {"json_script": json_script or {}}

    # If specific problematic slides are identified, use surgical edits
    if problematic_indices:
        print(f"🔧 Surgical edit: Fixing slides {problematic_indices}")
        return fix_specific_slides(json_script, feedback, problematic_indices)
    else:
        print("⚠️ No specific slides identified. Falling back to full-script optimization.")
        return optimise_full_script(json_script, feedback)


def fix_specific_slides(json_script: dict, feedback: str, problematic_indices: List[int]) -> dict:
    """Fix only the problematic slides and merge back into original script."""
    
    # Extract problematic slides with their indices
    slides_to_fix = []
    for idx in problematic_indices:
        if 0 <= idx < len(json_script.get('slides', [])):
            slide = json_script['slides'][idx]
            slides_to_fix.append({
                "index": idx,
                "title": slide.get('title'),
                "narration": slide.get('narration', ''),
                "image_prompt": slide.get('image_prompt', '')
            })
    
    if not slides_to_fix:
        print("⚠️ No valid slides to fix. Returning original.")
        return {"json_script": json_script}

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    structured_llm = llm.with_structured_output(FixedSlidesList)
    
    prompt = f"""Fix ONLY these specific slides based on the evaluator's feedback.
DO NOT add new slides. DO NOT change the indices. Return the same slides, fixed.

=== EVALUATOR FEEDBACK ===
{feedback}

=== SLIDES TO FIX ===
{json.dumps(slides_to_fix, indent=2)}

=== FORMATTING RULES ===
1. Every sentence MUST be ≤ 80 characters
2. Each sentence on a new line (use \\n)
3. No filler words: "So,", "Now,", "Well,"
4. Complete sentences only (no fragments)
5. Use **bold** for technical terms

Return the slides with the same indices, but with fixed narration."""

    try:
        result = structured_llm.invoke(prompt)
        fixed_slides = result.slides
        
        # Merge fixed slides back into original script
        new_script = deepcopy(json_script)
        
        for fixed in fixed_slides:
            idx = fixed.index
            if 0 <= idx < len(new_script['slides']):
                new_script['slides'][idx]['narration'] = fixed.narration
                if fixed.title is not None:
                    new_script['slides'][idx]['title'] = fixed.title
                if fixed.image_prompt:
                    new_script['slides'][idx]['image_prompt'] = fixed.image_prompt
        
        print(f"✓ Fixed {len(fixed_slides)} slides surgically.")
        return {"json_script": new_script}
        
    except Exception as e:
        print(f"❌ Surgical edit failed: {e}. Returning original.")
        return {"json_script": json_script}


def optimise_full_script(json_script: dict, feedback: str) -> dict:
    """Fallback: Optimize the entire script (legacy behavior)."""
    print("Optimising full script...")
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    structured_llm = llm.with_structured_output(Script)
    
    prompt = f"""Fix this Spoken Tutorial script based on the evaluator's feedback.

=== EVALUATOR FEEDBACK ===
{feedback}

=== PART 1: FORMATTING FIXES ===

1. LONG SENTENCES (>80 chars):
   - Split into two shorter, complete sentences
   - Each new sentence on its own line

2. MISSING NEWLINES:
   - Put each sentence on a new line
   - Use \\n between sentences in the narration field

3. SYMBOLS (arrows, hyphens, bullets):
   - Rewrite using words: "First,", "Next,", "Then,", "Finally,"
   - Exception: • is allowed in Learning Objectives slide

4. INCOMPLETE SENTENCES:
   - Complete any fragments
   - Ensure grammatical completeness

=== PART 2: NARRATIVE IMPROVEMENTS ===

If feedback mentions choppy or poor flow, improve using these patterns:

1. BRIDGE SCENE ANTICIPATION
   - Add hooks: "What if I told you...", "Imagine..."
   
2. LINK ACTION TO REFLECTION
   - Add prompts: "Notice...", "Think about it...", "Pause for a moment..."

3. CONNECT OBSERVATION TO TIMING
   - Add timing cues: "At this point...", "See what happens when..."

4. TIE MOTIVATION TO ACTION
   - Add motivation: "This matters because...", "This could happen to you..."

5. SMOOTH TRANSITIONS
   - Connect slides: "Now that we've seen..., let's look at..."
   - Avoid abrupt jumps

6. BE SPECIFIC
   - Replace vague: "It looks real" → "The lip sync matches perfectly"
   - Replace generic: "This is dangerous" → "This can destroy someone's career"

=== SCRIPT TO FIX ===
{json.dumps(json_script, indent=2)}

Return the corrected script with all issues fixed."""

    try:
        result = structured_llm.invoke(prompt)
        optimised_script = result.model_dump()
        print("✓ Full script optimised.")
        return {"json_script": optimised_script}
        
    except Exception as e:
        print(f"❌ Full optimisation failed: {e}")
        return {"json_script": json_script}
