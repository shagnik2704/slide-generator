import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.script_chat.state import ScriptChatState
from langgraph.config import get_stream_writer
from langgraph.types import interrupt
from src.script_chat.prompts.grounding import GROUNDING_SYSTEM_PROMPT
from pydantic import BaseModel, Field

def ground_node(state: ScriptChatState):
    """Grounds the content using Google Search."""
    if state.get("grounding_report"):
        return {}
        
    writer = get_stream_writer()
    raw_outline = state.get("raw_outline", "")
    foss_name = state.get("foss_name", "Unknown Software")
    
    writer({"status": f"Searching latest docs for {foss_name}...", "progress": 25})
    
    # Setup OpenAI client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        writer({"status": "Error: OPENAI_API_KEY not found", "progress": 100})
        return {"current_stage": "error"}
        
    llm = ChatOpenAI(
        model="gpt-5.4-mini",
        temperature=0.2,
        api_key=api_key
    ).bind_tools([{"type": "web_search"}])
    
    writer({"status": "Validating code snippets against web results...", "progress": 50})
    
    messages = [
        SystemMessage(content=GROUNDING_SYSTEM_PROMPT),
        HumanMessage(content=f"Please validate this outline for {foss_name}:\n\n{raw_outline}")
    ]
    
    try:
        response = llm.invoke(messages)
        text_response = response.content
        if isinstance(text_response, list):
            text_response = "".join([block.get("text", "") for block in text_response if isinstance(block, dict) and block.get("type") == "text"])
        if "```json" in text_response:
            text_response = text_response.split("```json")[1].split("```")[0]
        elif "```" in text_response:
            text_response = text_response.split("```")[1].split("```")[0]
        report_dict = json.loads(text_response.strip())
    except Exception as e:
        writer({"status": f"Grounding failed: {str(e)}", "progress": 100})
        return {"current_stage": "error", "grounding_report": None}
    
    writer({"status": "Validation complete", "progress": 100})
    
    return {
        "grounding_report": report_dict
    }

def ground_review_node(state: ScriptChatState):
    """Surfaces grounding results for HITL review."""
    report_dict = state.get("grounding_report")
    if not report_dict:
        return {"current_stage": "error"}
    
    # The interrupt pauses execution here and sends this payload to the client.
    # The graph will wait until it is invoked again with Command(resume=decision)
    user_decision = interrupt({
        "type": "validation_review",
        "report": report_dict,
        "message": "Review the grounding results. Please approve or provide edits."
    })
    
    # Execution resumes here
    if not user_decision or not isinstance(user_decision, dict):
        return {"current_stage": "error"}

    if user_decision.get("action") == "approve":
        final_content = report_dict.get("validated_content")
    else:
        # If user edited the content during review
        final_content = user_decision.get("edited_content", report_dict.get("validated_content"))
    
    return {
        "current_stage": "metadata",
        "raw_outline": final_content # Update with validated/edited content
    }
