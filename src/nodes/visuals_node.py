"""
Visual generation node for the 4-node pipeline.
Stage 3: Generates image prompts based on narration context.
"""
import os
from dotenv import load_dotenv
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.core.state import AgentState
import json

load_dotenv()


# Output schema for Stage 3
class FinalSlide(BaseModel):
    """Final slide with narration and image prompt."""
    title: Optional[str] = Field(description="Slide title")
    narration: str = Field(description="Full narration text")
    image_prompt: Optional[str] = Field(description="Visual cue description")


class FinalScript(BaseModel):
    """Final script output with all fields."""
    presentation_title: str
    module: str
    episode: str
    learning_objectives: List[str]
    duration: str
    meta_tags: List[str]
    prerequisites: str
    outline: List[str]
    slides: List[FinalSlide]


def generate_visuals(state: AgentState):
    """
    Stage 3: Generate image prompts based on narration context.
    
    Input: NarrationScript (from Stage 2)
    Output: Final json_script with image_prompts
    """
    print("🎨 Stage 3: Generating visual cues...")
    narration_script = state.get('narration_script', {})
    
    if not narration_script or not narration_script.get('slides'):
        print("⚠️ No narration script provided")
        return {"json_script": {}}
    
   
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    structured_llm = llm.with_structured_output(FinalScript)
    
    messages = get_visual_messages(narration_script)

    try:
        result = structured_llm.invoke(messages)
        
        # Handle None result from LLM
        if result is None:
            print("⚠️ Stage 3: LLM returned None, using narration script with default image prompts")
            # Fallback: use narration_script and add basic image_prompts
            fallback_script = narration_script.copy()
            for slide in fallback_script.get('slides', []):
                if not slide.get('image_prompt'):
                    slide['image_prompt'] = slide.get('title', 'Content Slide')
            return {"json_script": fallback_script}
        
        json_script = result.model_dump()
        
        slide_count = len(json_script.get('slides', []))
        print(f"✓ Stage 3 complete: {slide_count} slides with visual cues")
        
        return {"json_script": json_script}
        
    except Exception as e:
        print(f"❌ Stage 3 failed: {e}")
        import traceback
        traceback.print_exc()
        # Fallback: return narration_script as json_script with basic prompts
        fallback_script = narration_script.copy()
        for slide in fallback_script.get('slides', []):
            if not slide.get('image_prompt'):
                slide['image_prompt'] = slide.get('title', 'Content Slide')
        return {"json_script": fallback_script}


def get_visual_messages(narration_script: dict) -> list:
    """Messages for adding visual cues to narration script."""
    system_content = """You are adding VISUAL CUES (image_prompt) to a Spoken Tutorial script.

=== VISUAL CUE RULES ===

BOILERPLATE SLIDES (use exact strings):
- Title Slide → image_prompt: "Title Slide"
- Learning Objectives → image_prompt: "Learning Objectives Slide"
- System Requirements → image_prompt: "System Requirements Slide"
- Pre-requisite Slide → image_prompt: "Pre-requisite Slide \n https://EduPyramids.org"
- Summary Slide → image_prompt: "Summary Slide"
- Assignment Slide → image_prompt: "Assignment Slide"
- Thank You Slide → image_prompt: "EduPyramids logo"

SECTION HEADERS:
- When introducing a new topic → "Section Header: [Topic Name]"
- Example: "Section Header: Clarity"

DEMO SLIDES:
- User typing a prompt → "Screen close-up: user typing '[first few words of prompt]...'"
- AI generating response → "AI generating response on screen"
- Opening a tool → "Browser showing ChatGPT/Gemini interface"
- Clicking submit → "User clicking Submit button"

COMPARISON SLIDES:
- Showing vague vs improved → "Side-by-side: vague prompt output vs improved prompt output"
- Before/after comparison → "Three outputs shown side by side"

CONCEPT EXPLANATION:
- Explaining a concept → "Person at laptop, [relevant visual]"
- Showing frustration → "Person scratching head, confused at screen"
- Showing success → "Person at laptop, smiling at improved output"
- Abstract concept → "Illustration showing [concept] with simple icons"

REACTION/REFLECTION:
- Asking to think → "Person thinking with thought bubble"
- Emphasizing a point → "Close-up of screen showing key element"

=== RULES ===
1. Every slide MUST have an image_prompt (never null for content slides)
2. Match the visual to the narration content
3. Keep descriptions concise but specific
4. For demo slides, reference what's being typed/shown

Add image_prompt to EVERY slide. Keep title and narration unchanged."""

    human_content = f"""Add visual cues (image_prompt) to this narration script:

{json.dumps(narration_script, indent=2)}"""

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content)
    ]
