"""
Content slides generation node.
Generates the main learning content slides based on outline topics.

Adapts generation style based on tutorial_type:
- "conceptual": Explanations with analogies, definitions, examples
- "demo": Step-by-step software walkthrough with actions

Input: ScriptMetadata from metadata_node (outline, tutorial_type)
Output: List of content slides with narration + image_prompt
"""
import os
from dotenv import load_dotenv
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.core.state import AgentState
import json

load_dotenv()


# === OUTPUT SCHEMA ===

class ContentSlide(BaseModel):
    """A single content slide."""
    title: Optional[str] = Field(default="", description="Slide title (optional)")
    narration: str = Field(description="Full narration text, sentences separated by \\n")
    image_prompt: Optional[str] = Field(default="", description="Visual cue for image generation")


class ContentSlides(BaseModel):
    """All content slides for the tutorial."""
    slides: List[ContentSlide] = Field(description="List of content slides")


# === MAIN NODE FUNCTION ===

def generate_content(state: AgentState) -> dict:
    """
    Generates content slides based on outline topics.
    
    Uses different prompts for conceptual vs demo tutorials.
    """
    print("📚 Generating content slides...")
    
    metadata = state.get('metadata')
    tutorial_type = state.get('tutorial_type', 'conceptual')
    
    if not metadata:
        print("⚠️ No metadata provided for content generation")
        return {"content_slides": None}
    
    outline = metadata.get('outline', [])
    if not outline:
        print("⚠️ No outline topics provided")
        return {"content_slides": None}
    
    # Initialize LLM with structured output
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    llm_openai = ChatOpenAI(model="gpt-5.2")
    structured_llm = llm.with_structured_output(ContentSlides)
    structured_llm_openai = llm_openai.with_structured_output(ContentSlides)
    
    # Select prompt based on tutorial type
    if tutorial_type == "demo":
        messages = get_demo_content_messages(metadata)
    else:
        messages = get_conceptual_content_messages(metadata)
    
    try:
        result = structured_llm_openai.invoke(messages)
        
        if result is None:
            print("⚠️ LLM returned None for content slides")
            return {"content_slides": None}
        
        content_list = [slide.model_dump() for slide in result.slides]
        
        print(f"✓ Generated {len(content_list)} content slides ({tutorial_type} mode)")
        
        return {"content_slides": content_list}
        
    except Exception as e:
        print(f"Content generation failed: {e}")
        return {"content_slides": None}


# === CONCEPTUAL TUTORIAL PROMPT ===

def get_conceptual_content_messages(metadata: dict) -> list:
    """Messages for conceptual tutorial content generation."""
    
    system_content = CONCEPTUAL_PROMPT
    human_content = f"""Generate content slides for this tutorial:

METADATA:
{json.dumps(metadata, indent=2)}

Create slides that explain each topic in the outline with analogies and examples."""

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content)
    ]


# === DEMO TUTORIAL PROMPT ===

def get_demo_content_messages(metadata: dict) -> list:
    """Messages for demo tutorial content generation."""
    
    system_content = DEMO_PROMPT
    human_content = f"""Generate content slides for this DEMO tutorial:

METADATA:
{json.dumps(metadata, indent=2)}

Create step-by-step action slides for each topic in the outline."""

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content)
    ]

DEMO_PROMPT = """You are an instructional expert creating CONTENT SLIDES for a demo Spoken Tutorial.

=== NARRATION RULES (CRITICAL) ===
1. Each sentence on a NEW LINE (use \\n between sentences)
2. Sentences MUST be ≤ 80 characters
3. Use **bold** for UI elements, buttons, menu items
4. Simple, conversational Indian English
5. Write step-by-step action instructions

=== DEMO TUTORIAL STYLE ===

1. ONE ACTION PER SLIDE
   - Each slide = ONE clear action the user performs
   - "Open browser" → "Go to URL" → "Click button" = 3 separate slides

2. USE ACTION VERBS
   - Start each instruction with: Open, Click, Type, Select, Navigate, Copy, Paste
   - Example: "Click **Get API Key** in the left panel."

3. DESCRIBE SCREEN LOCATIONS (CRITICAL)
   - Always specify WHERE on screen the element is
   - "In the **top right corner**, click **Sign In**."
   - "On the **left panel**, click **Settings**."
   - "At the **bottom of the page**, click **Submit**."

4. VERIFICATION CUES
   - After key actions, tell what to expect:
   - "You will see a list of your API keys."
   - "The key appears on the screen."

=== SLIDE STRUCTURE ===

For each step in the process:
- **Action Slide**: One action with clear location
- **Verification**: What the user should see (can be part of same slide)

=== IMAGE PROMPTS ===

For demo content, use:
- "Screen close-up: user typing '[text]...'"
- "Screen showing [software] interface with [element] highlighted"
- "Browser showing [website/tool] interface"
- "User clicking [button] in [location]"

Generate content slides based on the outline topics."""


CONCEPTUAL_PROMPT = """You are a Spoken Tutorial script writer.

=== WRITING STYLE ===
- Write like you're SPEAKING to a learner, not reading bullet points
- Natural, conversational flow - sentences should connect smoothly
- Simple Indian English (easy to translate)
- Each sentence on a NEW LINE (use \\n) for TTS
- Sentences should be ≤ 80 characters

=== CONCISENESS RULES (IMPORTANT) ===

1. REMOVE REDUNDANCY (CRITICAL)
   - Don't say the same thing twice: "X is for Y. It does Y." → Just say "X is for Y."
   - Avoid repeating a term 3+ times in one slide
   - Example:"The API delivers to the model. The model processes..." → "The model receives and processes..."

2. ANALOGY REQUIRED FOR EVERY CONTENT TOPIC
   - Every content slide MUST include a relatable analogy
   - Pattern: "Think of X like Y..." or "Imagine X as Y..."
   - Use everyday scenarios: restaurant, library, traffic, school, keys

3. USE ACTIVE VOICE
   - "The request is sent to the API" → "You send a request to the API"

=== BOLD TERMS (for transliteration) ===
Use **bold** for technical terms: **AI**, **API**, **prompt**, **ChatGPT**, etc.


1. BRIDGE SCENE ANTICIPATION - Build curiosity before explaining
2. LINK ACTION TO REFLECTION - Prompt learner to think
3. SMOOTH TRANSITIONS - Connect slides naturally
4. BE SPECIFIC - Avoid vague statements
"""