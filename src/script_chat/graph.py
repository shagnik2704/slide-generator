from langgraph.graph import StateGraph, START, END
from src.script_chat.state import ScriptChatState
from src.script_chat.nodes.ingest import ingest_node
from src.script_chat.nodes.ground import ground_node, ground_review_node, ground_edit_node
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
    builder.add_node("ground_edit", ground_edit_node)
    builder.add_node("metadata", metadata_node)
    builder.add_node("metadata_review", metadata_review_node)
    builder.add_node("metadata_edit", metadata_edit_node)
    builder.add_node("generate", generate_node)
    builder.add_node("script_review", script_review_node)
    builder.add_node("edit", edit_node)
    builder.add_node("compliance", compliance_node)
    builder.add_node("compliance_review", compliance_review_node)
    
    builder.add_edge(START, "ingest")

    def route_after_ingest(state: ScriptChatState):
        return "ground" if state.get("current_stage") == "grounding" else END

    builder.add_conditional_edges("ingest", route_after_ingest)

    def route_after_ground(state: ScriptChatState):
        if state.get("current_stage") == "error":
            return END
        return "ground_review" if state.get("grounding_report") else END

    builder.add_conditional_edges("ground", route_after_ground)
    
    # Conditional: after ground review → ground_edit or metadata
    def route_after_ground_review(state: ScriptChatState):
        stage = state.get("current_stage")
        if stage == "grounding_edit":
            return "ground_edit"
        if stage == "metadata":
            return "metadata"
        if stage == "error":
            return END
        return END

    builder.add_conditional_edges("ground_review", route_after_ground_review)
    
    def route_after_ground_edit(state: ScriptChatState):
        return "ground" if state.get("current_stage") == "grounding" else END

    builder.add_conditional_edges("ground_edit", route_after_ground_edit)

    def route_after_metadata_node(state: ScriptChatState):
        if state.get("current_stage") == "error":
            return END
        return "metadata_review" if state.get("metadata") else END

    builder.add_conditional_edges("metadata", route_after_metadata_node)
    
    def route_after_metadata_edit_node(state: ScriptChatState):
        if state.get("current_stage") == "error":
            return END
        return "metadata_review" if state.get("metadata") else END
    
    builder.add_conditional_edges("metadata_edit", route_after_metadata_edit_node)
    
    def route_after_generate_node(state: ScriptChatState):
        if state.get("current_stage") == "error":
            return END
        return "script_review" if state.get("script") else END
    
    builder.add_conditional_edges("generate", route_after_generate_node)

    def route_after_edit_node(state: ScriptChatState):
        if state.get("current_stage") == "error":
            return END
        return "script_review" if state.get("script") else END
    
    builder.add_conditional_edges("edit", route_after_edit_node)

    def route_after_compliance_node(state: ScriptChatState):
        if state.get("current_stage") == "error":
            return END
        return "compliance_review" if state.get("compliance_results") else END

    builder.add_conditional_edges("compliance", route_after_compliance_node)
    
    # Conditional: after metadata review → metadata_edit or generate
    def route_after_metadata_review(state: ScriptChatState):
        stage = state.get("current_stage")
        if stage == "metadata_edit":
            return "metadata_edit"
        if stage == "generate":
            return "generate"
        return END

    builder.add_conditional_edges("metadata_review", route_after_metadata_review)
    
    # Conditional: after script review → edit or compliance
    def route_after_script_review(state: ScriptChatState):
        stage = state.get("current_stage")
        if stage == "edit":
            return "edit"
        if stage == "compliance":
            return "compliance"
        return END

    builder.add_conditional_edges("script_review", route_after_script_review)
    
    # Conditional: after compliance review → done or back to edit
    def route_after_compliance_review(state: ScriptChatState):
        stage = state.get("current_stage")
        if stage == "edit":
            return "edit"
        return END

    builder.add_conditional_edges("compliance_review", route_after_compliance_review)
    
    return builder.compile(checkpointer=checkpointer)
