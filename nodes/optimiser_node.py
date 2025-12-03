"""
Optimiser node for improving script based on feedback.
"""
import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from models.state import AgentState

load_dotenv()
# 1. Is the assignment fulfilling the learning objectives?
# 2. Is the script LO compliant?
# 3. Are sentences short and simple (Indian English)?

def optimise_script(state: AgentState):
    """Optimises the script based on evaluation feedback."""
    print("Optimising script based on feedback...")
    json_script = state.get('json_script')
    feedback = state.get('evaluation_feedback', '')
    
    if not json_script:
        return {"json_script": {}}

    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    
    prompt = f"""
    You are an expert script editor.
    
    Your task is to improve the following script based on the provided feedback.
    
    === FEEDBACK ===
    {feedback}
    
    === SCRIPT TO IMPROVE ===
    {json.dumps(json_script, indent=2)}
    
    === INSTRUCTIONS ===
    1. Address ALL points in the feedback.
    2. Maintain the exact same JSON structure.
    3. Do not remove any slides unless explicitly asked.
    4. Ensure the output is valid JSON.
    
    Return the COMPLETE updated script.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',  # Use Flash for faster optimization
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
        
        optimised_script = json.loads(response.text)
        print("✓ Script optimised.")
        return {"json_script": optimised_script}
        
    except Exception as e:
        print(f"Optimisation failed: {e}")
        return {"json_script": json_script} # Return original on failure
