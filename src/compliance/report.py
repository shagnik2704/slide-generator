"""Report assembly for evidence-based compliance."""

from typing import Dict, List

from src.compliance.schemas import CheckResult, ComplianceIssue, ComplianceReport, Policy, ScriptArtifact
from src.compliance.validators.semantic import derive_ready_for_review


def build_report(
    policy: Policy,
    artifact: ScriptArtifact,
    checks: List[CheckResult],
    issues: List[ComplianceIssue],
) -> ComplianceReport:
    checks_by_id = {check.id: check for check in checks}
    ordered_checks: List[CheckResult] = []
    for criterion in policy.criteria:
        if criterion.id == "ready_for_review":
            continue
        if criterion.id in checks_by_id:
            ordered_checks.append(checks_by_id[criterion.id])
        else:
            ordered_checks.append(CheckResult(
                id=criterion.id,
                criteria=criterion.criteria,
                ai_review=None,
                ai_notes="Check was not run.",
                severity=criterion.severity,
                validator=criterion.validator,
            ))

    ordered_checks.append(derive_ready_for_review(policy, ordered_checks))
    annotations = _build_annotations(issues)

    ai_passed = sum(1 for check in ordered_checks if check.ai_review is True)
    ai_failed = sum(1 for check in ordered_checks if check.ai_review is False)
    ai_skipped = sum(1 for check in ordered_checks if check.ai_review is None)
    failed_issue_ids = {issue_id for check in ordered_checks if check.ai_review is False for issue_id in check.issues}
    failed_issues = [issue for issue in issues if issue.id in failed_issue_ids or issue.criteria_id in {c.id for c in ordered_checks if c.ai_review is False}]

    return ComplianceReport(
        checks=ordered_checks,
        summary={
            "ai_passed": ai_passed,
            "ai_failed": ai_failed,
            "ai_skipped": ai_skipped,
            "total": len(ordered_checks),
            "blockers": sum(1 for issue in failed_issues if issue.severity == "blocker"),
            "major": sum(1 for issue in failed_issues if issue.severity == "major"),
            "minor": sum(1 for issue in failed_issues if issue.severity == "minor"),
        },
        issues=issues,
        annotations=annotations,
        policy={"id": policy.id, "version": policy.version, "criteria_count": len(policy.criteria)},
        artifact_summary={
            "rows": len(artifact.rows),
            "detected_sections": artifact.detected_sections,
            "hyperlinks": len(artifact.hyperlinks),
        },
    )


def _build_annotations(issues: List[ComplianceIssue]) -> Dict[str, List[str]]:
    annotations: Dict[str, List[str]] = {}
    for issue in issues:
        for evidence in issue.evidence:
            if not evidence.row_id or not evidence.field:
                continue
            key = f"{evidence.row_id}:{evidence.field}"
            annotations.setdefault(key, []).append(issue.id)
    return annotations
