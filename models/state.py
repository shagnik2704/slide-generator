"""
Data models for the slide generator agent.
Contains TypedDict and Pydantic model definitions.
"""
from typing import TypedDict, Optional, List
from langchain_core.pydantic_v1 import BaseModel, Field


class Slide(TypedDict):
    type: str
    title: str
    content: List[str]
    narration: List[str]
    image_prompt: str
    image_path: Optional[str]


class AgentState(TypedDict):
    topic: str
    project_id: Optional[int]
    outline: Optional[str]
    mode: str
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
