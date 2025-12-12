"""Pydantic models for API requests and responses."""
from pydantic import BaseModel
from typing import List, Union, Optional


class SlideContentItem(BaseModel):
    type: str
    items: Optional[List[str]] = None


class Slide(BaseModel):
    id: str
    type: str
    title: str
    content: List[Union[str, dict]]


class GenerateScriptRequest(BaseModel):
    outline: str  # User must provide outline
    title: Optional[str] = None
    target_audience: Optional[str] = None
    mode: Optional[str] = "script_only"


class GenerateVideoRequest(BaseModel):
    json_script: dict
    pdf_path: Optional[str] = None


class GenerateSlidesRequest(BaseModel):
    json_script: dict
