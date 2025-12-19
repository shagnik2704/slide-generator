"""
Evaluator node for checking script quality.
Uses LangChain's ChatGoogleGenerativeAI.
"""
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from src.core.state import AgentState
import json

load_dotenv()


class EvaluationResult(BaseModel):
    passed: bool
    feedback: str
    problematic_slides: list[int] = []  # 0-indexed slide indices with issues


def evaluate_quality(state: AgentState):
    """Evaluates the script quality using LangChain."""
    
    print("Evaluating script quality...")
    json_script = state.get('json_script')
    tutorial_type = state.get('tutorial_type', 'conceptual')
    iteration = state.get('evaluation_iteration', 0)
    
    # If no script exists, force proceed
    if not json_script or not json_script.get('slides'):
        print("⚠️ No script to evaluate - skipping.")
        return {
            "evaluation_passed": True,
            "evaluation_feedback": "No script found.",
            "evaluation_iteration": iteration + 1
        }

    # Initialize LangChain model with structured output
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.7,
    )
    
    structured_llm = llm.with_structured_output(EvaluationResult)
    
    # Select evaluation prompt based on tutorial type
    if tutorial_type == "demo":
        prompt = get_demo_evaluation_prompt(json_script)
    else:
        prompt = get_conceptual_evaluation_prompt(json_script)

    try:
        result = structured_llm.invoke(prompt)
        
        # Handle None result
        if result is None:
            print("⚠ Evaluator returned None - passing by default")
            return {
                "evaluation_passed": True,
                "evaluation_feedback": "Evaluator returned no result.",
                "evaluation_iteration": iteration + 1,
                "problematic_slides": []
            }
        
        passed = result.passed
        feedback = result.feedback
        
        if passed:
            print("✓ Script passed evaluation.")
        else:
            print(f"✗ Script failed. Feedback: {feedback[:100]}...")
            
        return {
            "evaluation_passed": passed,
            "evaluation_feedback": feedback,
            "evaluation_iteration": iteration + 1,
            "problematic_slides": result.problematic_slides if hasattr(result, 'problematic_slides') else []
        }
        
    except Exception as e:
        print(f"⚠ Evaluation error: {e}")
        return {
            "evaluation_passed": True,  # Fail open
            "evaluation_feedback": f"Evaluation error: {e}",
            "evaluation_iteration": iteration + 1,
            "problematic_slides": []
        }


def get_conceptual_evaluation_prompt(json_script: dict) -> str:
    """Evaluation prompt for conceptual tutorials - checks narrative flow."""
    return f"""Check this Spoken Tutorial script for formatting AND narrative quality.

=== PART 1: FORMATTING RULES ===

1. SENTENCE LENGTH: Every sentence MUST be ≤ 80 characters.
   - SKIP this check for Learning Objectives slide (uses bullet format).
   - SKIP this check for Thank You Slide.

2. NEW LINES: Each sentence must start on a new line (\\n).

3. NO SYMBOLS in narration:
   - Forbidden: ->, -->, *, - at start of lines
   - ALLOWED: **bold** markers
   - ALLOWED: • bullets ONLY in Learning Objectives slide

4. BOLD TERMS: Technical terms should use **bold** (advisory).

5. Check for fragmented sentences.

=== PART 2: NARRATIVE QUALITY (CONCEPTUAL) ===

Check if the script has good narrative flow:

1. BRIDGE SCENE ANTICIPATION - Does it build curiosity?
2. LINK ACTION TO REFLECTION - Are there prompts for learner to think?
3. CONNECT OBSERVATION TO TIMING - Does it point out WHEN/WHAT to notice?
4. TIE MOTIVATION TO ACTION - Does it explain WHY the learner should care?
5. SMOOTH TRANSITIONS - Are slides connected naturally?
6. ACCURACY AND CLARITY - Are descriptions specific, not vague?

=== SCRIPT TO CHECK ===
{json.dumps(json_script, indent=2)}

=== RESPONSE ===
passed=true if:
- No sentence exceeds 80 characters
- Has at least SOME narrative flow patterns (doesn't need all 6)

passed=false if:
- Multiple formatting violations, OR
- Narration is choppy with no flow (reads like bullet points)

IMPORTANT: Always include problematic_slides as a list of 0-indexed slide numbers with issues.
Example: If slide 2 and slide 5 have issues, return problematic_slides: [2, 5]"""


def get_demo_evaluation_prompt(json_script: dict) -> str:
    """Evaluation prompt for demo tutorials - checks action-focused narration."""
    return f"""Check this DEMO Tutorial script for formatting AND action-focused quality.

=== PART 1: FORMATTING RULES (SAME FOR ALL) ===

1. SENTENCE LENGTH: Every sentence MUST be ≤ 80 characters.
   - SKIP this check for Learning Objectives slide.
   - SKIP this check for Thank You Slide.

2. NEW LINES: Each sentence must start on a new line (\\n).

3. NO SYMBOLS in narration:
   - Forbidden: ->, -->, *, - at start of lines
   - ALLOWED: **bold** markers
   - ALLOWED: • bullets ONLY in Learning Objectives slide

4. BOLD TERMS: UI elements and buttons should use **bold**.

5. Check for fragmented sentences.

=== PART 2: DEMO QUALITY (ACTION-FOCUSED) ===

Check if the script is properly action-focused:

1. ACTION VERBS: Do sentences have action verbs?
   - Good: "Click", "Open", "Type", "Select", "Navigate", "Copy"

2. ONE ACTION PER SENTENCE: Is each sentence focused on a single action?
   - Good: "Click Get API Key."
   - Bad: "Click Get API Key and then select the project and copy the key."

3. EXPLICIT SCREEN LOCATIONS (CRITICAL): Does it describe WHERE elements are?
   - Good: "In the **top right corner**, click **Sign In**."
   - Good: "On the **left panel**, click **Get API Key**."
   - Good: "At the **bottom of the dialog**, click **Create**."
   - Bad: "Click Sign In." (no location specified)
   - Bad: "Click Settings." (WHERE on screen?)

4. VERIFICATION CUES: After key actions, does it tell what to expect?
   - Good: "You will see...", "The key appears..."

=== SCRIPT TO CHECK ===
{json.dumps(json_script, indent=2)}

=== RESPONSE ===
passed=true if:
- No sentence exceeds 80 characters
- Uses action verbs appropriately
- Steps are clear and focused

passed=false if:
- Multiple formatting violations, OR
- Narration is not action-focused (too conceptual/explanatory)

IMPORTANT: Always include problematic_slides as a list of 0-indexed slide numbers with issues.
Example: If slide 2 and slide 5 have issues, return problematic_slides: [2, 5]"""

