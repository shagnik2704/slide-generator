"""Admin compliance orchestration."""

import re
from typing import Any, Dict, List, Optional

from src.compliance.policies.admin_script_v1 import ADMIN_SCRIPT_POLICY_V1
from src.compliance.report import build_report
from src.compliance.schemas import ScriptArtifact, ScriptField, ScriptRow
from src.compliance.validators.deterministic import run_deterministic_validators
from src.compliance.validators.semantic import run_semantic_validators


URL_PATTERN = r"https?://[^\s<>\"{}|\\^`\[\]'()]+"


async def run_admin_script_compliance(
    json_script: dict,
    tutorial_type: Optional[str] = None,
    source_artifact: Optional[dict] = None,
) -> dict:
    artifact = build_script_artifact(json_script, tutorial_type=tutorial_type, source_artifact=source_artifact)
    det_checks, det_issues = run_deterministic_validators(ADMIN_SCRIPT_POLICY_V1, artifact)
    sem_checks, sem_issues = await run_semantic_validators(ADMIN_SCRIPT_POLICY_V1, artifact)
    report = build_report(ADMIN_SCRIPT_POLICY_V1, artifact, det_checks + sem_checks, det_issues + sem_issues)
    return report.model_dump()


def build_script_artifact(json_script: dict, tutorial_type: Optional[str] = None, source_artifact: Optional[dict] = None) -> ScriptArtifact:
    slides = json_script.get("slides") or []
    source_artifact = source_artifact or {}
    rows: List[ScriptRow] = []

    for index, slide in enumerate(slides, 1):
        visual = str(slide.get("image_prompt") or slide.get("visual_cue") or "")
        narration = str(slide.get("narration") or "")
        title = str(slide.get("title") or slide.get("slide_type") or "")
        row_text = "\n".join([title, visual, narration])
        rows.append(ScriptRow(
            row_id=f"row_{index:03d}",
            row_number=index,
            title=title,
            slide_type=_detect_slide_type(row_text, index, len(slides)),
            visual_cue=ScriptField(text=visual, hyperlinks=_extract_urls(visual)),
            narration=ScriptField(text=narration, hyperlinks=_extract_urls(narration)),
        ))

    hyperlinks = []
    hyperlinks.extend(source_artifact.get("hyperlinks") or [])
    for row in rows:
        hyperlinks.extend(row.visual_cue.hyperlinks)
        hyperlinks.extend(row.narration.hyperlinks)

    metadata = {
        "presentation_title": json_script.get("presentation_title") or json_script.get("title"),
        "title": json_script.get("title") or json_script.get("presentation_title"),
        "domain": json_script.get("domain"),
        "module": json_script.get("module"),
        "tutorial": json_script.get("tutorial"),
        "duration": json_script.get("duration"),
        "learning_objectives": json_script.get("learning_objectives") or [],
        "prerequisites": json_script.get("prerequisites"),
        "keywords": json_script.get("keywords") or json_script.get("meta_tags") or [],
        "meta_tags": json_script.get("meta_tags") or json_script.get("keywords") or [],
        "outline": json_script.get("outline") or [],
    }
    detected_sections = _detect_sections(rows, metadata)
    return ScriptArtifact(
        metadata=metadata,
        rows=rows,
        hyperlinks=sorted(set(url for url in hyperlinks if url)),
        detected_sections=detected_sections,
        tutorial_type=tutorial_type,
    )


def _detect_sections(rows: List[ScriptRow], metadata: Dict[str, Any]) -> List[str]:
    sections = set()
    if metadata.get("learning_objectives"):
        sections.add("objectives")
    if metadata.get("prerequisites"):
        sections.add("prerequisites")
    for row in rows:
        text = _plain("\n".join([row.title, row.visual_cue.text, row.narration.text])).lower()
        if "learning objective" in text or "we will learn" in text:
            sections.add("objectives")
        if _is_prerequisite_slide(text):
            sections.add("prerequisites")
        if "system requirement" in text or "to record this tutorial" in text:
            sections.add("system_requirements")
        if _is_resource_file_slide(text):
            sections.add("resource_files")
        if "disclaimer" in text or "ai tools constantly evolve" in text or "conversational ai chatbot" in text:
            sections.add("disclaimer")
        if "summary" in text or "in this tutorial, we learnt" in text or "recap" in text:
            sections.add("summary")
        if "assignment" in text or "practice" in text or "we encourage you" in text:
            sections.add("assignment")
        if "acknowledgement" in text:
            sections.add("acknowledgement")
        if "closing slide" in text or "thank you" in text or "thanks for joining" in text:
            sections.add("closing")
    order = ["objectives", "prerequisites", "system_requirements", "resource_files", "disclaimer", "summary", "assignment", "acknowledgement", "closing"]
    return [section for section in order if section in sections]


def _detect_slide_type(text: str, index: int, total: int) -> str:
    value = _plain(text).lower()
    if "learning objective" in value or "we will learn" in value:
        return "learning_objectives"
    if "system requirement" in value:
        return "system_requirements"
    if _is_resource_file_slide(value):
        return "resource_files"
    if _is_prerequisite_slide(value):
        return "prerequisites"
    if "disclaimer" in value or "ai tools constantly evolve" in value or "conversational ai chatbot" in value:
        return "disclaimer"
    if "summary" in value or "in this tutorial, we learnt" in value:
        return "summary"
    if "assignment" in value or "we encourage you" in value:
        return "assignment"
    if "acknowledgement" in value:
        return "acknowledgement"
    if "closing slide" in value or (index == total and ("thank you" in value or not value.strip())):
        return "closing"
    if index == 1 or "title slide" in value:
        return "title"
    return "content"


def _extract_urls(text: str) -> List[str]:
    return re.findall(URL_PATTERN, text or "")


def _is_resource_file_slide(text: str) -> bool:
    value = text.lower()
    file_terms = ("code file", "resource file", "data file", "sample file", "exercise file")
    setup_terms = ("required", "download", "practice this tutorial", "provided")
    return any(term in value for term in file_terms) and any(term in value for term in setup_terms)


def _is_prerequisite_slide(text: str) -> bool:
    value = re.sub(r"[\u2010-\u2015\u2212]", "-", text.lower())
    prerequisite_patterns = (
        r"\bpre[\s-]*(?:requisit|requist)e?s?\b",
        r"\bpre[\s-]*reqs?\b",
    )
    return (
        any(re.search(pattern, value) for pattern in prerequisite_patterns)
        or "to follow this tutorial" in value
    )


def _plain(text: str) -> str:
    return re.sub(r"\*\*([^*]+)\*\*", r"\1", text or "")
