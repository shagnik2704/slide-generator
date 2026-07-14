from src.script_chat.state import ScriptChatState
from langgraph.config import get_stream_writer
from langchain_core.messages import SystemMessage, HumanMessage
from src.script_chat.llm import invoke_structured
from src.script_chat.prompts.ingest import INGEST_SYSTEM_PROMPT
from src.script_chat.schemas import IngestResult


def _fallback_foss_name(raw_outline: str) -> str | None:
    first_lines = raw_outline.split("\n")[:5]
    for line in first_lines:
        lower_line = line.lower()
        if "pytorch" in lower_line:
            return "PyTorch"
        if "google colab" in lower_line or "tensorflow" in lower_line:
            return "TensorFlow"
    return None

def ingest_node(state: ScriptChatState):
    """Parses the raw outline, extracts initial info."""
    writer = get_stream_writer()
    
    raw_outline = state.get("raw_outline", "")
    if not raw_outline:
        writer({"status": "Error: No outline provided", "progress": 100})
        return {"current_stage": "error"}
        
    writer({"status": "Parsing your outline...", "progress": 50})
    
    foss_name = state.get("foss_name")
    if not foss_name:
        try:
            result = invoke_structured(
                [
                    SystemMessage(content=INGEST_SYSTEM_PROMPT),
                    HumanMessage(content=f"=== OUTLINE ===\n{raw_outline}"),
                ],
                IngestResult,
                model="gpt-5-nano",
                temperature=0.0,
            )
            foss_name = result.foss_name
        except Exception:
            foss_name = _fallback_foss_name(raw_outline)
            
    writer({"status": "Parsing complete", "progress": 100})
    
    return {
        "current_stage": "grounding",
        "foss_name": foss_name
    }
