"""
Outline generation node for the slide generator agent.
"""
import os
from dotenv import load_dotenv
from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, InternalServerError
from models.state import AgentState

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
    
    # Generate outline prompt (without target audience)
    meta_prompt = f"""Act as an expert instructional designer and curriculum developer specializing in creating engaging educational content.

Create a detailed, structured outline for a lesson/presentation on: "{topic}"

**REQUIREMENTS:**

1. **Learning Objectives**: Define 3-4 clear learning objectives that learners should achieve. Use appropriate action verbs based on the target audience

2. **Estimated Duration**: Suggest appropriate duration (e.g., "3-4 minutes", "5-7 minutes")

**OUTLINE STRUCTURE:**

Create 5-7 numbered main sections. For each section:

- Use hierarchical numbering (e.g., 2.1, 2.2, 2.3)
- Provide a clear, descriptive title
- Include 2-3 sub-points explaining what will be covered
- Where appropriate, include progressive examples showing skill development:
  * **Weak/Basic approach**
  * **Good approach**
  * **Better/Advanced approach**
  * **Excellent/Expert approach** (optional)

**SPECIAL SECTIONS TO INCLUDE:**

1. **Introduction/Overview** - Hook the audience, explain relevance
2. **Core Concepts** - 3-5 main teaching sections with examples
3. **Practical Application** - Hands-on activity or exercise
4. **Summary/Conclusion** - Key takeaways

**STYLE GUIDELINES:**

- **Spacing:** Ensure there is a blank line between every section and sub-section for readability.
- **Formatting:** Use bold text for key terms and headers.
- **Tone:** Use a friendly, conversational tone.
- **Clarity:** Make complex ideas accessible.
- **Insights:** Include "Pro Tip" or "Bonus" insights where relevant.
- **Teaching Moments:** Add teaching moments (e.g., "This sounds technical, but it's simple...")

**FORMAT:** Output as Markdown with clear hierarchy, proper numbering, and visual formatting.

**CRITICAL:** Generate original, substantive content for "{topic}". Don't just provide generic section titles - include specific details, concepts, and examples relevant to this topic.
"""
    
    try:
        print(f"Generating structured outline...")
        
        # Generate outline using Gemini 2.5 Flash (Pro was timing out)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=meta_prompt,
            config={
                'temperature': 0.7,
            }
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
    