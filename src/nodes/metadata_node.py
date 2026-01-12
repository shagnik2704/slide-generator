"""
Metadata extraction node for the script generation pipeline.
Stage 1: Extracts/generates metadata from user-provided content.

Input: User outline/content
Output: ScriptMetadata (title, module, episode, LOs, duration, etc.)
"""
import os
from dotenv import load_dotenv
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.core.state import AgentState

load_dotenv()


# === OUTPUT SCHEMA ===

class ScriptMetadata(BaseModel):
    """Metadata extracted/generated from user content."""
    
    # Core identifiers
    presentation_title: str = Field(
        description="Full title, format: 'Spoken Tutorial on [Topic]'"
    )
    module: str = Field(
        description="Module name or category"
    )
    episode: str = Field(
        description="Episode number and topic, e.g., '5. 3 Cs of Prompting'"
    )
    
    # Learning design
    learning_objectives: List[str] = Field(
        description="3-5 learning objectives using Bloom's verbs"
    )
    prerequisites: str = Field(
        description="Required prior knowledge. End with 'For pre-requisite tutorials, please visit this website.'"
    )
    
    # Content structure
    outline: List[str] = Field(
        description="Main content topics extracted from user input (DO NOT invent new topics)"
    )
    
    # Classification
    tutorial_type: Literal["conceptual", "demo"] = Field(
        description="'conceptual' for explaining ideas, 'demo' for step-by-step software walkthroughs"
    )
    
    # Discoverability
    meta_tags: List[str] = Field(
        description="8-12 keywords for searchability"
    )
    
    # Timing (will be recalculated after narration)
    duration: str = Field(
        default="3-4 min",
        description="Estimated tutorial duration"
    )


# === MAIN NODE FUNCTION ===

def extract_metadata(state: AgentState) -> dict:
    """
    Extracts/generates metadata from user-provided content.
    
    This is the first node in the pipeline - it analyzes whatever
    the user provides (outline, document, topic) and creates
    structured metadata for the rest of the pipeline.
    """
    print("📋 Stage 1: Extracting metadata...")
    
    # Get user content (could be outline, or extracted text from uploaded doc)
    user_content = state.get('outline', '')
    
    if not user_content:
        print("⚠️ No content provided for metadata extraction")
        return {"metadata": None, "tutorial_type": "conceptual"}
    
    # Initialize LLM with structured output
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    llm_openai = ChatOpenAI(model="gpt-5.2")
    structured_llm = llm.with_structured_output(ScriptMetadata)
    structured_llm_openai = llm_openai.with_structured_output(ScriptMetadata)
    
    messages = get_metadata_extraction_messages(user_content)
    
    try:
        result = structured_llm.invoke(messages)
        
        if result is None:
            print("⚠️ LLM returned None, using fallback metadata")
            return _create_fallback_metadata(user_content)
        
        metadata = result.model_dump()
        
        print(f"✓ Metadata extracted:")
        print(f"   Title: {metadata['presentation_title']}")
        print(f"   Type: {metadata['tutorial_type']}")
        print(f"   Topics: {len(metadata['outline'])} topics")
        print(f"   LOs: {len(metadata['learning_objectives'])} objectives")
        
        return {
            "metadata": metadata,
            "tutorial_type": metadata['tutorial_type']
        }
        
    except Exception as e:
        print(f"Metadata extraction failed: {e}")
        return {"metadata": None, "tutorial_type": None}


# === PROMPT MESSAGES ===

def get_metadata_extraction_messages(user_content: str) -> list:
    """Messages for metadata extraction."""
    
    system_content = """You are extracting metadata from user-provided content for a Spoken Tutorial script.

=== YOUR TASK ===
Analyze the content and extract/generate structured metadata.

=== FIELD RULES ===

**presentation_title**
- Format: "Spoken Tutorial on [Topic]"
- No bold markers or special formatting
- Example: "Spoken Tutorial on Understanding APIs"

**module**
- Extract from content, or infer from topic
- Example: "Introduction to AI", "Web Development Basics"

**episode**
- Format: "[Number]. [Topic]"
- Example: "5. 3 Cs of Prompting"

**learning_objectives** (CRITICAL)
- 3-5 objectives maximum
- Each objective ≤ 80 characters
- Make them ACHIEVABLE

**prerequisites**
- What the learner should know beforehand
- End with: "For pre-requisite tutorials, please visit this website."

**outline**
- Extract topics mentioned in the user's content

**tutorial_type**
- "conceptual": Explains WHAT/WHY/HOW concepts work
  - Keywords: "What is", "Understanding", "Explain", "Introduction to"
  - Focus: Definitions, analogies, theory
  
- "demo": Step-by-step SOFTWARE WALKTHROUGH
  - Keywords: "How to", "Setting up", "Create", "Install", "Configure"
  - Focus: Clicking, typing, navigating UI

**meta_tags**
- 8-12 relevant keywords for searchability
- Include: topic name, related concepts, tools mentioned

**duration**
- Will be recalculated after narration is written

Extract metadata from the content provided."""

    human_content = f"""Extract metadata from the following content:

{user_content}"""

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content)
    ]

