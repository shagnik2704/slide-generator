from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


Stage = Literal[
    "grounding",
    "grounding_edit",
    "metadata",
    "metadata_edit",
    "generate",
    "edit",
    "compliance",
    "done",
    "error",
]
ResumeAction = Literal["approve", "edit"]
EditableScriptField = Literal["narration", "visual_cue"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IngestResult(StrictModel):
    foss_name: Optional[str] = Field(
        default=None,
        description="The FOSS/tool taught by the outline, or null if none is clear.",
    )


class GroundingReport(StrictModel):
    validated_content: str = Field(
        description="The outline after technical corrections, preserving useful detail."
    )
    corrections_made: list[str] = Field(
        description="Specific technical corrections made to the outline."
    )
    warnings: list[str] = Field(
        description="Technical concerns, deprecations, or uncertainty to surface to the user."
    )
    is_mostly_correct: bool = Field(
        description="Whether the outline is mostly technically correct after validation."
    )
    error: Optional[str] = Field(default=None, description="System error, if validation failed.")


class ScriptMetadata(StrictModel):
    title: str
    learning_objectives: list[str] = Field(min_length=1)
    prerequisites: str
    system_requirements: str
    outline_topics: list[str] = Field(min_length=1)
    meta_tags: list[str] = Field(min_length=1)

    @field_validator("learning_objectives", "outline_topics", "meta_tags")
    @classmethod
    def require_items(cls, value: list[str]) -> list[str]:
        items = [item.strip() for item in value if item and item.strip()]
        if not items:
            raise ValueError("At least one non-empty item is required")
        return items


class ScriptSlide(StrictModel):
    slide_number: int = Field(ge=1)
    slide_type: str
    visual_cue: str
    narration: str


class ScriptResult(StrictModel):
    message: str
    script: list[ScriptSlide] = Field(min_length=1)


def dump_model(model: BaseModel) -> dict:
    return model.model_dump()


def dump_models(models: list[BaseModel]) -> list[dict]:
    return [model.model_dump() for model in models]


def parse_metadata(value: dict) -> ScriptMetadata:
    return ScriptMetadata.model_validate(value)


def parse_script(value: list[dict]) -> list[ScriptSlide]:
    return [ScriptSlide.model_validate(slide) for slide in value]
