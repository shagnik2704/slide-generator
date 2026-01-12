"""
Data models for the slide generator agent.
Contains TypedDict and Pydantic model definitions.
"""
from typing import TypedDict, Optional, List, Literal
from pydantic import BaseModel, Field


class Slide(TypedDict):
    type: str
    title: str
    content: List[str]
    narration: List[str]
    image_prompt: str
    image_path: Optional[str]


# === INTERMEDIATE SCHEMAS FOR 4-NODE PIPELINE ===

class SlideSkeleton(BaseModel):
    """Stage 1 output: Slide skeleton with notes (no narration yet)."""
    title: Optional[str] = Field(description="Slide title, or null for flow slides")
    notes: str = Field(description="1-2 sentence content summary")
    slide_type: Literal["boilerplate", "section_header", "content", "demo"] = Field(
        description="Type of slide for routing logic"
    )


class StructuredOutline(BaseModel):
    """Stage 1 output: Complete structured outline with metadata."""
    presentation_title: str = Field(description="Title of the presentation")
    module: str = Field(description="Module name")
    episode: str = Field(description="Episode number/name")
    learning_objectives: List[str] = Field(description="3-4 learning objectives")
    duration: str = Field(default="3-4 min", description="Tutorial duration")
    meta_tags: List[str] = Field(description="Keywords for searchability")
    prerequisites: str = Field(description="Pre-requisite knowledge")
    outline: List[str] = Field(description="Content topics only")
    slides: List[SlideSkeleton] = Field(description="Slide skeleton list")


class SlideWithNarration(BaseModel):
    """Stage 2 output: Slide with narration but no visuals yet."""
    title: Optional[str] = Field(description="Slide title")
    narration: str = Field(description="Full narration text")
    slide_type: str = Field(description="Type of slide")


class NarrationScript(BaseModel):
    """Stage 2 output: Script with narration for all slides."""
    presentation_title: str
    module: str
    episode: str
    learning_objectives: List[str]
    duration: str
    meta_tags: List[str]
    prerequisites: str
    outline: List[str]
    slides: List[SlideWithNarration]


# === AGENT STATE ===

class AgentState(TypedDict):
    topic: str
    project_id: Optional[int]
    outline: Optional[str]
    mode: str
    tutorial_type: Optional[str]  # "conceptual" or "demo"
    # Outline processor outputs
    outline_valid: Optional[bool]           # Whether outline is usable
    outline_topics: Optional[List[str]]     # Extracted topics
    outline_suggested_title: Optional[str]  # Suggested title
    outline_rejection: Optional[str]        # Why rejected (if invalid)
    # NEW PIPELINE: Stage outputs
    metadata: Optional[dict]           # ScriptMetadata from metadata_node
    boilerplate_slides: Optional[List[dict]]  # 7 boilerplate slides from boilerplate_node
    content_slides: Optional[List[dict]]      # Content slides from content_node
    # Legacy intermediate states (for backward compatibility)
    structured_outline: Optional[dict]  
    narration_script: Optional[dict]
    # Final output
    json_script: dict
    script_pdf_path: Optional[str]
    slides_pdf_path: Optional[str]
    pdf_path: Optional[str]
    image_paths: List[str]
    latex_content: Optional[str]
    audio_map: dict
    video_path: Optional[str]
    evaluation_iteration: int
    evaluation_passed: bool
    evaluation_feedback: Optional[str]
    problematic_slides: List[int]  # Slide indices that need fixing


# === FINAL OUTPUT SCHEMAS (existing) ===

class SlideModel(BaseModel):
    type: str = Field(description="Type of slide: 'title_slide' or 'content_slide'")
    title: str = Field(description="Title of the slide")
    content: List[str] = Field(description="List of bullet points or text content")
    narration: List[str] = Field(description="List of narration segments")
    image_prompt: str = Field(description="Prompt for generating an image")
    video_prompt: Optional[str] = Field(description="Prompt for generating a video (if is_video_slide is True)")
    is_video_slide: bool = Field(default=False, description="Whether this slide should have a video background instead of an image")


class Presentation(BaseModel):
    presentation_title: str = Field(description="Title of the entire presentation")
    module: str = Field(description="Module name or number")
    episode: str = Field(description="Episode number or name")
    learning_objectives: List[str] = Field(description="List of learning objectives")
    duration: str = Field(description="Approximate duration (e.g., '3-4 min')")
    outline: List[str] = Field(description="List of main topics covered")
    meta_tags: List[str] = Field(description="Keywords/tags for searchability")
    prerequisites: str = Field(description="Pre-requisite tutorials or knowledge")
    slides: List[SlideModel] = Field(description="List of slides")

