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
    
    # Generate outline following user's example format
    meta_prompt = f"""Create a detailed, practical outline for a Spoken Tutorial on: "{topic}"

=== STYLE TO FOLLOW ===

Use the EXACT style from this example:

**Module Structure:**
- Module title with topic name
- Brief welcome/intro explaining why this matters
- Clear numbered sections (2.1, 2.2, 2.3...)

**Content Style:**
- Direct, practical explanations
- Concrete examples with labels:
  * "Weak Example:", "Good Example:", "Better Example:", "Excellent Example:"
  * OR "Basic:", "Intermediate:", "Advanced:"
- Show progressions (weak → good → better)
- Include specific prompts/examples that learners can copy

**Section Format:**
Each section should have:
1. Clear section number and title (e.g., "2.1: The Anatomy of...")
2. Brief explanation (1-2 sentences)
3. Concrete examples showing the concept
4. Where applicable, show before/after or weak/strong comparisons

**Required Elements:**
- **Learning objectives (2-3 SIMPLE, ACHIEVABLE objectives)**
  * Keep them realistic for a 3-4 minute tutorial
  * Focus on ONE skill or concept, not multiple
  * Use clear action verbs: "create", "identify", "use", "apply"
  * Example: "Create a clear prompt" NOT "Master advanced prompt engineering"
- Prerequisites (what to know before)
- 5-7 main sections each with:
  * Concept explanation
  * Multiple concrete examples
  * Hands-on practice activity
- Final section: "Your Turn!" with practical exercises

**Language:**
- Simple, direct sentences
- Use "you" to address learner
- Avoid: "exciting journey", "let's dive in", "embark", "delve"
- Use: "Now...", "Here's how...", "Try this..."

**Examples Must Be:**
- Specific and actionable
- Show actual prompts/commands/code learners can try
- Progress from simple to complex
- Include expected output/results

=== OUTPUT FORMAT ===

Module [Number]: {topic}
[2-3 sentence introduction explaining why this skill matters]

[Section 2.1]: [First Main Concept]
[Explanation in 2-3 sentences]
[Concrete Example 1 with label]
[Concrete Example 2 with label]
[Concrete Example 3 showing progression]

[Section 2.2]: [Second Main Concept]
[Continue same pattern...]

[Final Section]: Your Turn! / Practical Lab
[Hands-on exercise with specific instructions]

Generate a complete, detailed outline following this exact format."""
    
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
    