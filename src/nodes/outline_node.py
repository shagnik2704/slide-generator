"""
Outline generation node for the slide generator agent.
"""
import os
from dotenv import load_dotenv
from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, InternalServerError
from src.core.state import AgentState

load_dotenv()


@retry(
    retry=retry_if_exception_type((ResourceExhausted, ServiceUnavailable, InternalServerError)),
    wait=wait_exponential(multiplier=4, min=4, max=60),
    stop=stop_after_attempt(5)
)
def generate_outline(state: AgentState):
    """Generates a structured, educational presentation outline using meta-prompting."""
    print("Generating enhanced outline...")
    print(f"Generating outline for: {state.get('topic')}")
    topic = state.get('topic') or state.get('outline')
    
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    
    # Generate outline
    meta_prompt = f"{topic}"
    
    try:
        print(f"Generating structured outline...")
        
        # Generate outline using Gemini 2.5 Flash (Pro was timing out)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=meta_prompt,
        )
        
        # Enhanced outline generation with formatting
        outline = response.text
        enhanced_outline = f"""# Presentation Outline

**Topic:** {topic.title()}

{outline}
"""

        print("✓ Enhanced outline generated successfully")
        return {"outline": enhanced_outline}
        
    except Exception as e:
        print(f"Outline generation failed: {e}")
        # Fallback: Simple outline generation
        fallback_prompt = f"""Create a simple outline for a presentation on "{topic}". Include 6-8 main sections with brief descriptions."""
        
        try:
            fallback_response = client.models.generate_content(model='gemini-2.5-flash', contents=fallback_prompt)
            return {"outline": fallback_response.text}
        except:
            return {"outline": "Failed to generate outline."}
    