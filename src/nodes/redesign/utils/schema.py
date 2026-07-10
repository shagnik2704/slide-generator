from pydantic import BaseModel
from typing import TypedDict, List

class Link(BaseModel):
    name:str
    url:str

class TutorialData(BaseModel):
    foss_name: str
    language: str = "English"
    links: list[Link]

class OldTutorial(BaseModel):
    outline: str = None
    duration: float = None

class UpdatedTutorial(BaseModel):
    updated_subtopics: str = None
    logs: list[str] = None

class SplitedTutorial(BaseModel):
    tutorial_title: str
    subtopic: str
    estimated_duration: float

class SplitedTutorialList(BaseModel):
    tutorials: list[SplitedTutorial]

class TutorialState(BaseModel):
    tutorial_name: str
    tutorial_link: str
    old_tutorial: OldTutorial
    updated_tutorial: UpdatedTutorial
    splited_tutorial: list[SplitedTutorial]

class SharedAgentState(BaseModel):
    data: TutorialData
    output_csv_path: str | None = None
    tutorial: TutorialState | None = None


class ShareTutorialRequest(BaseModel):
    url: str
    recipients: list[dict]  # [{"email": str, "role": str}]

class TutorialResponse(BaseModel):
    status: str
    url: str
    response: dict

class GenerateTutorialRequest(BaseModel):
    foss_name: str
    language: str
    export: bool = True
    reciept_emails: list[str] = []
    reciept_role: str = "writer"

class GenerateTutorialResponse(BaseModel):
    status: str
    url: str


class ShareTutorialResponse(BaseModel):
    status: str
    message: str