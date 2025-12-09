"""
Optimiser node for improving script based on feedback.
Uses LangChain's ChatGoogleGenerativeAI.
"""
import os
import json
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from models.state import AgentState

load_dotenv()


# Reuse the same schema from script_node
class Slide(BaseModel):
    title: str
    narration: str
    image_prompt: Optional[str] = ""


class Script(BaseModel):
    presentation_title: str = ""
    module: str = ""
    episode: str = ""
    learning_objectives: List[str] = Field(default_factory=list)
    duration: str = ""
    outline: List[str] = Field(default_factory=list)
    meta_tags: List[str] = Field(default_factory=list)
    prerequisites: str = ""
    slides: List[Slide]


def optimise_script(state: AgentState):
    """Optimises the script based on evaluation feedback using LangChain."""
    print("Optimising script based on feedback...")
    json_script = state.get('json_script')
    feedback = state.get('evaluation_feedback', '')
    
    if not json_script:
        return {"json_script": {}}

    # Initialize LangChain model with structured output
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
    )
    
    structured_llm = llm.with_structured_output(Script)
    
    # Optimization prompt with fix instructions
    prompt = f"""Fix this Spoken Tutorial script based on the evaluator's feedback.

=== EVALUATOR FEEDBACK ===
{feedback}

=== FIX INSTRUCTIONS ===

1. LONG SENTENCES (>80 chars):
   - Split into two shorter, complete sentences
   - Each new sentence on its own line
   - Do NOT create fragments

2. MISSING NEWLINES:
   - Put each sentence on a new line
   - Use \\n between sentences in the narration field

3. SYMBOLS (arrows, hyphens, bullets):
   - Rewrite using words: "First," "Next," "Then," "Finally,"
   - Convert lists to flowing sentences

4. INCOMPLETE SENTENCES:
   - Complete any fragments
   - Ensure grammatical completeness


=== SCRIPT TO FIX ===
{json.dumps(json_script, indent=2)}

Return the corrected script with all issues fixed."""

    try:
        result = structured_llm.invoke(prompt)
        optimised_script = result.model_dump()
        print("✓ Script optimised.")
        return {"json_script": optimised_script}
        
    except Exception as e:
        print(f"Optimisation failed: {e}")
        return {"json_script": json_script}  # Return original on failure
