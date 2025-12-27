"""
Narration expansion node for the 4-node pipeline.
Stage 2: Expands slide skeleton into full narration.
"""
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.core.state import AgentState, NarrationScript
import json

load_dotenv()


def expand_narration(state: AgentState):
    """
    Stage 2: Expand skeleton into full narration per slide.
    Uses different styles for conceptual vs demo tutorials.
    """
    print("📝 Stage 2: Expanding narration...")
    structured_outline = state.get('structured_outline', {})
    tutorial_type = state.get('tutorial_type', 'conceptual')
    
    if not structured_outline or not structured_outline.get('slides'):
        print("⚠️ No structured outline provided")
        return {"narration_script": {}}
        
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    structured_llm = llm.with_structured_output(NarrationScript)
    
    # Select messages based on tutorial type
    if tutorial_type == "demo":
        messages = get_demo_narration_messages(structured_outline)
    else:
        messages = get_conceptual_narration_messages(structured_outline)
    
    try:
        result = structured_llm.invoke(messages)
        narration_script = result.model_dump()
        
        # Calculate duration based on word count (avg 135 wpm)
        total_words = 0
        for slide in narration_script.get('slides', []):
            narration_text = slide.get('narration', '')
            total_words += len(narration_text.split())
            
        minutes = total_words / 135
        min_duration = int(minutes)
        max_duration = int(minutes) + 1
        
        # Ensure at least "1-2 min"
        if min_duration < 1:
            min_duration = 1
            max_duration = 2
            
        calculated_duration = f"{min_duration}-{max_duration} min"
        narration_script['duration'] = calculated_duration
        
        slide_count = len(narration_script.get('slides', []))
        print(f"✓ Stage 2 complete: {slide_count} slides with narration ({tutorial_type} mode)")
        print(f"⏱️  Calculated Duration: {calculated_duration} ({total_words} words)")
        
        return {"narration_script": narration_script}
        
    except Exception as e:
        print(f"❌ Stage 2 failed: {e}")
        import traceback
        traceback.print_exc()
        return {"narration_script": {}}


def get_conceptual_narration_messages(structured_outline: dict) -> list:
    """Messages for conceptual tutorials - flowing narrative with analogies."""
    system_content = """You are a Spoken Tutorial script writer expanding slide skeletons into FULL NARRATION.

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

=== BOILERPLATE NARRATION ===

IMPORTANT: Narration is ONLY what is spoken aloud.
Do NOT include visual descriptions like "The title appears on screen" or "You will see X".
Those belong in image_prompt, not narration.

Title Slide (ONE sentence only):
"Welcome to the Spoken Tutorial on [topic from title]."

Learning Objectives Slide:
"In this tutorial, you will learn to,\\n• [objective 1].\\n• [objective 2].\\n• [objective 3]."

System Requirements Slide:
"Here I am using [device/browser].\\n
For this tutorial, you need [item 1], [item 2], and [item 3]."
(Combine all requirements into ONE flowing sentence - avoid repeating 'You will need')

Pre-requisite Slide:
"To follow this tutorial, you should have [concept knowledge].\\n
For pre-requisite tutorials, please visit this website."
(Keep it brief - one sentence for requirements, one for the website.)

Summary Slide: "Let us summarize what we learned.\\n[brief recap]"

Assignment Slide: "Now as an assignment,\\n[simple practice task].\\nCompare the results."

Thank You Slide: "This Spoken Tutorial is brought to you by\\n**EduPyramids Educational Services Private Limited**, **SINE**, **IIT Bombay**.\\nThank you for joining."

=== REAL-LIFE EXAMPLE SLIDE (REQUIRED) ===

Include ONE slide showing an EVERYDAY SCENARIO that demonstrates the concept:

PATTERN:
1. Start with a relatable action: "Open any grocery app on your phone."
2. Show user interaction: "Tap the search bar. Type 'tomato'."
3. Explain what happens behind the scenes: "The app sends a request to the **API**."
4. Describe the process: "The **API** searches for matching products."
5. Show the result: "You see the tomato products on your screen."
6. Optionally show edge case: "If no products are found, the **API** returns an empty list."

USE EVERYDAY APPS: grocery apps, food delivery, ride sharing, weather apps, etc.

=== NARRATIVE FLOW FOR CONTENT SLIDES ===

1. BRIDGE SCENE ANTICIPATION - Build curiosity before explaining
2. LINK ACTION TO REFLECTION - Prompt learner to think
3. SMOOTH TRANSITIONS - Connect slides naturally
4. BE SPECIFIC - Avoid vague statements

Expand EVERY slide's 'notes' into full conversational 'narration' with analogies."""

    human_content = f"""Expand the following structured outline into full narration:

{json.dumps(structured_outline, indent=2)}"""

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content)
    ]


def get_demo_narration_messages(structured_outline: dict) -> list:
    """Messages for demo tutorials - action-focused step-by-step instructions."""
    system_content = """You are a Spoken Tutorial script writer expanding slide skeletons into STEP-BY-STEP NARRATION for a Demo Tutorial.

=== DEMO WRITING STYLE ===
- Write like you're GUIDING someone through a task
- Short, imperative sentences - one action at a time
- Simple Indian English (easy to translate)
- Each sentence on a NEW LINE (use \\n) for TTS
- Sentences should be ≤ 80 characters

=== SHARED QUALITY RULES (APPLY TO ALL TUTORIALS) ===

1. CUT FILLER PHRASES

2. REMOVE REDUNDANCY (CRITICAL)
   - Don't say the same thing twice
   - Avoid repeating a term 3+ times in one slide
   - "Click the button. The button will..." → "Click the button. It will..."

3. USE ACTIVE VOICE

=== DEMO-SPECIFIC RULES ===

1. ONE ACTION = ONE SENTENCE
   - "Open the browser. Go to aistudio.google.com."
   - NOT: "Open the browser and navigate to the AI Studio website where you can create API keys."

4. INCLUDE VERIFICATION CUES
   - After key actions, tell them what they should see:
   - "You will see a list of your API keys."
   - "The key appears on the screen."

5. BE SCREEN-CENTRIC WITH EXPLICIT LOCATIONS (CRITICAL)
   Always describe WHERE elements are located on screen:
   
   EXAMPLE POSITIONS TO USE:
   - "In the **top right corner**..."
   - "On the **left panel**..." / "In the **left sidebar**..."
   - "At the **bottom of the page**..."
   - "In the **center of the screen**..."
   - "Below the **search bar**..."
   - "Next to the **profile icon**..."
   
   EXAMPLES:
   - "In the **top right corner**, click **Sign In**."
   - "On the **left panel**, click **Get API Key**."
   - "At the **bottom of the dialog box**, click **Create**."
   - "In the **text box** at the center, type your project name."
   
   BAD (no location):
   - "Click Sign In." (WHERE is it?)
   - "Click Settings." (WHERE on the screen?)
   
   GOOD (with location):
   - "In the **top right corner**, click **Sign In**."
   - "On the **left panel**, click **Settings**."

=== BOLD TERMS ===
Use **bold** for:
- Button names: **Create API Key**, **Submit**, **Copy**
- Menu items: **Settings**, **API Keys**
- Important UI elements: **left panel**, **text box**

=== BOILERPLATE NARRATION ===

IMPORTANT: Narration is ONLY what is spoken aloud.
Do NOT include visual descriptions like "The title appears on screen" or "You will see X".
Those belong in image_prompt, not narration.

Title Slide (ONE sentence only):
"Welcome to the Spoken Tutorial on [topic from title]."

Learning Objectives Slide:
"In this tutorial, you will learn to,\\n• [action objective 1].\\n• [action objective 2]."

System Requirements Slide:
"Here I am using [device/browser].\\n
Optional:For this tutorial, you need [item 1], [item 2], and [item 3]."
(Combine all requirements into ONE flowing sentence - avoid repeating 'You will need')

Pre-requisite Slide:
"To follow this tutorial, you should have [concept knowledge].\\n
For pre-requisite tutorials, please visit this website."

Summary Slide: "Let us summarize what we have learnt.\\n[recap of key actions]"

Assignment Slide: "Now as an assignment,\\n[practice task].\\nCompare the results."

Thank You Slide: "This Spoken Tutorial is brought to you by\\n**EduPyramids Educational Services Private Limited**, **SINE**, **IIT Bombay**.\\nThank you for joining."

Expand EVERY slide's 'notes' into clear action-focused narration."""

    human_content = f"""Expand the following structured outline into full narration:

{json.dumps(structured_outline, indent=2)}"""

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content)
    ]

