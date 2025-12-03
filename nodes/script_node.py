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
    
    Generate a complete presentation script for the outline: "{outline}".
    The presentation should typically have 10-11 slides following the structure below.
    
    === IIT BOMBAY FOSSEE / EDUPYRAMIDS STANDARDS ===
    
    **METADATA TABLE (REQUIRED)**:
    - Module: Descriptive module name
    - Episode: Episode number and title
    - Learning Objectives: 3-4 clear objectives using Bloom's Taxonomy verbs
    - Duration: 3-4 min (approximately 500 words total narration)
    - Outline: List of main topics covered
    - Meta Tags: Keywords for searchability
    - Prerequisites: Prior knowledge or technical competencies needed
    
    **BLOOM'S TAXONOMY PROGRESSION**:
    Use these action verbs for learning objectives (Remember → Understand → Apply → Analyze → Evaluate → Create).
    
    **TWO-COLUMN SCRIPT STRUCTURE**:
    Each slide must have:
    - Visual Cue: Short description of what is shown on screen
    - Narration: What the instructor says (aligned with visual)
    
    **QUALITY GUIDELINES**:
    - Keep all sentences ≤ 80 characters.
    - Use simple Indian English.
    - Maintain clear examples.
    - Ensure total duration ≈ 3–4 minutes.
    - Short, active sentences (8–15 words).
    - Visual + narration alignment.
    - Pause cues included (e.g., "[Pause]").
    - Consistent tone and pacing.
    
    **NARRATIVE TECHNIQUES**:
    - Bridge the scene anticipation.
    - Link action to reflection.
    - Connect observation to timing.
    - Tie motivation to action.
    - Smooth transition to new action.
    - Improve accuracy and clarity.
    
    === SLIDE STRUCTURE (STRICT) ===
    
    **Slide 1: TITLE SLIDE**
    - Visual Cue: Tutorial title, presenter name
    - Narration: Warm, simple welcome
    
    **Slide 2: LEARNING OBJECTIVES**
    - Visual Cue: 3-4 learning objectives using Bloom's verbs
    - Narration: "At the end of this tutorial, you will be able to..."
    
    **Slide 3: PREREQUISITES**
    - Visual Cue: Prior knowledge or technical competencies
    - Narration: Friendly, bridging tone
    
    **Slide 4: SYSTEM REQUIREMENTS**
    - Visual Cue: Minimal, simple setup
    - Narration: State requirements clearly
    
    **Slide 5: CONCEPT INTRODUCTION**
    - Start with a relatable question or analogy.
    - Visual Cue: Illustration of the analogy.
    - Narration: Introduce the concept using the analogy.
    
    **Slide 6-8: CONCEPT DEVELOPMENT (2-3 Slides)**
    - 2-3 examples or demonstrations.
    - Step-by-step instructions for demo/illustrations to practice side by side.
    - Visual Cue: Specific visuals for examples/demos.
    - Narration: Clear explanation, linking back to the concept.
    
    **Slide 9: SUMMARY**
    - Visual Cue: Key points, concise bullets.
    - Narration: Brief recap.
    
    **Slide 10: ASSIGNMENT**
    - Visual Cue: 1 small activity that applies learning.
    - Narration: Instructions for the assignment.
    - **CRITICAL**: Assignment MUST directly fulfill the stated learning objectives.
    
    **Slide 11: ACKNOWLEDGEMENT & CLOSING**
    - Visual Cue: Mention EduPyramids / IIT Bombay Spoken Tutorial.
    - Narration: Closing remarks.
    
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
