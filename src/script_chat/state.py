from typing import TypedDict, Optional, Annotated, Any
import operator

class ScriptChatState(TypedDict):
    """The state for the script chat graph."""
    # Conversation history
    messages: Annotated[list[Any], operator.add]
    
    # Core data
    raw_outline: Optional[str]
    foss_name: Optional[str]
    grounding_report: Optional[dict]
    metadata: Optional[dict]
    script: Optional[list[dict]]
    
    # Edit loop
    edit_instruction: Optional[str]
    
    # Tracking
    script_version: int
    compliance_results: Optional[dict]
    quality_results: Optional[dict]
    current_stage: str
