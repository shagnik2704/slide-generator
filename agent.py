"""
Main agent workflow for the slide generator.
All business logic has been modularized into separate files.
"""
from langgraph.graph import StateGraph, START, END
from models.state import AgentState
from nodes.outline_node import generate_outline
from nodes.script_node import generate_script
from nodes.evaluator_node import evaluate_quality
from nodes.optimiser_node import optimise_script
from nodes.pdf_node import generate_script_pdf, convert_to_latex, compile_pdf
from nodes.media_node import generate_images, generate_audio
from nodes.video_node import create_video
from routing.router import route_step, route_evaluation


# Build the graph
builder = StateGraph(AgentState)

# === ORIGINAL NODES (kept for backward compatibility) ===
builder.add_node("generate_script", generate_script)  # Base script generation
builder.add_node("generate_outline", generate_outline)
builder.add_node("generate_script_pdf", generate_script_pdf)

# === QUALITY CONTROL NODES (NEW) ===
builder.add_node("evaluator", evaluate_quality)
builder.add_node("optimiser", optimise_script)

# Phase 2: PDF
builder.add_node("convert_to_latex", convert_to_latex)
builder.add_node("compile_pdf", compile_pdf)
builder.add_node("generate_images", generate_images)

# Phase 3: Video
builder.add_node("generate_audio", generate_audio)
builder.add_node("create_video", create_video)


# Routing
builder.add_conditional_edges(START, route_step, {
    "outline": "generate_outline",
    "script": "generate_script",
    "pdf": "convert_to_latex",
    "video": "generate_audio"
})

builder.add_edge("generate_outline", END)


# Script generation -> Evaluator
builder.add_edge("generate_script", "evaluator")

# === EVALUATION LOOP ===
builder.add_conditional_edges("evaluator", route_evaluation, {
    "proceed": "generate_script_pdf",
    "optimise": "optimiser"
})
builder.add_edge("optimiser", "evaluator") # Loop back to check quality again

builder.add_edge("generate_script_pdf", END)

# Phase 2: Images + LaTeX
builder.add_edge("generate_images", "convert_to_latex")
builder.add_edge("convert_to_latex", "compile_pdf")
builder.add_edge("compile_pdf", END)

# Phase 3: Video
builder.add_edge("generate_audio", "create_video")
builder.add_edge("create_video", END)

graph = builder.compile()
