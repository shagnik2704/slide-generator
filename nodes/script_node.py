"""
Script generation node for the slide generator agent.
Contains the main script generation logic with comprehensive prompts.
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

@retry(
    retry=retry_if_exception_type((ResourceExhausted, ServiceUnavailable, InternalServerError)),
    wait=wait_exponential(multiplier=4, min=4, max=60),
    stop=stop_after_attempt(5)
)
def generate_script(state: AgentState):
    """Generates a presentation script using Gemini 2.5 Flash."""
    print("Generating script...")
    outline = state.get('outline')

    # Use raw Google GenAI client instead of LangChain to avoid hanging issues
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    
    # Read business requirements

    prompt = f"""
    You are an expert Spoken Tutorial script writer following IIT Bombay's FOSSEE / EduPyramids standards.
    
    Generate a complete PRACTICAL DEMONSTRATION tutorial script based on the outline: "{outline}".
    
    === TUTORIAL STYLE: PRACTICAL DEMONSTRATION ===
    
    This is a HANDS-ON, FOLLOW-ALONG tutorial where the learner:
    - Opens actual tools/software
    - Types actual examples
    - Sees real outputs
    - Compares results progressively
    
    NOT a conceptual explanation with analogies.
    
    === CRITICAL: DISTILL AND FLOW ===
    
    **DO NOT REPLICATE THE OUTLINE:**
    - The outline is comprehensive and DENSE - it's a reference, NOT a script
    - Your script must be LIGHTER and more CONVERSATIONAL
    - Focus on ONE clear demonstration that builds progressively
    - Goal: 3-4 minute spoken tutorial (approximately 500 words)
    
    **CONVERSATIONAL TEACHING:**
    - Sound like a teacher DEMONSTRATING live, not lecturing
    - Use "you" and "we" to create connection
    - Use "Let's...", "Now...", "Here's what happens...", "See the difference?"
    - Invite learners to follow along: "Type this...", "Notice that..."
    
    
    === SCREEN RECORDING VISUAL CUES (CRITICAL) ===
    
    **Keep visual cues CONCISE but SPECIFIC:**
    
    GOOD Examples (concise and clear):
    - "Screen recording showing browser with ChatGPT"
    - "Close-up: user typing 'Write about electric cars'"
    - "Side-by-side: vague output vs improved output"
    - "Three outputs in comparison"
    - "Person at laptop with thought bubble"
    - "Icons: 'task', 'topic', 'instructions'"
    
    BAD Examples (too vague OR too long):
    - ❌ "Screenshot" (too vague)
    - ❌ "Screen recording showing browser window with different AI tools including ChatGPT, Gemini, Claude and other options" (too descriptive)
    
    **RULE: Keep visual cues under 60 characters when possible**
    
    === PROGRESSIVE DEMONSTRATION PATTERN (CRITICAL) ===
    
    **Build ONE example progressively across 4-6 slides:**
    
    1. **Show the problem/vague approach**
       - Visual: "person typing vague prompt"
       - Narration: "For example, consider this prompt: 'Write about electric cars'"
       - Show the weak output
    
    2. **First improvement**
       - Visual: "User typing improved prompt with [specific element added]"
       - Narration: "Now, let's improve it by adding [element]"
       - Show the better output
    
    3. **Second improvement** (if applicable)
       - Visual: "User adding [another element]"
       - Narration: "Adding [element] makes the response more tailored"
       - Show even better output
    
    4. **Final comparison**
       - Visual: "Side-by-side: all outputs in comparison"
       - Narration: "Compare all three outputs now. See the difference?"
    
    === LANGUAGE REQUIREMENTS (CRITICAL) ===
    
    **SIMPLE INDIAN ENGLISH:**
    • Use common, everyday words easy to translate to Hindi, Tamil, Telugu
    • AVOID: Complex vocabulary, idioms, Western-centric examples
    • USE: Simple sentence structure, universal examples, clear instructions
    
    === IIT BOMBAY FOSSEE / EDUPYRAMIDS STANDARDS ===
    
    **METADATA (REQUIRED)**:
    - Module: Descriptive module name
    - Episode: Episode number and title
    - **Learning Objectives: 2-3 SIMPLE, ACHIEVABLE objectives**
      * Realistic for 3-4 minute tutorial
      * Use Bloom's verbs: "define", "explain", "compare", "apply", "create"
      * Example: "Apply the 3 Cs to write clear prompts" NOT "Master prompting"
    - Duration: 3-4 min
    - Outline: List of main topics covered
    - Meta Tags: Keywords for searchability
    - Prerequisites: Prior knowledge needed
    
    **TWO-COLUMN SCRIPT STRUCTURE**:
    - Visual Cue: Specific description of what's shown on screen
    - Narration: What the instructor says (array of sentences, one per line)
    
    === SLIDE STRUCTURE (10-13 SLIDES) ===
    
    **Slide 1: TITLE SLIDE**
    - Visual Cue: "Title Slide"
    - Narration: "Welcome to this Spoken Tutorial on [Topic]."
    
    **Slide 2: LEARNING OBJECTIVES**
    - Visual Cue: "Learning Objectives Slide"
    - Narration: "In this tutorial, you will learn to [obj1], [obj2], and [obj3]."
    
    **Slide 3: SYSTEM REQUIREMENTS**
    - Visual Cue: "System Requirements Slide"
    - Narration: "Here I am using a browser on a computer or mobile."
    - Purpose: Tell learner what tools they need
    
    **Slide 4: PREREQUISITES**
    - Visual Cue: "Pre-requisite Slide"
    - Narration: "To follow this tutorial, you must be connected to the internet.
You should also be familiar with [prerequisite concept].
No coding needed."
    - Purpose: Set expectations for prior knowledge
    
    **Slide 5: HOOK / PROBLEM STATEMENT**
    - Visual Cue: Relatable scenario showing the problem
    - Narration: Start with a question or problem the tutorial solves
    - Example: "Have you ever got a strange answer from an AI? That's because of a weak prompt."
    
    **Slide 6: CONCEPT INTRODUCTION**
    - Visual Cue: Simple graphic or text slide explaining the main concept
    - Narration: Define the concept in simple terms
    - Example: "Best prompts include three ingredients: Clarity, Context, and Constraints."
    
    **Slides 7-11: PROGRESSIVE DEMONSTRATION** (4-5 slides)
    
    **Pattern for each demonstration slide:**
    
    - **First Demo Slide (Vague Approach)**
      * Visual: "Screen recording: user typing vague prompt"
      * Narration: "Let's open any AI tool. Type a vague prompt like '[example]'. What do you think, is this clear or vague?"
      * Show the weak result
    
    - **Improvement Slide(s)** (2-3 slides, one per element)
      * Visual: "Screen close-up: user adding [specific element]"
      * Narration: "Now, let's improve it by adding [element]. [Specific instruction]."
      * Show the improved result
      * Use section headers if teaching multiple elements: "Section Header: 1. Clarity"
    
    - **Comparison Slide**
      * Visual: "Side-by-side: [element 1] vs [element 2] comparison" or "Three outputs shown side by side"
      * Narration: "See the difference? Adding [elements] improves quality significantly."
    
    **KEY DEMONSTRATION GUIDELINES:**
    - Use actual tool names: ChatGPT, Gemini, Claude
    - Show actual prompts being typed
    - Describe outputs: "The output will be broad and unfocused" → "The output is sharper, more relevant"
    - Use "pause moments": "Pause and think about it. What should the AI focus on?"
    - Use progressive reveals: Show problem → solution 1 → solution 2 → final comparison
    
    **Slide 12: SUMMARY**
    - Visual Cue: Summary slide with key points
    - Narration: "Let's summarize. [Key takeaway 1]. [Key takeaway 2]. [Key takeaway 3]."
    - Keep concise, use narrative language
    
    **Slide 13: ASSIGNMENT**
    - Visual Cue: Assignment instructions
    - Narration: "Now as an assignment, [specific task]. 
First, [step 1]. 
Then [step 2]. 
Compare the results. 
Note down which [element] made the biggest difference."
    - **CRITICAL**: Assignment MUST let learners practice what was demonstrated
    
    **Slide 14: ACKNOWLEDGEMENT**
    - Visual Cue: "EduPyramids logo"
    - Narration: "This Spoken Tutorial is brought to you by EduPyramids Educational Services Private Limited, SINE, IIT Bombay.
Thank you for joining!"
    
    === JSON OUTPUT FORMAT (STRICT) ===
    
    {{
      "presentation_title": "",
      "module": "",
      "episode": "",
      "learning_objectives": ["Use Bloom's verbs"],
      "duration": "3-4 min",
      "outline": [""],
      "meta_tags": [""],
      "prerequisites": "",
      "slides": [
        {{
          "title": "",
          "content": [""],
          "narration": [""],
          "image_prompt": "",
          "video_prompt": "",
          "is_video_slide": false
        }}
      ]
    }}
    """
    
    try:
        # Use raw client with structured output
        response = client.models.generate_content(
            model='gemini-2.5-flash',  # Use Flash to avoid timeouts
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
                                    "content": {"type": "array", "items": {"type": "string"}},
                                    "narration": {"type": "array", "items": {"type": "string"}},
                                    "image_prompt": {"type": "string"},
                                    "video_prompt": {"type": "string"},
                                    "is_video_slide": {"type": "boolean"}
                                },
                                "required": ["title", "content", "narration", "image_prompt"]
                            }
                        }
                    },
                    "required": ["slides", "module", "episode", "learning_objectives", "duration", "outline", "meta_tags", "prerequisites"]
                }
            )
        )
        json_script = json.loads(response.text)
        
        # Post-processing (same as before)
        for slide in json_script.get('slides', []):
            # Ensure content is clean
            raw_content = slide.get('content', [])
            clean_content = [c for c in raw_content if isinstance(c, str) and c.strip()]
            slide['content'] = clean_content
            
            # Ensure narration matches content + 1x
            current_narration = slide.get('narration', [])
            if isinstance(current_narration, str):
                current_narration = ["Introduction."] + [current_narration] * len(clean_content)
            
            target_length = len(clean_content) + 1
            if len(current_narration) < target_length:
                diff = target_length - len(current_narration)
                current_narration.extend([f"Point {k+1}." for k in range(diff)])
            elif len(current_narration) > target_length:
                current_narration = current_narration[:target_length]
            
            slide['narration'] = current_narration
            
        return {"json_script": json_script}
    except Exception as e:
        print(f"Failed to generate script: {e}")
        return {"json_script": {}}
