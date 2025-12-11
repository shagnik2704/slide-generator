"""
Main agent workflow for the slide generator.
All business logic has been modularized into separate files.

4-NODE PIPELINE:
  Stage 1: generate_structure - Parse outline, create metadata + slide skeleton
  Stage 2: expand_narration - Expand skeleton to full narration
  Stage 3: generate_visuals - Add image prompts based on narration
  Stage 4: evaluator - Quality checks + optimization loop
"""
from langgraph.graph import StateGraph, START, END
from models.state import AgentState

# === 4-NODE PIPELINE IMPORTS ===
from nodes.structure_node import generate_structure
from nodes.narration_node import expand_narration
from nodes.visuals_node import generate_visuals
from nodes.type_detector import detect_tutorial_type

# === QUALITY CONTROL ===
from nodes.evaluator_node import evaluate_quality
from nodes.optimiser_node import optimise_script

# === PDF GENERATION ===
from nodes.pdf_node import generate_script_pdf, convert_to_latex, compile_pdf

# === MEDIA GENERATION ===
from nodes.media_node import generate_images, generate_audio
from nodes.video_node import create_video
from nodes.slide_content_node import generate_slide_content

# === ROUTING ===
from routing.router import route_step, route_evaluation


# Build the graph
builder = StateGraph(AgentState)

# === 5-NODE SCRIPT GENERATION PIPELINE ===
builder.add_node("detect_type", detect_tutorial_type)         # Stage 0: Detect tutorial type
builder.add_node("generate_structure", generate_structure)    # Stage 1
builder.add_node("expand_narration", expand_narration)        # Stage 2
builder.add_node("generate_visuals", generate_visuals)        # Stage 3
builder.add_node("generate_script_pdf", generate_script_pdf)

# === QUALITY CONTROL NODES ===
builder.add_node("evaluator", evaluate_quality)
builder.add_node("optimiser", optimise_script)

# === PHASE 2: PDF - Slide Content + Images + LaTeX ===
builder.add_node("generate_slide_content", generate_slide_content)
builder.add_node("convert_to_latex", convert_to_latex)
builder.add_node("compile_pdf", compile_pdf)
builder.add_node("generate_images", generate_images)

# === PHASE 3: Video ===
builder.add_node("generate_audio", generate_audio)
builder.add_node("create_video", create_video)


# === ROUTING ===
builder.add_conditional_edges(START, route_step, {
    "script": "detect_type",  # Now starts with type detection
    "pdf": "generate_slide_content",
    "video": "generate_audio"
})


# === 5-NODE PIPELINE EDGES ===
# Type Detection -> Stage 1 -> Stage 2 -> Stage 3 -> Evaluator
builder.add_edge("detect_type", "generate_structure")
builder.add_edge("generate_structure", "expand_narration")
builder.add_edge("expand_narration", "generate_visuals")
builder.add_edge("generate_visuals", "evaluator")

# === EVALUATION LOOP ===
builder.add_conditional_edges("evaluator", route_evaluation, {
    "proceed": "generate_script_pdf",
    "optimise": "optimiser"
})
builder.add_edge("optimiser", "evaluator")
builder.add_edge("generate_script_pdf", END)

# === PHASE 2: Slide Content -> Images -> LaTeX -> PDF ===
builder.add_edge("generate_slide_content", "generate_images")
builder.add_edge("generate_images", "convert_to_latex")
builder.add_edge("convert_to_latex", "compile_pdf")
builder.add_edge("compile_pdf", END)

# === PHASE 3: Video ===
builder.add_edge("generate_audio", "create_video")
builder.add_edge("create_video", END)

# Compile graph (no checkpointer)
graph = builder.compile()

