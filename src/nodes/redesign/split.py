from typing import List, Optional, Dict, Any, TypedDict
import json
import logging
from src.nodes.redesign.utils.schema import TutorialState, SplitedTutorialList, SplitedTutorial
from src.nodes.redesign.utils.config import llm
from src.nodes.redesign.utils.prompts import (
    SPLIT_AGENT_PROMPT3,
    REASONING_AGENT_PROMPT,
    SPLIT_REVISION_INSTRUCTION
)
from src.nodes.redesign.validate_split import validate_tutorial_split
from langgraph.graph import StateGraph, START, END

logger = logging.getLogger(__name__)

# Define Workflow State
class SplitWorkflowState(TypedDict):
    # Inputs
    updated_subtopics: str
    total_duration: float
    number_of_tutorials: int
    
    # Outputs/Internal state
    splited_tutorial: List[SplitedTutorial]
    validation_issues: List[str]
    reasoning_feedback: Optional[str]
    iterations: int

# Initialize LLM with structured output for the Planning Agent
planning_llm = llm.with_structured_output(SplitedTutorialList)

def serialize_tutorials(tutorials: List[Any]) -> str:
    """Helper to safely serialize SplitedTutorial list for prompting."""
    serialized = []
    for t in tutorials:
        if hasattr(t, "model_dump"):
            serialized.append(t.model_dump())
        elif hasattr(t, "dict"):
            serialized.append(t.dict())
        elif isinstance(t, dict):
            serialized.append(t)
        else:
            serialized.append({
                "tutorial_title": getattr(t, "tutorial_title", ""),
                "subtopic": getattr(t, "subtopic", ""),
                "estimated_duration": getattr(t, "estimated_duration", 0.0)
            })
    return json.dumps(serialized, indent=2)

def planning_agent(state: SplitWorkflowState) -> Dict[str, Any]:
    iterations = state.get("iterations", 0)
    logger.info(f"[split_workflow] planning_agent: Starting planning. Iteration: {iterations}")
    
    # Construct initial payload
    payload = {
        "updated_subtopics": state["updated_subtopics"],
        "duration": state["total_duration"],
        "number_of_tutorials": state["number_of_tutorials"]
    }
    
    messages = [
        ("system", SPLIT_AGENT_PROMPT3),
        ("user", json.dumps(payload))
    ]
    
    # If reasoning feedback exists, append the revision instruction
    if state.get("reasoning_feedback") and state.get("splited_tutorial"):
        logger.info(f"[split_workflow] planning_agent: Appending reasoning feedback from previous iteration to prompt.")
        failed_split_repr = serialize_tutorials(state["splited_tutorial"])
        
        revision_instruction = SPLIT_REVISION_INSTRUCTION.format(
            failed_split=failed_split_repr,
            validation_issues="\n".join(f"- {issue}" for issue in state["validation_issues"]),
            reasoning_feedback=state["reasoning_feedback"]
        )
        messages.append(("user", revision_instruction))
        
    response = planning_llm.invoke(messages)
    logger.info(f"[split_workflow] planning_agent: Generated {len(response.tutorials)} tutorials.")
    
    return {
        "splited_tutorial": response.tutorials
    }

def validate_split(state: SplitWorkflowState) -> Dict[str, Any]:
    logger.info("[split_workflow] validate_split: Validating split tutorials...")
    tutorial_list = SplitedTutorialList(
        tutorials=state["splited_tutorial"],
        total_duration=state["total_duration"]
    )
    validation_res = validate_tutorial_split(tutorial_list)
    
    if validation_res.is_valid:
        logger.info("[split_workflow] validate_split: Validation succeeded. Split is valid!")
    else:
        logger.warning(f"[split_workflow] validate_split: Validation failed with issues: {validation_res.issues}")
        
    return {
        "validation_issues": validation_res.issues
    }

def reasoning_agent(state: SplitWorkflowState) -> Dict[str, Any]:
    logger.info(f"[split_workflow] reasoning_agent: Analysing issues for iteration: {state['iterations']}")
    failed_split_repr = serialize_tutorials(state["splited_tutorial"])
    
    prompt_payload = {
        "original_subtopics": state["updated_subtopics"],
        "original_duration": state["total_duration"],
        "expected_tutorials": state["number_of_tutorials"],
        "failed_split": failed_split_repr,
        "validation_errors": "\n".join(f"- {issue}" for issue in state["validation_issues"])
    }
    
    messages = [
        ("system", REASONING_AGENT_PROMPT),
        ("user", json.dumps(prompt_payload))
    ]
    
    response = llm.invoke(messages)
    logger.info("[split_workflow] reasoning_agent: Formulated critique and revision guidance.")
    
    return {
        "reasoning_feedback": response.content,
        "iterations": state["iterations"] + 1
    }

def should_continue(state: SplitWorkflowState):
    if not state.get("validation_issues"):
        logger.info("[split_workflow] should_continue: Split is valid. Routing to END.")
        return END
    
    iterations = state.get("iterations", 0)
    if iterations >= 3:
        logger.warning(f"[split_workflow] should_continue: Maximum iterations ({iterations}) reached. Routing to END with current split.")
        return END
        
    logger.info(f"[split_workflow] should_continue: Split is invalid (Iteration {iterations}). Routing to reasoning_agent.")
    return "reasoning_agent"

# Build Graph
builder = StateGraph(SplitWorkflowState)
builder.add_node("planning_agent", planning_agent)
builder.add_node("validate_split", validate_split)
builder.add_node("reasoning_agent", reasoning_agent)

builder.add_edge(START, "planning_agent")
builder.add_edge("planning_agent", "validate_split")
builder.add_conditional_edges(
    "validate_split",
    should_continue,
    {
        "reasoning_agent": "reasoning_agent",
        END: END
    }
)
builder.add_edge("reasoning_agent", "planning_agent")

workflow = builder.compile()

def duration_split(state: TutorialState) -> TutorialState:
    logger.info(f"Starting LangGraph duration split workflow for {state.tutorial_name}")
    number_of_tutorials = round(state.old_tutorial.duration / 210)  # Assuming 4 minutes (210 seconds) per tutorial
    
    initial_state = {
        "updated_subtopics": state.updated_tutorial.updated_subtopics,
        "total_duration": state.old_tutorial.duration,
        "number_of_tutorials": number_of_tutorials,
        "splited_tutorial": [],
        "validation_issues": [],
        "reasoning_feedback": None,
        "iterations": 0
    }
    
    final_state = workflow.invoke(initial_state)
    logger.info(f"LangGraph duration split workflow completed for {state.tutorial_name}")
    
    state.splited_tutorial = final_state["splited_tutorial"]
    return state