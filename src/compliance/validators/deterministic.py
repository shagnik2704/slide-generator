"""Deterministic admin compliance validators."""

import re
from typing import Iterable, List, Tuple

import httpx

from src.compliance.schemas import (
    CheckResult,
    ComplianceIssue,
    Evidence,
    Policy,
    PolicyCriterion,
    ScriptArtifact,
    ScriptRow,
)


SKIP_LENGTH_SECTIONS = {
    "title",
    "learning_objectives",
    "system_requirements",
    "prerequisites",
    "resource_files",
    "disclaimer",
    "summary",
    "assignment",
    "closing",
    "acknowledgement",
}


def run_deterministic_validators(policy: Policy, artifact: ScriptArtifact) -> Tuple[List[CheckResult], List[ComplianceIssue]]:
    checks: List[CheckResult] = []
    issues: List[ComplianceIssue] = []
    issue_counter = 1

    def criterion(criteria_id: str) -> PolicyCriterion:
        return next(c for c in policy.criteria if c.id == criteria_id)

    def add_issue(criteria_id: str, message: str, evidence: List[Evidence], suggested_action: str = "") -> ComplianceIssue:
        nonlocal issue_counter
        c = criterion(criteria_id)
        issue = ComplianceIssue(
            id=f"det_{issue_counter:03d}",
            criteria_id=criteria_id,
            severity=c.severity,
            message=message,
            evidence=evidence,
            suggested_action=suggested_action,
        )
        issue_counter += 1
        issues.append(issue)
        return issue

    def add_check(criteria_id: str, passed: bool, notes: str, issue_ids: List[str] | None = None) -> None:
        c = criterion(criteria_id)
        checks.append(CheckResult(
            id=criteria_id,
            criteria=c.criteria,
            ai_review=passed,
            ai_notes=notes,
            severity=c.severity,
            validator=c.validator,
            issues=issue_ids or [],
        ))

    rows = artifact.rows

    _two_column_format(add_check, add_issue, rows)
    _required_metadata(add_check, add_issue, artifact)
    _section_presence("learning_objectives_present", "objectives", add_check, add_issue, artifact)
    _section_presence("prerequisites_present", "prerequisites", add_check, add_issue, artifact)
    _duration_compliance(add_check, add_issue, artifact)
    _row_granularity(add_check, add_issue, rows)
    _sentence_hard_limit(add_check, add_issue, rows)
    _sentence_soft_target(add_check, add_issue, rows)
    _one_sentence_per_line(add_check, add_issue, rows)
    _links_active(add_check, add_issue, artifact)
    _section_presence("recap_summary_present", "summary", add_check, add_issue, artifact)
    _section_presence("assignment_present", "assignment", add_check, add_issue, artifact)
    _closing_present(add_check, add_issue, artifact)

    return checks, issues


def _two_column_format(add_check, add_issue, rows: List[ScriptRow]) -> None:
    issue_ids = []
    if not rows:
        issue = add_issue("two_column_format", "No script rows were found.", [Evidence(field="script", text="")], "Use a two-column Visual Cue and Narration table.")
        issue_ids.append(issue.id)
    else:
        missing = [
            Evidence(row_id=r.row_id, row_number=r.row_number, field="script", text="", reason="Row is missing both visual cue and narration.")
            for r in rows
            if not r.visual_cue.text.strip() and not r.narration.text.strip()
        ]
        if missing:
            issue = add_issue("two_column_format", f"{len(missing)} row(s) are empty.", missing[:5], "Remove empty rows or fill both script columns.")
            issue_ids.append(issue.id)
    add_check("two_column_format", not issue_ids, "Script rows use Visual Cue and Narration fields." if not issue_ids else "Some rows do not preserve the expected two-column script structure.", issue_ids)


def _required_metadata(add_check, add_issue, artifact: ScriptArtifact) -> None:
    metadata = artifact.metadata
    required = {
        "title": metadata.get("presentation_title") or metadata.get("title"),
        "domain/module": metadata.get("domain") or metadata.get("module"),
        "duration": metadata.get("duration"),
        "prerequisites": metadata.get("prerequisites"),
        "keywords": metadata.get("keywords") or metadata.get("meta_tags"),
        "outline": metadata.get("outline"),
    }
    missing = [name for name, value in required.items() if not _has_value(value)]
    if missing:
        issue = add_issue(
            "required_metadata_present",
            f"Missing metadata: {', '.join(missing)}.",
            [Evidence(field="metadata", text=", ".join(missing), reason="Required metadata field is empty or unavailable.")],
            "Complete the script metadata table before review.",
        )
        add_check("required_metadata_present", False, issue.message, [issue.id])
    else:
        add_check("required_metadata_present", True, "Required metadata is present.")


def _section_presence(criteria_id: str, section: str, add_check, add_issue, artifact: ScriptArtifact) -> None:
    if section in artifact.detected_sections:
        add_check(criteria_id, True, f"{section.replace('_', ' ').title()} section detected.")
        return
    issue = add_issue(
        criteria_id,
        f"No {section.replace('_', ' ')} section was detected.",
        [Evidence(field="script", text="", reason=f"Detected sections: {', '.join(artifact.detected_sections) or 'none'}.")],
        f"Add a clear {section.replace('_', ' ')} section.",
    )
    add_check(criteria_id, False, issue.message, [issue.id])


def _closing_present(add_check, add_issue, artifact: ScriptArtifact) -> None:
    if {"closing", "acknowledgement"} & set(artifact.detected_sections):
        add_check("closing_acknowledgement_present", True, "Closing or acknowledgement section detected.")
        return
    issue = add_issue(
        "closing_acknowledgement_present",
        "No closing or acknowledgement section was detected.",
        [Evidence(field="script", text="", reason=f"Detected sections: {', '.join(artifact.detected_sections) or 'none'}.")],
        "Add the required closing and acknowledgement content.",
    )
    add_check("closing_acknowledgement_present", False, issue.message, [issue.id])


def _duration_compliance(add_check, add_issue, artifact: ScriptArtifact) -> None:
    duration_text = str(artifact.metadata.get("duration") or "")
    minutes = _parse_duration_minutes(duration_text)
    if minutes is None:
        words = sum(len(_plain_text(row.narration.text).split()) for row in artifact.rows)
        minutes = words / 130 if words else None
        duration_text = f"estimated from {words} narration words"

    if minutes is None:
        issue = add_issue("duration_compliance", "Duration could not be estimated.", [Evidence(field="metadata", text=duration_text)], "Add duration metadata or provide a recording duration.")
        add_check("duration_compliance", False, issue.message, [issue.id])
        return

    if 4 <= minutes <= 5:
        add_check("duration_compliance", True, f"Duration is within range ({duration_text}).")
        return

    issue = add_issue(
        "duration_compliance",
        f"Duration is outside the 4-5 minute range ({duration_text}).",
        [Evidence(field="metadata", text=duration_text, length=round(minutes, 2))],
        "Trim or expand narration, or record an approved exception outside compliance.",
    )
    add_check("duration_compliance", False, issue.message, [issue.id])


def _row_granularity(add_check, add_issue, rows: List[ScriptRow]) -> None:
    crowded = [
        Evidence(row_id=r.row_id, row_number=r.row_number, field="narration", text=_preview(r.narration.text), length=len(_plain_text(r.narration.text)), reason="Narration is long for one row.")
        for r in rows
        if len(_plain_text(r.narration.text)) > 220 and r.slide_type not in SKIP_LENGTH_SECTIONS
    ]
    if len(rows) < 8:
        issue = add_issue("sufficient_row_granularity", "Script has fewer than 8 rows.", [Evidence(field="script", text=str(len(rows)), length=len(rows))], "Split content into more focused visual/narration rows.")
        add_check("sufficient_row_granularity", False, issue.message, [issue.id])
    elif crowded:
        issue = add_issue("sufficient_row_granularity", f"{len(crowded)} row(s) may be overcrowded.", crowded[:5], "Split long narration into smaller visual steps.")
        add_check("sufficient_row_granularity", False, issue.message, [issue.id])
    else:
        add_check("sufficient_row_granularity", True, "Row granularity looks adequate.")


def _sentence_hard_limit(add_check, add_issue, rows: List[ScriptRow]) -> None:
    evidence = []
    for row, line_no, line in _applicable_lines(rows):
        length = len(_plain_text(line))
        if length > 80:
            evidence.append(Evidence(row_id=row.row_id, row_number=row.row_number, field="narration", text=line, start_offset=0, end_offset=len(line), length=length, reason=f"Line {line_no} exceeds 80 characters."))
    if evidence:
        issue = add_issue("sentence_hard_limit", f"{len(evidence)} applicable sentence(s) exceed 80 characters.", evidence[:10], "Split long narration into shorter lines.")
        add_check("sentence_hard_limit", False, issue.message, [issue.id])
    else:
        add_check("sentence_hard_limit", True, "No applicable narration sentence exceeds 80 characters.")


def _sentence_soft_target(add_check, add_issue, rows: List[ScriptRow]) -> None:
    lines = list(_applicable_lines(rows))
    if not lines:
        add_check("sentence_soft_target", True, "No applicable narration sentences found.")
        return
    over = []
    for row, line_no, line in lines:
        length = len(_plain_text(line))
        if length > 60:
            over.append(Evidence(row_id=row.row_id, row_number=row.row_number, field="narration", text=line, start_offset=0, end_offset=len(line), length=length, reason=f"Line {line_no} exceeds the 60-character target."))
    pass_ratio = (len(lines) - len(over)) / len(lines)
    if pass_ratio >= 0.9:
        add_check("sentence_soft_target", True, f"{round(pass_ratio * 100)}% of applicable sentences are within 60 characters.")
    else:
        issue = add_issue("sentence_soft_target", f"Only {round(pass_ratio * 100)}% of applicable sentences are within 60 characters.", over[:10], "Prefer shorter narration lines for translation and dubbing.")
        add_check("sentence_soft_target", False, issue.message, [issue.id])


def _one_sentence_per_line(add_check, add_issue, rows: List[ScriptRow]) -> None:
    evidence = []
    for row, line_no, line in _applicable_lines(rows):
        plain = _plain_text(line)
        if re.search(r"[.!?]\s+[A-Z0-9]", plain):
            evidence.append(Evidence(row_id=row.row_id, row_number=row.row_number, field="narration", text=line, reason=f"Line {line_no} appears to contain multiple sentences."))
    if evidence:
        issue = add_issue("one_sentence_per_line", f"{len(evidence)} line(s) appear to contain multiple sentences.", evidence[:10], "Place each sentence on its own narration line.")
        add_check("one_sentence_per_line", False, issue.message, [issue.id])
    else:
        add_check("one_sentence_per_line", True, "Narration appears to keep one sentence per line.")


def _links_active(add_check, add_issue, artifact: ScriptArtifact) -> None:
    urls = sorted(set(artifact.hyperlinks))
    if not urls:
        add_check("links_present_active", True, "No URLs found in the script.")
        return
    broken = []
    for url in urls:
        reason = _validate_url(url)
        if reason:
            broken.append(Evidence(field="script", text=url, reason=reason))
    if broken:
        issue = add_issue("links_present_active", f"{len(broken)} link(s) could not be validated.", broken[:10], "Check the links and update any inactive references.")
        add_check("links_present_active", False, issue.message, [issue.id])
    else:
        add_check("links_present_active", True, f"All {len(urls)} link(s) are active.")


def _applicable_lines(rows: List[ScriptRow]) -> Iterable[Tuple[ScriptRow, int, str]]:
    for row in rows:
        if row.slide_type in SKIP_LENGTH_SECTIONS:
            continue
        for line_no, raw_line in enumerate(row.narration.text.splitlines(), 1):
            line = raw_line.strip()
            if not line or line.startswith("•"):
                continue
            yield row, line_no, line


def _has_value(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _parse_duration_minutes(text: str) -> float | None:
    numbers = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text)]
    if not numbers:
        return None
    return max(numbers)


def _validate_url(url: str) -> str | None:
    try:
        with httpx.Client(timeout=5.0, follow_redirects=True) as client:
            response = client.head(url)
            if response.status_code == 405:
                response = client.get(url)
            if response.status_code < 400:
                return None
            return f"HTTP {response.status_code}"
    except httpx.TimeoutException:
        return "Timeout"
    except httpx.RequestError:
        return "Connection error"
    except Exception as exc:
        return str(exc)[:80]


def _plain_text(text: str) -> str:
    return re.sub(r"\*\*([^*]+)\*\*", r"\1", text or "").strip()


def _preview(text: str, limit: int = 180) -> str:
    plain = _plain_text(text).replace("\n", " ")
    return plain if len(plain) <= limit else plain[: limit - 3] + "..."
