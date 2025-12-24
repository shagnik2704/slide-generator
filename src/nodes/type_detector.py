"""
Tutorial type detection node.
Analyzes the outline and determines if it's conceptual or demo-based.
"""
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from src.core.state import AgentState

load_dotenv()


def detect_tutorial_type(state: AgentState) -> dict:
    """
    Analyzes the outline and determines the tutorial type:
    - 'conceptual': Explaining concepts, theory, definitions
    - 'demo': Step-by-step software walkthrough
    """
    print("🔍 Detecting tutorial type...")
    outline = state.get('outline', '')
    
    if not outline:
        print("⚠️ No outline provided, defaulting to conceptual")
        return {"tutorial_type": "conceptual"}
    
    llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview")
    
    prompt = f"""Classify this tutorial outline into ONE of two types:

TYPE 1: "conceptual"
- Explains WHAT something is, WHY it matters, HOW it works conceptually
- Focus on understanding, definitions, analogies
- Examples: "What is an API?", "Understanding deepfakes", "3 Cs of Prompting"

TYPE 2: "demo"  
- Involving a software
- Step-by-step SOFTWARE WALKTHROUGH with specific actions
- Focus on clicking, typing, navigating UI
- Examples: "How to create an API key", "Setting up ChatGPT", "Installing Python"

OUTLINE TO CLASSIFY:
{outline}

IMPORTANT: Return ONLY the single word "conceptual" or "demo" with no other text."""

    try:
        result = llm.invoke(prompt)
        tutorial_type = result.content.strip().lower().replace('"', '').replace("'", "")
        
        # Validate the response
        if tutorial_type not in ["conceptual", "demo"]:
            print(f"⚠️ Unexpected type '{tutorial_type}', defaulting to conceptual")
            tutorial_type = "conceptual"
        
        print(f"✓ Tutorial type detected: {tutorial_type}")
        return {"tutorial_type": tutorial_type}
        
    except Exception as e:
        print(f"❌ Type detection failed: {e}, defaulting to conceptual")
        return {"tutorial_type": "conceptual"}
