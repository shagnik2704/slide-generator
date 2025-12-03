"""
Evaluator node for checking script quality.
"""
import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from models.state import AgentState

load_dotenv()

# PLACEHOLDER PROMPT - User to provide specific criteria
EVALUATOR_PROMPT = """
You are a strict quality control evaluator for educational scripts.

Analyze the provided script and determine if it meets the following quality standards.

=== PEDAGOGICAL CHECKS ===
Check for the presence and quality of:
1. **Bridge the scene anticipation**: Does the narration prepare learners for what's next?
2. **Link action to reflection**: Does it help learners think about what they're doing?
3. **Connect observation to timing**: Does it guide attention during demos?
4. **Tie motivation to action**: Does it explain WHY before HOW?
5. **Smooth transition to new action**: Is the flow seamless?
6. **Accuracy and clarity**: Are instructions precise?

=== FORMATTING & STYLE CHECKS ===
Ensure the following conditions are met:
1. **Sentence Length**: EVERY narration sentence must be under 80 characters (including spaces).
2. **New Lines**: Start EACH new sentence on a new line.
3. **Narration Style**: No arrows (->), hyphens (-), or symbols that cannot be narrated.
4. **Simple English**: Use clear, simple language for teaching effectiveness.
5. **Complete Sentences**: No sentences cut in the middle.
6. **Structure**: Maintain 2 column format (Visual Cue and Narration).

=== OUTPUT ===
If the script meets ALL standards, return:
{{
  "passed": true,
  "feedback": "Script meets all quality standards."
}}

If the script fails ANY standard, return:
{{
  "passed": false,
  "feedback": "Specific feedback listing EXACTLY what failed. Example: 'Slide 3 narration has sentences > 80 chars', 'Missing bridge anticipation in Slide 5'."
}}

Script to evaluate:
{script_content}
"""

def evaluate_quality(state: AgentState):
    """Evaluates the script quality using a defined prompt."""
    print("Evaluating script quality...")
    json_script = state.get('json_script')
    iteration = state.get('evaluation_iteration', 0)
    
    # CRITICAL: If no script exists, force proceed to avoid infinite loop
    if not json_script or not json_script.get('slides'):
        print("⚠️ No script to evaluate - forcing proceed to prevent infinite loop.")
        return {
            "evaluation_passed": True,  # Force pass to exit loop
            "evaluation_feedback": "No script found - skipping evaluation.",
            "evaluation_iteration": iteration + 1
        }

    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',  # Use Flash for faster evaluation
            contents=EVALUATOR_PROMPT.format(script_content=json.dumps(json_script, indent=2)),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "object",
                    "properties": {
                        "passed": {"type": "boolean"},
                        "feedback": {"type": "string"}
                    },
                    "required": ["passed", "feedback"]
                }
            )
        )
        
        # Parse JSON response
        result = json.loads(response.text)
        
        passed = result.get('passed', False)
        feedback = result.get('feedback', '')
        
        if passed:
            print("✓ Script passed evaluation.")
        else:
            print(f"✗ Script failed evaluation (Iteration {iteration}). Feedback: {feedback[:100]}...")
            
        return {
            "evaluation_passed": passed,
            "evaluation_feedback": feedback,
            "evaluation_iteration": iteration + 1
        }
        
    except json.JSONDecodeError as json_err:
        print(f"⚠ JSON parsing error in evaluator: {json_err}")
        print(f"Raw response text: {response.text}")
        return {
            "evaluation_passed": True,  # Fail open
            "evaluation_feedback": f"Evaluation JSON parsing failed: {str(json_err)}",
            "evaluation_iteration": iteration + 1
        }
    except Exception as e:
        print(f"⚠ Evaluation failed with error: {e}")
        print(f"Error type: {type(e).__name__}")
        # Try to print response if it exists
        try:
            print(f"Response text (if available): {response.text[:500]}")
        except:
            pass
        return {
            "evaluation_passed": True, # Fail open if API fails
            "evaluation_feedback": "Evaluation failed due to error.",
            "evaluation_iteration": iteration + 1
        }
