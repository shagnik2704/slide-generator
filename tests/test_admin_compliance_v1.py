import os
import unittest
from unittest.mock import AsyncMock, patch

from src.api.auth import TokenData
from src.api.routes.compliance import check_admin_compliance_v1_endpoint
from src.compliance.policies.admin_script_v1 import ADMIN_SCRIPT_POLICY_V1
from src.compliance.schemas import ComplianceIssue, Evidence, CheckResult, SemanticBatchResult, SemanticCheckResult, SemanticEvidence
from src.compliance.validators import semantic
from src.compliance.workflow import run_admin_script_compliance
from src.compliance.workflow import build_script_artifact


SAMPLE_SCRIPT = {
    "presentation_title": "Working with Tables of Data",
    "domain": "Artificial Intelligence",
    "duration": "5-6 minutes",
    "learning_objectives": ["Create simple data tables"],
    "prerequisites": "Basic Python programming",
    "keywords": ["PyTorch", "Tensor"],
    "outline": ["Introduction", "Rows and columns", "Summary"],
    "slides": [
        {"image_prompt": "Title Slide", "narration": "Welcome to this **Spoken Tutorial**."},
        {"image_prompt": "Learning Objectives", "narration": "In this tutorial, we will learn to\n• Create simple data tables."},
        {"image_prompt": "Prerequisites", "narration": "To follow this tutorial, know **Python**."},
        {"image_prompt": "Long disclaimer", "narration": "As AI tools constantly evolve, if you are unable to locate any icon or encounter difficulty at any step, you may use any conversational AI chatbot for guidance."},
        {"image_prompt": "Code files", "narration": "The following **code file** is required to practice this tutorial."},
        {"image_prompt": "Demo", "narration": "Open **Firefox**.\nType the URL and press **Enter**.\nThis content row is intentionally long enough to fail the hard narration limit check."},
        {"image_prompt": "Summary", "narration": "In this tutorial, we learnt to\n• Create tables."},
        {"image_prompt": "Assignment", "narration": "We encourage you to do this assignment."},
        {"image_prompt": "Acknowledgement", "narration": "Thank you for joining."},
    ],
}


class AdminComplianceV1Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.old_key = os.environ.pop("OPENAI_API_KEY", None)

    def tearDown(self):
        if self.old_key:
            os.environ["OPENAI_API_KEY"] = self.old_key

    async def test_sentence_limits_create_evidence_annotations_and_legacy_shape(self):
        report = await run_admin_script_compliance(SAMPLE_SCRIPT)

        self.assertIn("checks", report)
        self.assertIn("summary", report)
        self.assertIn("issues", report)
        self.assertIn("annotations", report)

        hard_check = next(check for check in report["checks"] if check["id"] == "sentence_hard_limit")
        self.assertFalse(hard_check["ai_review"])
        self.assertTrue(hard_check["issues"])

        issue = next(issue for issue in report["issues"] if issue["id"] == hard_check["issues"][0])
        evidence_rows = {evidence["row_number"] for evidence in issue["evidence"]}
        self.assertNotIn(4, evidence_rows)
        self.assertNotIn(5, evidence_rows)
        self.assertIn(6, evidence_rows)
        self.assertIn("row_006:narration", report["annotations"])

    async def test_hyphenated_prerequisite_slide_is_boilerplate_for_length_checks(self):
        script = {
            **SAMPLE_SCRIPT,
            "slides": [
                {"image_prompt": "Slide 1 Title", "narration": "Welcome."},
                {
                    "image_prompt": "Slide 2\nPre-requisite slide",
                    "narration": "For the pre-requisite of this tutorial, please visit the website shown on your screen.",
                },
                {
                    "image_prompt": "Slide 3\nPre\u2011requiste slide",
                    "narration": "For the pre\u2011requiste of this tutorial, please visit the website shown on your screen.",
                },
                {
                    "image_prompt": "Demo",
                    "narration": "This content row is intentionally long enough to fail the hard narration limit check.",
                },
            ],
        }

        artifact = build_script_artifact(script)
        self.assertEqual(artifact.rows[1].slide_type, "prerequisites")
        self.assertEqual(artifact.rows[2].slide_type, "prerequisites")
        self.assertIn("prerequisites", artifact.detected_sections)

        report = await run_admin_script_compliance(script)
        hard_check = next(check for check in report["checks"] if check["id"] == "sentence_hard_limit")
        issue = next(issue for issue in report["issues"] if issue["id"] == hard_check["issues"][0])
        evidence_rows = {evidence["row_number"] for evidence in issue["evidence"]}

        self.assertNotIn(2, evidence_rows)
        self.assertNotIn(3, evidence_rows)
        self.assertIn(4, evidence_rows)

    async def test_source_artifact_hyperlinks_are_counted(self):
        with patch("src.compliance.validators.deterministic._validate_url", return_value=None):
            report = await run_admin_script_compliance(
                SAMPLE_SCRIPT,
                source_artifact={"hyperlinks": ["https://edupyramids.org/"]},
            )

        self.assertEqual(report["artifact_summary"]["hyperlinks"], 1)
        links_check = next(check for check in report["checks"] if check["id"] == "links_present_active")
        self.assertTrue(links_check["ai_review"])

    async def test_route_returns_additive_report_shape(self):
        current_user = TokenData(email="reviewer@example.com", name="Reviewer", sub="1")
        with patch("src.compliance.validators.deterministic._validate_url", return_value=None):
            report = await check_admin_compliance_v1_endpoint(
                {"json_script": SAMPLE_SCRIPT, "source_artifact": {"hyperlinks": ["https://edupyramids.org/"]}},
                current_user=current_user,
            )

        self.assertIn("checks", report)
        self.assertIn("summary", report)
        self.assertIn("issues", report)
        self.assertIn("annotations", report)
        self.assertEqual(report["policy"]["id"], "admin_script_compliance_v1")

    async def test_semantic_criteria_are_partitioned_into_expected_groups(self):
        criteria = semantic._semantic_criteria(ADMIN_SCRIPT_POLICY_V1)
        groups = semantic._group_semantic_criteria(criteria)

        self.assertEqual([group_id for group_id, _ in groups], list(semantic.SEMANTIC_GROUPS.keys()))
        grouped_ids = [criterion.id for _, group_criteria in groups for criterion in group_criteria]
        self.assertEqual(grouped_ids, [criteria_id for ids in semantic.SEMANTIC_GROUPS.values() for criteria_id in ids])

    async def test_semantic_fan_in_orders_checks_and_normalizes_issue_ids(self):
        artifact = build_script_artifact(SAMPLE_SCRIPT)
        criteria = semantic._semantic_criteria(ADMIN_SCRIPT_POLICY_V1)

        async def fake_group(group_id, group_criteria, _artifact):
            first = group_criteria[0]
            issue = ComplianceIssue(
                id="sem_001",
                criteria_id=first.id,
                severity=first.severity,
                message=f"{group_id} failed.",
                evidence=[Evidence(row_id="row_006", row_number=6, field="narration", text="Example evidence.")],
            )
            checks = [
                CheckResult(
                    id=first.id,
                    criteria=first.criteria,
                    ai_review=False,
                    ai_notes=issue.message,
                    severity=first.severity,
                    validator="semantic",
                    issues=[issue.id],
                )
            ]
            checks.extend(
                CheckResult(
                    id=criterion.id,
                    criteria=criterion.criteria,
                    ai_review=True,
                    ai_notes="Passed.",
                    severity=criterion.severity,
                    validator="semantic",
                )
                for criterion in group_criteria[1:]
            )
            return checks, [issue]

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}):
            with patch("src.compliance.validators.semantic._run_semantic_group", new=fake_group):
                with patch("src.compliance.validators.semantic._run_factual_group", new=fake_group):
                    checks, issues = await semantic.run_semantic_validators(ADMIN_SCRIPT_POLICY_V1, artifact)

        self.assertEqual([check.id for check in checks], [criterion.id for criterion in criteria])
        self.assertEqual(len({issue.id for issue in issues}), len(issues))
        self.assertTrue(all(issue.id.startswith("sem_") for issue in issues))
        for check in checks:
            for issue_id in check.issues:
                self.assertIn(issue_id, {issue.id for issue in issues})

    async def test_semantic_group_failure_skips_only_that_group(self):
        artifact = build_script_artifact(SAMPLE_SCRIPT)

        async def fake_group(group_id, group_criteria, _artifact):
            if group_id == "visual_demo":
                raise RuntimeError("visual group failed")
            return [
                CheckResult(
                    id=criterion.id,
                    criteria=criterion.criteria,
                    ai_review=True,
                    ai_notes="Passed.",
                    severity=criterion.severity,
                    validator="semantic",
                )
                for criterion in group_criteria
            ], []

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}):
            with patch("src.compliance.validators.semantic._run_semantic_group", new=fake_group):
                with patch("src.compliance.validators.semantic._run_factual_group", new=fake_group):
                    checks, _ = await semantic.run_semantic_validators(ADMIN_SCRIPT_POLICY_V1, artifact)

        by_id = {check.id: check for check in checks}
        self.assertIsNone(by_id["visual_narration_alignment"].ai_review)
        self.assertIsNone(by_id["technical_demo_executability"].ai_review)
        self.assertTrue(by_id["script_follows_outline"].ai_review)
        self.assertTrue(by_id["translation_friendly_language"].ai_review)

    async def test_malformed_semantic_failure_without_evidence_is_skipped(self):
        artifact = build_script_artifact(SAMPLE_SCRIPT)
        criterion = next(c for c in semantic._semantic_criteria(ADMIN_SCRIPT_POLICY_V1) if c.id == "grammar_punctuation")
        result = SemanticBatchResult(checks=[
            SemanticCheckResult(
                criteria_id=criterion.id,
                passed=False,
                notes="Grammar appears problematic.",
                evidence=[],
            )
        ])

        checks, issues = semantic._semantic_batch_to_results([criterion], artifact, result)

        self.assertIsNone(checks[0].ai_review)
        self.assertEqual(issues, [])

    async def test_semantic_failures_are_split_into_row_level_issues(self):
        artifact = build_script_artifact(SAMPLE_SCRIPT)
        criterion = next(c for c in semantic._semantic_criteria(ADMIN_SCRIPT_POLICY_V1) if c.id == "visual_narration_alignment")
        result = SemanticBatchResult(checks=[
            SemanticCheckResult(
                criteria_id=criterion.id,
                passed=False,
                notes="Several cues omit key actions mentioned in narration.",
                evidence=[
                    SemanticEvidence(
                        row_number=6,
                        field="visual_cue",
                        text="Demo",
                        reason="Visual cue does not mention opening Firefox before typing the URL.",
                    ),
                    SemanticEvidence(
                        row_number=7,
                        field="narration",
                        text="In this tutorial, we learnt to\n• Create tables.",
                        reason="Narration recap does not match the demonstrated browser action.",
                    ),
                ],
                suggested_action="Align each visual cue with its narration.",
            )
        ])

        checks, issues = semantic._semantic_batch_to_results([criterion], artifact, result)

        self.assertFalse(checks[0].ai_review)
        self.assertEqual(len(issues), 2)
        self.assertEqual(checks[0].issues, [issue.id for issue in issues])
        self.assertEqual(issues[0].message, "Visual cue does not mention opening Firefox before typing the URL.")
        self.assertEqual(issues[0].evidence[0].row_number, 6)
        self.assertEqual(len(issues[0].evidence), 1)

    async def test_factual_supported_claim_returns_pass(self):
        artifact = build_script_artifact(SAMPLE_SCRIPT)
        criterion = next(c for c in semantic._semantic_criteria(ADMIN_SCRIPT_POLICY_V1) if c.id == "factual_claims_credible")

        async def fake_notes(_criteria, _artifact):
            return "FACTUAL_SUPPORTED: Mozilla release notes support Firefox version 148.0.2. Source: https://mozilla.org/"

        async def fake_structured(_prompt):
            return SemanticBatchResult(checks=[
                SemanticCheckResult(criteria_id=criterion.id, passed=True, notes="Version claim is supported.")
            ])

        with patch("src.compliance.validators.semantic._run_factual_research_pass", new=fake_notes):
            with patch("src.compliance.validators.semantic._run_structured_llm", new=fake_structured):
                checks, issues = await semantic._run_factual_group("factuality", [criterion], artifact)

        self.assertTrue(checks[0].ai_review)
        self.assertEqual(issues, [])

    async def test_factual_contradicted_claim_returns_issue(self):
        artifact = build_script_artifact(SAMPLE_SCRIPT)
        criterion = next(c for c in semantic._semantic_criteria(ADMIN_SCRIPT_POLICY_V1) if c.id == "factual_claims_credible")

        async def fake_notes(_criteria, _artifact):
            return "FACTUAL_CONTRADICTION: Official release notes at https://example.com contradict the version claim."

        async def fake_structured(_prompt):
            return SemanticBatchResult(checks=[
                SemanticCheckResult(
                    criteria_id=criterion.id,
                    passed=False,
                    notes="Version claim is contradicted by official release notes.",
                    evidence=[
                        SemanticEvidence(
                            row_number=6,
                            field="narration",
                            text="Open **Firefox**.",
                            reason="Official source contradicts the version detail.",
                        )
                    ],
                    suggested_action="Update the version claim.",
                )
            ])

        with patch("src.compliance.validators.semantic._run_factual_research_pass", new=fake_notes):
            with patch("src.compliance.validators.semantic._run_structured_llm", new=fake_structured):
                checks, issues = await semantic._run_factual_group("factuality", [criterion], artifact)

        self.assertFalse(checks[0].ai_review)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].evidence[0].row_number, 6)

    async def test_factual_inconclusive_claim_is_skipped(self):
        artifact = build_script_artifact(SAMPLE_SCRIPT)
        criterion = next(c for c in semantic._semantic_criteria(ADMIN_SCRIPT_POLICY_V1) if c.id == "factual_claims_credible")
        structured = AsyncMock()

        async def fake_notes(_criteria, _artifact):
            return "FACTUAL_VERIFICATION_INCONCLUSIVE: no reliable web evidence was available."

        with patch("src.compliance.validators.semantic._run_factual_research_pass", new=fake_notes):
            with patch("src.compliance.validators.semantic._run_structured_llm", new=structured):
                checks, issues = await semantic._run_factual_group("factuality", [criterion], artifact)

        self.assertIsNone(checks[0].ai_review)
        self.assertEqual(issues, [])
        structured.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
