from langgraph.graph import StateGraph, START, END
from src.script_chat.state import ScriptChatState
from src.script_chat.nodes.ingest import ingest_node
from src.script_chat.nodes.ground import ground_node, ground_review_node
from src.script_chat.nodes.metadata import metadata_node, metadata_review_node
from src.script_chat.nodes.generate import generate_node, script_review_node
from src.script_chat.nodes.edit import edit_node
from src.script_chat.nodes.metadata_edit import metadata_edit_node
from src.script_chat.nodes.compliance import compliance_node, compliance_review_node

def build_script_chat_graph(checkpointer=None):
    """Build the LangGraph for the script chat flow.
    
    Graph:
        START → ingest → ground → ground_review → metadata → metadata_review ⇄ metadata_edit
        → generate → script_review ⇄ edit (loop)
        → compliance → compliance_review → END (or back to edit)
    """
    builder = StateGraph(ScriptChatState)
    
    # Add all nodes
    builder.add_node("ingest", ingest_node)
    builder.add_node("ground", ground_node)
    builder.add_node("ground_review", ground_review_node)
    builder.add_node("metadata", metadata_node)
    builder.add_node("metadata_review", metadata_review_node)
    builder.add_node("metadata_edit", metadata_edit_node)
    builder.add_node("generate", generate_node)
    builder.add_node("script_review", script_review_node)
    builder.add_node("edit", edit_node)
    builder.add_node("compliance", compliance_node)
    builder.add_node("compliance_review", compliance_review_node)
    
    # Linear edges: ingestion pipeline
    builder.add_edge(START, "ingest")
    builder.add_edge("ingest", "ground")
    builder.add_edge("ground", "ground_review")
    builder.add_edge("ground_review", "metadata")
    builder.add_edge("metadata", "metadata_review")
    
    # Metadata edit loop: after editing, back to metadata_review
    builder.add_edge("metadata_edit", "metadata_review")
    
    builder.add_edge("generate", "script_review")
    
    # Edit loop: after editing, back to script_review
    builder.add_edge("edit", "script_review")
    
    # Compliance pipeline
    builder.add_edge("compliance", "compliance_review")
    
    # Conditional: after metadata review → metadata_edit or generate
    def route_after_metadata_review(state: ScriptChatState):
        stage = state.get("current_stage")
        if stage == "metadata_edit":
            return "metadata_edit"
        elif stage == "generate":
            return "generate"
        return "generate"

    builder.add_conditional_edges(
        "metadata_review",
        route_after_metadata_review
    )
    
    # Conditional: after script review → edit or compliance
    def route_after_script_review(state: ScriptChatState):
        stage = state.get("current_stage")
        if stage == "edit":
            return "edit"
        elif stage == "compliance":
            return "compliance"
        return "compliance"  # Default: proceed to compliance

    builder.add_conditional_edges(
        "script_review",
        route_after_script_review
    )
    
    # Conditional: after compliance review → done or back to edit
    def route_after_compliance_review(state: ScriptChatState):
        stage = state.get("current_stage")
        if stage == "edit":
            return "edit"
        return END  # Done

    builder.add_conditional_edges(
        "compliance_review",
        route_after_compliance_review
    )
    
    # Compile
    return builder.compile(checkpointer=checkpointer)
