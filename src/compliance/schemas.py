"""Schemas for evidence-based admin compliance."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


Severity = Literal["blocker", "major", "minor", "advisory"]
ValidatorKind = Literal["deterministic", "semantic", "derived"]
CheckStatus = Literal["passed", "failed", "skipped"]


class PolicyCriterion(BaseModel):
    id: str
    criteria: str
    category: str
    severity: Severity = "major"
    validator: ValidatorKind


class Policy(BaseModel):
    id: str
    version: str
    criteria: List[PolicyCriterion]


class ScriptField(BaseModel):
    text: str = ""
    hyperlinks: List[str] = Field(default_factory=list)


class ScriptRow(BaseModel):
    row_id: str
    row_number: int
    title: str = ""
    slide_type: str = "content"
    visual_cue: ScriptField = Field(default_factory=ScriptField)
    narration: ScriptField = Field(default_factory=ScriptField)


class ScriptArtifact(BaseModel):
    metadata: Dict[str, Any] = Field(default_factory=dict)
    rows: List[ScriptRow] = Field(default_factory=list)
    hyperlinks: List[str] = Field(default_factory=list)
    detected_sections: List[str] = Field(default_factory=list)
    tutorial_type: Optional[str] = None


class Evidence(BaseModel):
    row_id: Optional[str] = None
    row_number: Optional[int] = None
    field: Optional[Literal["visual_cue", "narration", "metadata", "script"]] = None
    text: str = ""
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    reason: Optional[str] = None
    length: Optional[int] = None


class ComplianceIssue(BaseModel):
    id: str
    criteria_id: str
    severity: Severity
    status: Literal["failed"] = "failed"
    message: str
    evidence: List[Evidence] = Field(default_factory=list)
    suggested_action: str = ""


class CheckResult(BaseModel):
    id: str
    criteria: str
    ai_review: Optional[bool]
    ai_notes: str
    human_review: Optional[str] = None
    severity: Severity
    validator: ValidatorKind
    issues: List[str] = Field(default_factory=list)


class ComplianceReport(BaseModel):
    checks: List[CheckResult]
    summary: Dict[str, int]
    issues: List[ComplianceIssue]
    annotations: Dict[str, List[str]]
    policy: Dict[str, Any]
    artifact_summary: Dict[str, Any]


class SemanticEvidence(BaseModel):
    row_number: Optional[int] = None
    field: Optional[Literal["visual_cue", "narration", "metadata", "script"]] = None
    text: str = ""
    reason: Optional[str] = None


class SemanticCheckResult(BaseModel):
    criteria_id: str
    passed: bool
    notes: str
    evidence: List[SemanticEvidence] = Field(default_factory=list)
    suggested_action: str = ""


class SemanticBatchResult(BaseModel):
    checks: List[SemanticCheckResult]
