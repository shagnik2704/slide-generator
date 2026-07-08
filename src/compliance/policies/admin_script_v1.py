"""Admin script compliance policy v1."""

from src.compliance.schemas import Policy, PolicyCriterion


ADMIN_SCRIPT_POLICY_V1 = Policy(
    id="admin_script_compliance_v1",
    version="1.0",
    criteria=[
        PolicyCriterion(id="two_column_format", criteria="Is the script in a clear Visual Cue and Narration two-column format?", category="structure", severity="blocker", validator="deterministic"),
        PolicyCriterion(id="required_metadata_present", criteria="Are title, domain/module, duration, prerequisites, keywords, and outline present where expected?", category="metadata", severity="major", validator="deterministic"),
        PolicyCriterion(id="learning_objectives_present", criteria="Are learning objectives clearly stated near the beginning?", category="structure", severity="major", validator="deterministic"),
        PolicyCriterion(id="prerequisites_present", criteria="Are learner prerequisites and/or prerequisite tutorials clearly mentioned?", category="structure", severity="major", validator="deterministic"),
        PolicyCriterion(id="script_follows_outline", criteria="Does the script cover the outline topics in the intended order?", category="semantic", severity="major", validator="semantic"),
        PolicyCriterion(id="logical_learning_flow", criteria="Does the script move through setup, explanation/demo, recap, assignment, and closing in a sensible sequence?", category="semantic", severity="major", validator="semantic"),
        PolicyCriterion(id="utility_context_explained", criteria="Is the usefulness or context of the topic briefly explained?", category="semantic", severity="minor", validator="semantic"),
        PolicyCriterion(id="visual_narration_alignment", criteria="Does each visual cue match what the narration says or asks the learner to do?", category="semantic", severity="major", validator="semantic"),
        PolicyCriterion(id="technical_demo_executability", criteria="For technical scripts, can the steps be followed side-by-side in the target tool without missing actions?", category="semantic", severity="major", validator="semantic"),
        PolicyCriterion(id="demonstration_analogy_ratio", criteria="Is most content demonstration-based or analogy-based, not only theory?", category="semantic", severity="major", validator="semantic"),
        PolicyCriterion(id="duration_compliance", criteria="Is the estimated duration within the expected 4-5 minute range?", category="timing", severity="major", validator="deterministic"),
        PolicyCriterion(id="sufficient_row_granularity", criteria="Are there enough rows/slides to avoid overcrowded narration and visuals?", category="structure", severity="minor", validator="deterministic"),
        PolicyCriterion(id="sentence_hard_limit", criteria="Does every applicable narration sentence stay within 80 characters?", category="formatting", severity="major", validator="deterministic"),
        PolicyCriterion(id="sentence_soft_target", criteria="Are most applicable narration sentences within 60 characters?", category="formatting", severity="minor", validator="deterministic"),
        PolicyCriterion(id="one_sentence_per_line", criteria="Does each narration sentence start on a new line?", category="formatting", severity="minor", validator="deterministic"),
        PolicyCriterion(id="translation_friendly_language", criteria="Is the narration simple, direct, and easy to translate/dub?", category="semantic", severity="major", validator="semantic"),
        PolicyCriterion(id="grammar_punctuation", criteria="Is the narration grammatically correct with proper spelling and punctuation?", category="semantic", severity="major", validator="semantic"),
        PolicyCriterion(id="terminology_clarity_consistency", criteria="Are technical terms introduced clearly and used consistently?", category="semantic", severity="major", validator="semantic"),
        PolicyCriterion(id="abbreviations_explained", criteria="Are abbreviations avoided or explained on first use?", category="semantic", severity="minor", validator="semantic"),
        PolicyCriterion(id="technical_ui_terms_bolded", criteria="Are important technical terms, UI elements, buttons, filenames, and commands marked in bold?", category="formatting", severity="minor", validator="semantic"),
        PolicyCriterion(id="links_present_active", criteria="Are any referenced links preserved and active?", category="references", severity="major", validator="deterministic"),
        PolicyCriterion(id="factual_claims_credible", criteria="Are key technical/factual statements plausible and not obviously unsupported or misleading?", category="semantic", severity="major", validator="semantic"),
        PolicyCriterion(id="recap_summary_present", criteria="Is there a quick recap or summary near the end?", category="structure", severity="major", validator="deterministic"),
        PolicyCriterion(id="assignment_present", criteria="Is there an assignment or practice activity where appropriate?", category="structure", severity="minor", validator="deterministic"),
        PolicyCriterion(id="closing_acknowledgement_present", criteria="Does the script include the required closing/acknowledgement section?", category="structure", severity="minor", validator="deterministic"),
        PolicyCriterion(id="ready_for_review", criteria="Overall, is the script polished enough to send to novice and domain reviewers?", category="derived", severity="major", validator="derived"),
    ],
)
