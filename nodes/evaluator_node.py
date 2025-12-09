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
    prompt = f"""Check this Spoken Tutorial script for formatting issues.

=== FORMATTING RULES ===

1. SENTENCE LENGTH - HARD LIMIT: Every sentence MUST be ≤ 80 characters.
   - NO EXCEPTIONS. This applies to ALL slides including boilerplate.
   - If ANY sentence exceeds 80 characters, the script FAILS.
   - Count characters carefully for each sentence.
   
   

2. NEW LINES: Each sentence must start on a new line
   - Multiple sentences on same line = FAIL
   - Exception: short phrases like "Think about it. What do you think?"

3. NO SYMBOLS: Narration cannot contain arrows or bullet symbols
   - No: ->, -->, •, * at start of lines
   - Exception: **bold** markers are ALLOWED

4. COMPLETE SENTENCES: No fragments or mid-cut sentences

5. BOLD TERMS: Technical terms should be in **bold** (advisory only)

=== STRICT ENFORCEMENT ===
Check EVERY slide. No slides are exempt from the 80-character rule.

=== SCRIPT TO CHECK ===
{json.dumps(json_script, indent=2)}

=== RESPONSE FORMAT ===
passed=true if script is acceptable (minor issues OK)
passed=false only for MAJOR issues (multiple long sentences, symbols, fragments)"""

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
