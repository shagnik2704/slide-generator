"""
Evaluator node for checking script quality.
Uses LangChain's ChatGoogleGenerativeAI.
"""
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from models.state import AgentState
import json

load_dotenv()


class EvaluationResult(BaseModel):
    passed: bool
    feedback: str


def evaluate_quality(state: AgentState):
    """Evaluates the script quality using LangChain."""
    
    print("Evaluating script quality...")
    json_script = state.get('json_script')
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
    
    # Formatting evaluation prompt
    prompt = f"""Check this Spoken Tutorial script for formatting AND narrative quality.

=== PART 1: FORMATTING RULES ===

1. SENTENCE LENGTH: Every sentence MUST be ≤ 80 characters.
   - SKIP this check for Learning Objectives slide (uses bullet format).

2. NEW LINES: Each sentence must start on a new line (\\n).

3. NO SYMBOLS in narration:
   - Forbidden: ->, -->, *, - at start of lines
   - ALLOWED: **bold** markers
   - ALLOWED: • bullets ONLY in Learning Objectives slide

4. BOLD TERMS: Technical terms should use **bold** (advisory).

5.Check for fragmented sentences.

=== PART 2: NARRATIVE QUALITY ===

Check if the script has good narrative flow using these patterns:

1. BRIDGE SCENE ANTICIPATION
   - Does it build curiosity before explaining?
   - Example: "What if I told you..." or "Imagine..."

2. LINK ACTION TO REFLECTION
   - Are there prompts for learner to think?
   - Example: "Notice...", "Think about it...", "Pause for a moment..."

3. CONNECT OBSERVATION TO TIMING
   - Does it point out WHEN and WHAT to notice?
   - Example: "At this point...", "See what happens when..."

4. TIE MOTIVATION TO ACTION
   - Does it explain WHY the learner should care?
   - Example: "This matters because...", "This could happen to you..."

5. SMOOTH TRANSITIONS
   - Are slides connected naturally?
   - Not abrupt jumps between topics

6. ACCURACY AND CLARITY
   - Are descriptions specific, not vague?
   - "The skin texture matches perfectly" vs "It looks real"

=== SCRIPT TO CHECK ===
{json.dumps(json_script, indent=2)}

=== RESPONSE ===
passed=true if:
- No sentence exceeds 80 characters
- Has at least SOME narrative flow patterns (doesn't need all 6)

passed=false if:
- Multiple formatting violations, OR
- Narration is choppy with no flow (reads like bullet points)"""

    try:
        result = structured_llm.invoke(prompt)
        
        # Handle None result
        if result is None:
            print("⚠ Evaluator returned None - passing by default")
            return {
                "evaluation_passed": True,
                "evaluation_feedback": "Evaluator returned no result.",
                "evaluation_iteration": iteration + 1
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
            "evaluation_iteration": iteration + 1
        }
        
    except Exception as e:
        print(f"⚠ Evaluation error: {e}")
        return {
            "evaluation_passed": True,  # Fail open
            "evaluation_feedback": f"Evaluation error: {e}",
            "evaluation_iteration": iteration + 1
        }
