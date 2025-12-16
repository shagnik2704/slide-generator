"""
Narration expansion node for the 4-node pipeline.
Stage 2: Expands slide skeleton into full narration.
"""
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
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
    
    # Select prompt based on tutorial type
    if tutorial_type == "demo":
        prompt = get_demo_narration_prompt(structured_outline)
    else:
        prompt = get_conceptual_narration_prompt(structured_outline)
    
    try:
        result = structured_llm.invoke(prompt)
        narration_script = result.model_dump()
        
        slide_count = len(narration_script.get('slides', []))
        print(f"✓ Stage 2 complete: {slide_count} slides with narration ({tutorial_type} mode)")
        
        return {"narration_script": narration_script}
        
    except Exception as e:
        print(f"❌ Stage 2 failed: {e}")
        import traceback
        traceback.print_exc()
        return {"narration_script": {}}


def get_conceptual_narration_prompt(structured_outline: dict) -> str:
    """Prompt for conceptual tutorials - flowing narrative with analogies."""
    return f"""You are expanding a slide skeleton into FULL NARRATION for a Spoken Tutorial.

=== INPUT: STRUCTURED OUTLINE ===
{json.dumps(structured_outline, indent=2)}

=== WRITING STYLE ===
- Write like you're SPEAKING to a learner, not reading bullet points
- Natural, conversational flow - sentences should connect smoothly
- Simple Indian English (easy to translate)
- Each sentence on a NEW LINE (use \\n) for TTS
- Sentences should be ≤ 80 characters

=== CONCISENESS RULES (IMPORTANT) ===

1. CUT FILLER PHRASES
   Remove these unnecessary starters:
   - "So," / "Now," / "Well,"
   - "So, what exactly is..." → "What is..."
   - "Now, let's look at..." → Just start the content

2. REMOVE REDUNDANCY (CRITICAL)
   - Don't say the same thing twice: "X is for Y. It does Y." → Just say "X is for Y."
   - Avoid repeating a term 3+ times in one slide
   - "The API delivers to the model. The model processes..." → "The model receives and processes..."

3. ANALOGY REQUIRED FOR EVERY CONTENT TOPIC
   - Every content slide MUST include a relatable analogy
   - Pattern: "Think of X like Y..." or "Imagine X as Y..."
   - Use everyday scenarios: restaurant, library, traffic, school, keys

4. USE ACTIVE VOICE
   - "The request is sent to the API" → "You send a request to the API"

=== BOLD TERMS (for transliteration) ===
Use **bold** for technical terms: **AI**, **API**, **prompt**, **ChatGPT**, etc.

=== BOILERPLATE NARRATION ===

Title Slide: "Welcome to this Spoken Tutorial on [presentation_title]."

Learning Objectives Slide:
"In this tutorial, you will learn to,\\n• [objective 1].\\n• [objective 2].\\n• [objective 3]."

System Requirements Slide: "Here I am using a browser on a computer or mobile."

Pre-requisite Slide: "To follow this tutorial, you should have [concept knowledge].\\nPlease refer to our website for more details."

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

EXAMPLE NARRATION:
"Let's see how this works in real life.
Open any grocery app on your phone.
Tap the search bar at the top.
Type 'tomato' and press search.
Behind the scenes, the app sends a request to the **API**.
The **API** searches for all matching products.
The server sends back a list of results.
You now see all tomato products on your screen.
This is an **API** in action!"

USE EVERYDAY APPS: grocery apps, food delivery, ride sharing, weather apps, etc.

=== NARRATIVE FLOW FOR CONTENT SLIDES ===

1. BRIDGE SCENE ANTICIPATION - Build curiosity before explaining
2. LINK ACTION TO REFLECTION - Prompt learner to think
3. SMOOTH TRANSITIONS - Connect slides naturally
4. BE SPECIFIC - Avoid vague statements

Expand EVERY slide's 'notes' into full conversational 'narration' with analogies."""


def get_demo_narration_prompt(structured_outline: dict) -> str:
    """Prompt for demo tutorials - action-focused step-by-step instructions."""
    return f"""You are expanding a slide skeleton into STEP-BY-STEP NARRATION for a Demo Tutorial.

=== INPUT: STRUCTURED OUTLINE ===
{json.dumps(structured_outline, indent=2)}

=== DEMO WRITING STYLE ===
- Write like you're GUIDING someone through a software task
- Short, imperative sentences - one action at a time
- Simple Indian English (easy to translate)
- Each sentence on a NEW LINE (use \\n) for TTS
- Sentences should be ≤ 80 characters

=== SHARED QUALITY RULES (APPLY TO ALL TUTORIALS) ===

1. CUT FILLER PHRASES
   Remove these unnecessary starters:
   - "So," / "Now," / "Well," / "Alright,"
   - "Let's go ahead and..." → Just start the action
   - "What we need to do is..." → Just state the action

2. REMOVE REDUNDANCY (CRITICAL)
   - Don't say the same thing twice
   - Avoid repeating a term 3+ times in one slide
   - "Click the button. The button will..." → "Click the button. It will..."

3. USE ACTIVE VOICE
   - "The button is clicked" → "Click the button"
   - "The key will be generated" → "A new key appears"

=== DEMO-SPECIFIC RULES ===

1. USE ACTION VERBS (START EACH SENTENCE WITH)
   - Open, Click, Type, Select, Navigate, Copy, Paste, Scroll
   - Example: "Click on Get API Key."
   - Example: "Type your project name in the text box."

2. NO ANALOGIES NEEDED
   - Demo tutorials focus on DOING, not explaining concepts
   - Just tell them what to do, not why it works

3. ONE ACTION = ONE SENTENCE
   - "Open the browser. Go to aistudio.google.com."
   - NOT: "Open the browser and navigate to the AI Studio website where you can create API keys."

4. INCLUDE VERIFICATION CUES
   - After key actions, tell them what they should see:
   - "You will see a list of your API keys."
   - "The key appears on the screen."

5. BE SCREEN-CENTRIC WITH EXPLICIT LOCATIONS (CRITICAL)
   Always describe WHERE elements are located on screen:
   
   POSITIONS TO USE:
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

Title Slide: "Welcome to this Spoken Tutorial on [presentation_title]."

Learning Objectives Slide:
"In this tutorial, you will learn to,\\n• [action objective 1].\\n• [action objective 2]."

System Requirements Slide: "Here I am using a browser on a computer.\\nYou will need [specific requirements]."

Pre-requisite Slide: "To follow this tutorial, you should have [concept knowledge].\\nPlease refer to our website for more details."

Summary Slide: "Let us summarize what we did.\\n[recap of key actions]"

Assignment Slide: "Now as an assignment,\\n[practice task].\\nCompare the results."

Thank You Slide: "This Spoken Tutorial is brought to you by\\n**EduPyramids Educational Services Private Limited**, **SINE**, **IIT Bombay**.\\nThank you for joining."

Expand EVERY slide's 'notes' into clear action-focused narration."""

