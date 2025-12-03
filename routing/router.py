"""
Routing logic for the agent workflow.
"""
from models.state import AgentState


def route_evaluation(state: AgentState):
    """Routes based on evaluation results."""
    passed = state.get('evaluation_passed', False)
    iteration = state.get('evaluation_iteration', 0)
    max_iterations = 5
    
    if passed:
        return "proceed"
    elif iteration >= max_iterations:
        print(f"⚠ Max evaluation iterations ({max_iterations}) reached.")
        return "proceed"
    else:
        print(f"↺ Optimising script (Iteration {iteration})...")
        return "optimise"

def route_step(state: AgentState):
    mode = state.get("mode", "script_only")
    
    print(f"DEBUG: route_step mode={mode}")
    
    if mode == "slides_only":
        return "pdf"
        
    elif mode == "video_production":
        return "video"
        
    elif mode == "outline_only":
        return "outline"
        
    if state.get("outline"):
        return "script"
        
    return "script"
