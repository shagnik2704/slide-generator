"""
Main agent workflow for the slide generator.
All business logic has been modularized into separate files.

4-NODE SCRIPT PIPELINE (Parallel):
  Stage 1: extract_metadata - Extract metadata from user content
  Stage 2a: generate_boilerplate - Generate 7 boilerplate slides (parallel)
  Stage 2b: generate_content - Generate content slides (parallel)  
  Stage 3: merge_script - Combine into final json_script
"""
# Load environment variables first for LangSmith tracing
from dotenv import load_dotenv
load_dotenv()

from langgraph.graph import StateGraph, START, END
from src.core.state import AgentState

# === SCRIPT PIPELINE IMPORTS ===
from src.nodes.metadata_node import extract_metadata
from src.nodes.boilerplate_node import generate_boilerplate
from src.nodes.content_node import generate_content
from src.nodes.merge_node import merge_script

# === ROUTING ===
from src.routing.router import route_step


def build_graph(checkpointer=None):
    """Build and compile the LangGraph workflow with optional checkpointer."""
    
    builder = StateGraph(AgentState)

    # === 4-NODE SCRIPT PIPELINE ===
    builder.add_node("extract_metadata", extract_metadata)          # Stage 1
    builder.add_node("generate_boilerplate", generate_boilerplate)  # Stage 2a
    builder.add_node("generate_content", generate_content)          # Stage 2b
    builder.add_node("merge_script", merge_script)                  # Stage 3


    # === ROUTING FROM START ===
    builder.add_conditional_edges(START, route_step, {
        "script": "extract_metadata",  # Start with metadata extraction
        "pdf": "extract_metadata",     # Temporary: route PDF to script for now
        "video": "extract_metadata"    # Temporary: route video to script for now
    })


    # === SCRIPT PIPELINE EDGES ===
    # Stage 1 -> Stage 2a AND Stage 2b (parallel fan-out)
    builder.add_edge("extract_metadata", "generate_boilerplate")
    builder.add_edge("extract_metadata", "generate_content")
    
    # Stage 2a AND Stage 2b -> Stage 3 (fan-in at merge)
    builder.add_edge("generate_boilerplate", "merge_script")
    builder.add_edge("generate_content", "merge_script")
    
    # Stage 3 -> END
    builder.add_edge("merge_script", END)

    # Compile graph with optional checkpointer
    return builder.compile(checkpointer=checkpointer)


# For backwards compatibility and non-async usage (e.g., testing)
# Creates a graph without checkpointer by default
graph = build_graph()
