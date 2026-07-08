"""Semantic LLM validators for admin compliance."""

import asyncio
import json
import os
from typing import Dict, List, Tuple

from langchain_openai import ChatOpenAI

from src.compliance.schemas import (
    CheckResult,
    ComplianceIssue,
    Evidence,
    Policy,
    PolicyCriterion,
    ScriptArtifact,
    SemanticBatchResult,
)


SEMANTIC_MODEL = "gpt-5.2"

SEMANTIC_GROUPS: Dict[str, Tuple[str, ...]] = {
    "structure_flow": (
        "script_follows_outline",
        "logical_learning_flow",
        "utility_context_explained",
        "demonstration_analogy_ratio",
    ),
    "visual_demo": (
        "visual_narration_alignment",
        "technical_demo_executability",
    ),
    "language_quality": (
        "translation_friendly_language",
        "grammar_punctuation",
    ),
    "terminology_formatting": (
        "terminology_clarity_consistency",
        "abbreviations_explained",
        "technical_ui_terms_bolded",
    ),
    "factuality": (
        "factual_claims_credible",
    ),
}

GROUP_INSTRUCTIONS = {
    "structure_flow": "Focus on outline coverage, sequencing, learner context, and whether the script uses demonstration or analogy rather than only theory.",
    "visual_demo": "Focus on whether each visual cue matches the narration and whether technical/demo steps can be followed side-by-side without missing actions.",
    "language_quality": "Focus on translation-friendly narration, grammar, spelling, punctuation, and dubbing clarity.",
    "terminology_formatting": "Focus on term introduction, consistency, abbreviation expansion, and bold marking for important UI or technical terms.",
    "factuality": "Focus only on check-worthy factual, version, API, historical, etymology, or technical requirement claims.",
    "ungrouped": "Evaluate the listed criteria using row/cell evidence.",
}


def _semantic_criteria(policy: Policy) -> List[PolicyCriterion]:
    return [c for c in policy.criteria if c.validator == "semantic"]


async def run_semantic_validators(policy: Policy, artifact: ScriptArtifact) -> Tuple[List[CheckResult], List[ComplianceIssue]]:
    criteria = _semantic_criteria(policy)
    if not criteria:
        return [], []

    if not os.getenv("OPENAI_API_KEY"):
        return [_skipped(c, "Semantic checks skipped because OPENAI_API_KEY is not configured.") for c in criteria], []

    groups = _group_semantic_criteria(criteria)
    tasks = [
        _run_factual_group(group_id, group_criteria, artifact)
        if group_id == "factuality"
        else _run_semantic_group(group_id, group_criteria, artifact)
        for group_id, group_criteria in groups
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    checks: List[CheckResult] = []
    issues: List[ComplianceIssue] = []
    for (group_id, group_criteria), result in zip(groups, results):
        if isinstance(result, Exception):
            note = f"Semantic group '{group_id}' skipped because the LLM call failed: {str(result)[:160]}"
            checks.extend(_skipped(c, note) for c in group_criteria)
            continue

        group_checks, group_issues = _normalize_group_issue_ids(group_id, result[0], result[1])
        checks.extend(group_checks)
        issues.extend(group_issues)

    checks_by_id = {check.id: check for check in checks}
    ordered_checks = [checks_by_id[c.id] for c in criteria if c.id in checks_by_id]
    return ordered_checks, issues


def _group_semantic_criteria(criteria: List[PolicyCriterion]) -> List[Tuple[str, List[PolicyCriterion]]]:
    by_id = {criterion.id: criterion for criterion in criteria}
    grouped: List[Tuple[str, List[PolicyCriterion]]] = []
    seen = set()

    for group_id, criterion_ids in SEMANTIC_GROUPS.items():
        group_criteria = [by_id[criteria_id] for criteria_id in criterion_ids if criteria_id in by_id]
        if group_criteria:
            grouped.append((group_id, group_criteria))
            seen.update(criterion.id for criterion in group_criteria)

    remaining = [criterion for criterion in criteria if criterion.id not in seen]
    if remaining:
        grouped.append(("ungrouped", remaining))

    return grouped


async def _run_semantic_group(group_id: str, criteria: List[PolicyCriterion], artifact: ScriptArtifact) -> Tuple[List[CheckResult], List[ComplianceIssue]]:
    prompt = _build_group_prompt(group_id, criteria, artifact)
    result = await _run_structured_llm(prompt)
    return _semantic_batch_to_results(criteria, artifact, result)


async def _run_factual_group(group_id: str, criteria: List[PolicyCriterion], artifact: ScriptArtifact) -> Tuple[List[CheckResult], List[ComplianceIssue]]:
    criterion = criteria[0]
    notes = await _run_factual_research_pass(criteria, artifact)

    if _factual_notes_have_no_claims(notes):
        return [CheckResult(
            id=criterion.id,
            criteria=criterion.criteria,
            ai_review=True,
            ai_notes="No high-risk factual claims requiring web verification were found.",
            severity=criterion.severity,
            validator="semantic",
        )], []

    if _factual_notes_are_inconclusive(notes):
        return [_skipped(criterion, "Factual verification skipped because web evidence was unavailable or inconclusive.")], []

    prompt = _build_factual_structured_prompt(criteria, artifact, notes)
    result = await _run_structured_llm(prompt)
    checks, issues = _semantic_batch_to_results(criteria, artifact, result)

    if not _factual_notes_allow_failure(notes):
        checks = [
            _skipped(criterion, "Factual verification skipped because no web-sourced contradiction was found.")
            if check.id == criterion.id and check.ai_review is False
            else check
            for check in checks
        ]
        issues = [issue for issue in issues if issue.criteria_id != criterion.id]

    return checks, issues


async def _run_structured_llm(prompt: str) -> SemanticBatchResult:
    llm = ChatOpenAI(model=SEMANTIC_MODEL, temperature=0.2)
    result = await llm.with_structured_output(SemanticBatchResult).ainvoke(prompt)
    if result is None:
        raise RuntimeError("LLM returned no structured result")
    return result


async def _run_factual_research_pass(criteria: List[PolicyCriterion], artifact: ScriptArtifact) -> str:
    prompt = _build_factual_research_prompt(criteria, artifact)
    llm = ChatOpenAI(model=SEMANTIC_MODEL, temperature=0.2).bind_tools([{"type": "web_search"}])
    response = await llm.ainvoke(prompt)
    return _message_content_to_text(response)


def _semantic_batch_to_results(
    criteria: List[PolicyCriterion],
    artifact: ScriptArtifact,
    result: SemanticBatchResult | None,
) -> Tuple[List[CheckResult], List[ComplianceIssue]]:
    by_id = {item.criteria_id: item for item in (result.checks if result else [])}
    checks: List[CheckResult] = []
    issues: List[ComplianceIssue] = []
    issue_counter = 1

    for criterion in criteria:
        item = by_id.get(criterion.id)
        if item is None:
            checks.append(_skipped(criterion, "Semantic check skipped because the model did not return this criterion."))
            continue

        if item.passed:
            checks.append(CheckResult(
                id=criterion.id,
                criteria=criterion.criteria,
                ai_review=True,
                ai_notes=item.notes or "Passed.",
                severity=criterion.severity,
                validator="semantic",
            ))
            continue

        if not item.evidence:
            checks.append(_skipped(criterion, "Semantic failure skipped because the model did not provide row/cell evidence."))
            continue

        evidence = []
        for ev in item.evidence[:8]:
            row = _row_by_number(artifact, ev.row_number)
            evidence.append(Evidence(
                row_id=row.row_id if row else None,
                row_number=ev.row_number,
                field=ev.field or "script",
                text=ev.text,
                reason=ev.reason,
            ))

        issue_ids = []
        for ev in evidence:
            issue = ComplianceIssue(
                id=f"sem_{issue_counter:03d}",
                criteria_id=criterion.id,
                severity=criterion.severity,
                message=_issue_message_for_evidence(criterion, item.notes, ev),
                evidence=[ev],
                suggested_action=item.suggested_action or _suggested_action_for_evidence(criterion, ev),
            )
            issue_counter += 1
            issues.append(issue)
            issue_ids.append(issue.id)

        checks.append(CheckResult(
            id=criterion.id,
            criteria=criterion.criteria,
            ai_review=False,
            ai_notes=item.notes or f"{len(issue_ids)} row-level issue(s) found.",
            severity=criterion.severity,
            validator="semantic",
            issues=issue_ids,
        ))

    return checks, issues


def _normalize_group_issue_ids(
    group_id: str,
    checks: List[CheckResult],
    issues: List[ComplianceIssue],
) -> Tuple[List[CheckResult], List[ComplianceIssue]]:
    id_map = {
        issue.id: f"sem_{group_id}_{index:03d}"
        for index, issue in enumerate(issues, 1)
    }
    normalized_issues = [
        issue.model_copy(update={"id": id_map[issue.id]})
        for issue in issues
    ]
    normalized_checks = [
        check.model_copy(update={"issues": [id_map.get(issue_id, issue_id) for issue_id in check.issues]})
        for check in checks
    ]
    return normalized_checks, normalized_issues


def derive_ready_for_review(policy: Policy, checks: List[CheckResult]) -> CheckResult:
    criterion = next(c for c in policy.criteria if c.id == "ready_for_review")
    failed_major = [c for c in checks if c.ai_review is False and c.severity in {"blocker", "major"}]
    skipped_major = [c for c in checks if c.ai_review is None and c.severity in {"blocker", "major"}]
    if failed_major:
        return CheckResult(
            id=criterion.id,
            criteria=criterion.criteria,
            ai_review=False,
            ai_notes=f"Not ready: {len(failed_major)} blocker/major check(s) failed.",
            severity=criterion.severity,
            validator="derived",
            issues=[],
        )
    if skipped_major:
        return CheckResult(
            id=criterion.id,
            criteria=criterion.criteria,
            ai_review=None,
            ai_notes=f"Readiness cannot be confirmed: {len(skipped_major)} blocker/major check(s) were skipped.",
            severity=criterion.severity,
            validator="derived",
            issues=[],
        )
    return CheckResult(
        id=criterion.id,
        criteria=criterion.criteria,
        ai_review=True,
        ai_notes="No blocker or major compliance failures were found.",
        severity=criterion.severity,
        validator="derived",
    )


def _skipped(criterion: PolicyCriterion, note: str) -> CheckResult:
    return CheckResult(
        id=criterion.id,
        criteria=criterion.criteria,
        ai_review=None,
        ai_notes=note,
        severity=criterion.severity,
        validator=criterion.validator,
    )


def _row_by_number(artifact: ScriptArtifact, row_number: int | None):
    if row_number is None:
        return None
    for row in artifact.rows:
        if row.row_number == row_number:
            return row
    return None


def _build_prompt(criteria: List[PolicyCriterion], artifact: ScriptArtifact) -> str:
    return _build_group_prompt("semantic", criteria, artifact)


def _build_group_prompt(group_id: str, criteria: List[PolicyCriterion], artifact: ScriptArtifact) -> str:
    rows = [
        {
            "row_number": row.row_number,
            "visual_cue": row.visual_cue.text,
            "narration": row.narration.text,
            "slide_type": row.slide_type,
        }
        for row in artifact.rows
    ]
    checklist = [{"criteria_id": c.id, "question": c.criteria, "severity": c.severity} for c in criteria]
    return f"""You are an admin compliance reviewer for Spoken Tutorial scripts.

Evaluate only the listed semantic criteria for the {group_id} review group.
Group focus: {GROUP_INSTRUCTIONS.get(group_id, GROUP_INSTRUCTIONS["ungrouped"])}
Use British English spelling.

Rules:
- Every failed check MUST include row_number, field, quoted text, and reason.
- Each evidence reason MUST be specific to that exact row/cell. Avoid vague phrases like "several rows", "some cues", or "multiple issues".
- For visual/narration issues, state exactly what narration action is missing, incorrect, or mismatched in the visual cue.
- For language, terminology, grammar, and factual issues, quote the exact problematic wording and explain the concrete problem.
- If you cannot cite row/cell evidence, mark the check as passed only if there is truly no issue.
- Keep notes concise and actionable.
- Do not invent rows or facts.
- Treat slide_type values such as title, prerequisites, resource_files, disclaimer, summary, assignment, acknowledgement, and closing as boilerplate unless the listed criterion directly concerns them.

Metadata:
{json.dumps(artifact.metadata, indent=2)}

Detected sections:
{json.dumps(artifact.detected_sections)}

Criteria:
{json.dumps(checklist, indent=2)}

Script rows:
{json.dumps(rows, indent=2)}
"""


def _build_factual_research_prompt(criteria: List[PolicyCriterion], artifact: ScriptArtifact) -> str:
    rows = [
        {
            "row_number": row.row_number,
            "visual_cue": row.visual_cue.text,
            "narration": row.narration.text,
            "slide_type": row.slide_type,
        }
        for row in artifact.rows
    ]
    checklist = [{"criteria_id": c.id, "question": c.criteria, "severity": c.severity} for c in criteria]
    return f"""You are a factual verification reviewer for Spoken Tutorial scripts.

Use web_search only when needed. Verify at most 5 high-risk factual claims:
- software, browser, package, or OS versions
- technical requirements
- API/library behaviour
- historical or etymology claims
- strong absolute factual claims

Do not flag ordinary instructions such as "open", "click", "type", or tutorial framing.
Prefer official/vendor documentation and release notes when searching.
Training knowledge can help you reason, but a failure must be backed by web evidence.

Return concise verification notes using these exact markers where applicable:
- NO_CHECK_WORTHY_CLAIMS: no high-risk factual claims need verification.
- FACTUAL_SUPPORTED: checked claims are supported by web evidence.
- FACTUAL_CONTRADICTION: a claim is clearly contradicted by web evidence.
- FACTUAL_VERIFICATION_INCONCLUSIVE: search was unavailable, weak, unsupported, or inconclusive.

For every checked claim, include row_number, field, claim text, status, reason, and source title/URL when available.

Criteria:
{json.dumps(checklist, indent=2)}

Script rows:
{json.dumps(rows, indent=2)}
"""


def _build_factual_structured_prompt(
    criteria: List[PolicyCriterion],
    artifact: ScriptArtifact,
    verification_notes: str,
) -> str:
    rows = [
        {
            "row_number": row.row_number,
            "visual_cue": row.visual_cue.text,
            "narration": row.narration.text,
            "slide_type": row.slide_type,
        }
        for row in artifact.rows
    ]
    checklist = [{"criteria_id": c.id, "question": c.criteria, "severity": c.severity} for c in criteria]
    return f"""Convert factual verification notes into structured compliance results.

Rules:
- Return a result for every listed criterion.
- Mark passed=true when claims are supported or no compliance issue remains.
- Mark passed=false only when the notes contain FACTUAL_CONTRADICTION with web evidence.
- Unsupported, unavailable, weak, or inconclusive evidence must not become a failure.
- Every failed check MUST include row_number, field, quoted text, and reason.
- Each evidence reason MUST identify the exact contradicted wording and the source-backed contradiction.
- Keep notes concise and actionable.

Criteria:
{json.dumps(checklist, indent=2)}

Script rows:
{json.dumps(rows, indent=2)}

Factual verification notes:
{verification_notes}
"""


def _message_content_to_text(response) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        return "".join(parts).strip()
    return str(content).strip()


def _issue_message_for_evidence(criterion: PolicyCriterion, notes: str, evidence: Evidence) -> str:
    reason = (evidence.reason or "").strip()
    if reason:
        return reason

    location = (
        f"Row {evidence.row_number}, {evidence.field.replace('_', ' ')}"
        if evidence.row_number and evidence.field
        else "Script evidence"
    )
    if notes and not _looks_like_vague_summary(notes):
        return f"{location}: {notes}"
    return f"{location} needs review for: {criterion.criteria}"


def _suggested_action_for_evidence(criterion: PolicyCriterion, evidence: Evidence) -> str:
    field = (evidence.field or "script").replace("_", " ")
    if criterion.id == "visual_narration_alignment":
        return f"Revise the {field} so it includes the exact action or UI state described by the matching narration."
    if criterion.id == "technical_demo_executability":
        return "Add the missing step or clarify the cited action so the demo can be followed side-by-side."
    if criterion.id == "translation_friendly_language":
        return "Rewrite the cited wording in simpler, direct narration while preserving the meaning."
    if criterion.id == "grammar_punctuation":
        return "Correct the cited grammar, spelling, or punctuation issue."
    if criterion.id == "terminology_clarity_consistency":
        return "Introduce or reuse the cited term consistently and clearly."
    if criterion.id == "abbreviations_explained":
        return "Expand the abbreviation on first use or avoid it."
    if criterion.id == "technical_ui_terms_bolded":
        return "Mark the cited UI term, command, file name, or technical term in bold."
    if criterion.id == "factual_claims_credible":
        return "Verify the cited claim against the source evidence and correct it if needed."
    return f"Review and revise the cited {field}."


def _looks_like_vague_summary(text: str) -> bool:
    value = text.lower()
    vague_markers = (
        "several",
        "multiple",
        "some ",
        "a few",
        "many ",
        "various",
        "overall",
    )
    return any(marker in value for marker in vague_markers)


def _factual_notes_have_no_claims(notes: str) -> bool:
    return "no_check_worthy_claims" in (notes or "").lower()


def _factual_notes_are_inconclusive(notes: str) -> bool:
    value = (notes or "").lower()
    return (
        "factual_verification_inconclusive" in value
        or "not_verifiable" in value
        or "not verifiable" in value
        or "inconclusive" in value
        or "search unavailable" in value
        or "no reliable web evidence" in value
    )


def _factual_notes_allow_failure(notes: str) -> bool:
    value = (notes or "").lower()
    has_contradiction = (
        "factual_contradiction" in value
        or "contradicted" in value
        or "contradicts" in value
        or "conflicts with" in value
    )
    has_source = (
        "http://" in value
        or "https://" in value
        or "source:" in value
        or "official" in value
        or "release notes" in value
        or "documentation" in value
    )
    return has_contradiction and has_source
