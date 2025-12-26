"""Pydantic models for outline chat."""
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str  # "user" or "assistant"
    content: str


class TutorialRow(BaseModel):
    """Single tutorial row in the course outline table."""
    tutorial_number: int
    title: str
    prerequisites: List[str] = Field(default_factory=list, description="List of prerequisites for this tutorial")
    topics_details: List[str] = Field(description="List of demonstrable steps")
    time_seconds: int
    comments: str = ""


class CourseOutlineData(BaseModel):
    """Complete Course Outline data structure matching the template."""
    outline_type: str = "FOSS"  # "FOSS", "ICT", or "OTHER"
    platform_name: str = ""     # Name of FOSS software / ICT platform / Other
    os_version: str = ""        # Compatible operating system name + version
    outline_name: str = ""      # Name of the course outline (how it should appear to learners)
    foss_version: str = "Not Applicable"
    target_audience: str = ""
    entry_behaviour: str = ""
    purpose: str = ""
    recommended_no_of_tutorials: int = 0
    prepared_by: str = ""
    domain: str = ""
    reviewer: str = "IITB ST Team"
    date: str = ""
    keywords: List[str] = []
    about_course: str = ""
    course_objectives: List[str] = []
    topics_included: List[str] = []
    topics_not_included: List[str] = []
    core_example: str = ""
    allied_examples: List[str] = []
    tutorial_rows: List[TutorialRow] = []


class ConversationPhase(str, Enum):
    """Tracks which phase of the interview we're in."""
    WARMUP = "warmup"  # Phase A
    OUTCOMES = "outcomes"  # Phase B
    EXAMPLES = "examples"  # Phase C
    STRUCTURE = "structure"  # Phase D
    METADATA = "metadata"  # Phase E
    REVIEW = "review"
    APPROVED = "approved"


class OutlineChatRequest(BaseModel):
    """Request model for outline chat."""
    conversation: List[ChatMessage]
    outline_data: Optional[Dict] = None
    project_id: Optional[int] = None
    phase: Optional[str] = None


class OutlineChatResponse(BaseModel):
    """Response model for outline chat."""
    project_id: int
    assistant_message: str
    follow_up_question: Optional[str] = None
    phase: str
    outline_data: Dict
    validation_errors: List[str] = []
    pedagogy_compliance: Dict = {}
    is_draft_ready: bool = False
    is_approved: bool = False

