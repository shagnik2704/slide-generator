"""
AI-powered compliance checking service for Spoken Tutorial scripts.
Uses Gemini LLM to evaluate scripts against the official checklist.
"""
from langchain_openai import ChatOpenAI
import json
import re
from typing import Dict, List, Tuple
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
import httpx


class CheckResult(BaseModel):
    """Result for a single compliance check."""
    passed: bool = Field(description="Whether the check passed (true) or failed (false)")
    notes: str = Field(description="Brief explanation of the result")


class ComplianceResults(BaseModel):
    """All compliance check results."""
    # Original checklist criteria
    two_column_format: CheckResult = Field(description="Is the script in two column tabular format?")
    prerequisites_mentioned: CheckResult = Field(description="Are all prerequisites mentioned?")
    learning_objectives: CheckResult = Field(description="Are learning objectives mentioned at the beginning?")
    utility_explained: CheckResult = Field(description="Is the utility of the topic explained briefly?")
    abbreviations_avoided: CheckResult = Field(description="Are abbreviations/acronyms avoided or explained?")
    bold_technical_terms: CheckResult = Field(description="Are technical words and UI elements displayed in **bold**?")
    demo_75_percent: CheckResult = Field(description="Is 75% of the tutorial devoted to demonstration or analogies?")
    sufficient_slides: CheckResult = Field(description="Are there sufficient slides for the content?")
    recap_at_end: CheckResult = Field(description="Is there a quick recap at the end of the script?")
    visual_narration_consistent: CheckResult = Field(description="Are Visual Cues consistent with Narration?")
    ready_for_review: CheckResult = Field(description="Is the script ready for Novice and Domain review?")
    
    # Formatting criteria
    sentence_length: CheckResult = Field(description="Are all sentences ≤80 characters? (Skip LO, System Req, Prerequisites, Summary, Assignment, Thank You slides)")
    new_lines: CheckResult = Field(description="Does each sentence start on a new line?")
    grammatical_correctness: CheckResult = Field(description="Is the narration grammatically correct with proper spelling and punctuation?")
    no_forbidden_symbols: CheckResult = Field(description="No forbidden symbols (->, -->, *, - at line start) in narration?")
    


class OutlineComplianceResults(BaseModel):
    """All outline compliance check results based on Spoken Tutorial rubric."""
    # Section A: Outline & Tutorial Design (A1-A17)
    a1_foss_intro: CheckResult = Field(description="A1: Is there a clear introduction to the FOSS?")
    a2_contributors: CheckResult = Field(description="A2: Are contributors clearly mentioned?")
    a3_target_audience: CheckResult = Field(description="A3: Is the target audience clearly defined?")
    a4_descriptive_titles: CheckResult = Field(description="A4: Are tutorial titles descriptive (not Part 1, 2…)?")
    a5_title_length: CheckResult = Field(description="A5: Are all titles under 50 characters?")
    a6_difficulty_grouping: CheckResult = Field(description="A6: Are tutorials grouped by difficulty level?")
    a7_substantial_skill: CheckResult = Field(description="A7: Does each tutorial teach a substantial, usable skill?")
    a8_concept_application_balance: CheckResult = Field(description="A8: Is there a balance of concept and application?")
    a9_trivial_topics_avoided: CheckResult = Field(description="A9: Are trivial and irrelevant topics avoided?")
    a10_objectives_stated: CheckResult = Field(description="A10: Are learning objectives clearly stated?")
    a11_objectives_covered: CheckResult = Field(description="A11: Are all learning objectives fully covered?")
    a12_duration_3to5min: CheckResult = Field(description="A12: Is each tutorial planned for about 3 to 5 minutes?")
    a13_minimum_5_bullets: CheckResult = Field(description="A13: Does each tutorial have at least 5 bullet points?")
    a14_similar_topics_together: CheckResult = Field(description="A14: Are similar-level topics kept in the same tutorial?")
    a15_minimise_overlap: CheckResult = Field(description="A15: Is overlap between tutorials minimised?")
    a16_logical_sequence: CheckResult = Field(description="A16: Are tutorials arranged in a logical learning sequence?")
    a17_no_hardcoded_numbers: CheckResult = Field(description="A17: Are tutorials free from hard-coded numbering?")
    
    # Section B: Beginner-Friendly Design Check (B1-B6)
    b1_beginner_followable: CheckResult = Field(description="B1: Can a true beginner follow without external help?")
    b2_one_concept_per_tutorial: CheckResult = Field(description="B2: Is only one major concept taught per tutorial?")
    b3_examples_used: CheckResult = Field(description="B3: Are examples used to explain concepts?")
    b4_continuing_examples: CheckResult = Field(description="B4: Are continuing examples used across tutorials?")
    b5_hands_on: CheckResult = Field(description="B5: Is most of the tutorial hands-on?")
    b6_mistakes_recovery: CheckResult = Field(description="B6: Are common mistakes and recovery shown?")
    
    # Section C: Expert-Friendly Design Check (C1-C6)
    c1_modular_reusable: CheckResult = Field(description="C1: Are tutorials modular and reusable?")
    c2_scope_bounded: CheckResult = Field(description="C2: Is the scope of each tutorial clearly bounded?")
    c3_reorderable: CheckResult = Field(description="C3: Can tutorials be reordered without rewriting?")
    c4_course_structure: CheckResult = Field(description="C4: Can the series map to a formal course structure?")
    c5_consistent_demo: CheckResult = Field(description="C5: Is the demonstration standard consistent?")
    c6_overview_planned: CheckResult = Field(description="C6: Is there a plan for an overview tutorial?")
    
    # Section D: Examples & Demonstrations (D1-D5)
    d1_examples_mandatory: CheckResult = Field(description="D1: Does every tutorial include at least one example?")
    d2_build_on_examples: CheckResult = Field(description="D2: Do tutorials build on earlier examples/files?")
    d3_75_percent_demo: CheckResult = Field(description="D3: Is at least 75% of each tutorial demonstration?")
    d4_self_learning: CheckResult = Field(description="D4: Is the tutorial suitable for self-learning?")
    d5_overview_after_series: CheckResult = Field(description="D5: Is the overview tutorial planned after the series?")
    


def extract_urls(json_script: dict) -> List[str]:
    """Extract all URLs from narration and visual cue text in the script."""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]\'()]+'
    urls = []
    
    for slide in json_script.get('slides', []):
        # Check narration
        narration = slide.get('narration', '')
        urls.extend(re.findall(url_pattern, narration))
        
        # Check visual cue / image prompt
        visual_cue = slide.get('image_prompt', '')
        urls.extend(re.findall(url_pattern, visual_cue))
    
    return list(set(urls))  # Remove duplicates


def validate_urls(urls: List[str]) -> Tuple[List[str], List[Tuple[str, str]]]:
    """
    Validate URLs by making HEAD requests.
    Returns (active_urls, broken_urls) where broken_urls is list of (url, reason) tuples.
    """
    active = []
    broken = []
    
    if not urls:
        return active, broken
    
    with httpx.Client(timeout=5.0, follow_redirects=True) as client:
        for url in urls:
            try:
                response = client.head(url)
                if response.status_code < 400:
                    active.append(url)
                else:
                    broken.append((url, f"HTTP {response.status_code}"))
            except httpx.TimeoutException:
                broken.append((url, "Timeout"))
            except httpx.RequestError as e:
                broken.append((url, f"Connection error"))
            except Exception as e:
                broken.append((url, str(e)[:30]))
    
    return active, broken


def check_links(json_script: dict) -> dict:
    """
    Check if all links in the script are active.
    Returns a check result dict.
    """
    urls = extract_urls(json_script)
    
    if not urls:
        return {
            "id": "links_active",
            "criteria": "Are all links in the script active (if any)?",
            "ai_review": True,
            "ai_notes": "No URLs found in the script",
            "human_review": None
        }
    
    active, broken = validate_urls(urls)
    
    if not broken:
        return {
            "id": "links_active",
            "criteria": "Are all links in the script active (if any)?",
            "ai_review": True,
            "ai_notes": f"All {len(active)} link(s) are active",
            "human_review": None
        }
    else:
        broken_list = ", ".join([f"{url} ({reason})" for url, reason in broken[:3]])
        if len(broken) > 3:
            broken_list += f" ... and {len(broken) - 3} more"
        return {
            "id": "links_active",
            "criteria": "Are all links in the script active (if any)?",
            "ai_review": False,
            "ai_notes": f"{len(broken)} broken link(s): {broken_list}",
            "human_review": None
        }


async def check_compliance(json_script: dict, tutorial_type: str = "conceptual") -> dict:
    """
    Run AI-powered compliance checks on a script.
    
    Args:
        json_script: The parsed script JSON
        tutorial_type: 'conceptual' or 'demo'
    
    Returns:
        Dictionary with checklist results for 3-column display
    """
    # Initialize LLM with structured output
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3,    
    )
    llm_openai = ChatOpenAI(model='gpt-5.2')
    structured_llm = llm_openai.with_structured_output(ComplianceResults)
    
    # Build the prompt
    prompt = f"""You are a Spoken Tutorial script reviewer. Evaluate this script against the official compliance checklist.

 Use British English spelling and conventions throughout your responses.

=== SCRIPT TO REVIEW ===
{json.dumps(json_script, indent=2)}

=== COMPLIANCE CHECKLIST ===

### CONTENT CRITERIA
1. **Two Column Format**: Does the script have a clear Visual Cue and Narration structure?
2. **Prerequisites Mentioned**: Are the prerequisites (prior knowledge, software, tutorials) clearly stated?
3. **Learning Objectives**: Are clear learning objectives mentioned in the first few slides?
4. **Utility Explained**: Is there a brief explanation of WHY this topic is useful or important?
5. **Abbreviations Avoided**: Are abbreviations either avoided or properly explained when first used?
6. **Bold Technical Terms**: Are technical terms, UI elements, buttons, and keywords marked in **bold**?
7. **75% Demonstration/Analogies**: Is at least 75% of the content focused on hands-on demonstration OR relatable analogies (not just dry theory)?
    - Demonstrations: step-by-step actions, clicking, typing, running code
    - Analogies: relatable examples, comparisons, real-world scenarios that explain concepts
    - SKIP this check for: Learning Objectives, System Requirements, Prerequisites, Summary, Assignment, and Thank You slides
    - Only check content slides

8. **Sufficient Slides**: Are there enough slides to cover the content adequately (typically 8-15 for a 3-4 min tutorial)? More slides are okay,less are not.
9. **Recap at End**: Is there a summary or recap slide near the end?
10. **Visual-Narration Consistency**: Do the Visual Cues match what the Narration describes?
11. **Ready for Review**: Overall, is this script polished enough for Novice and Domain expert review?

### FORMATTING CRITERIA
12. **Sentence Length**: EVERY sentence MUST be ≤ 80 characters.
    - SKIP this check for: Learning Objectives, System Requirements, Prerequisites, Summary, Assignment, and Thank You slides
    - These slides typically have bullet points that naturally exceed 80 characters
    - Only check content/demonstration slides
    - If ANY sentence in a content slide exceeds 80 chars, mark as FAILED
    
13. **New Lines**: Each sentence must start on a new line (\n between sentences).
    - Multiple sentences on the same line = FAILED

14. **Grammatical Correctness**: Check the narration for grammar, spelling, and punctuation:
    - Correct subject-verb agreement
    - Proper spelling of all words
    - Correct punctuation (periods, commas, apostrophes)
    - Clear and readable sentence structure
    - If there are ANY errors, mark as FAILED and list the specific issues
    
15. **No Forbidden Symbols**: Check narration for forbidden symbols:
    - FORBIDDEN: ->, -->, *, - at the start of lines
    - ALLOWED: **bold** markers are OK
    - ALLOWED: • bullets ONLY in Learning Objectives slide

For each check, provide:
- passed: true/false
- notes: Structured feedback following this format:
  - If PASSED: brief confirmation
  - If FAILED: Use numbered lists with EACH ITEM ON A NEW LINE:
    1. "Row X: [specific issue]"
    2. "Line Y: [specific problem]"
    Use newline characters (\n) between each numbered item.
  - IMPORTANT: Always use "Row" (not "Slide") when referencing issues. E.g., "Row 3: sentence exceeds 80 chars"
  - Be specific: quote problematic text when helpful
  - Keep each item concise (under 100 chars)
"""

    try:
        result = await structured_llm.ainvoke(prompt)
        
        if result is None:
            return _get_error_response("AI returned no result")
        
        # Convert to checklist format - Content criteria
        checks = [
            _format_check("two_column_format", "Is the script in two column tabular format?", result.two_column_format),
            _format_check("prerequisites", "Are all the prerequisites mentioned?", result.prerequisites_mentioned),
            _format_check("learning_objectives", "Are the learning objectives mentioned at the beginning?", result.learning_objectives),
            _format_check("utility_explained", "Is the utility of the topic explained briefly?", result.utility_explained),
            _format_check("abbreviations", "Are abbreviations/acronyms avoided or explained?", result.abbreviations_avoided),
            _format_check("bold_technical", "Are technical words/UI elements in **bold**?", result.bold_technical_terms),
            _format_check("demo_percentage", "Is 75% of the tutorial devoted to demonstration/analogies?", result.demo_75_percent),
            _format_check("sufficient_slides", "Are there sufficient slides for the content?", result.sufficient_slides),
            _format_check("recap", "Is a quick recap given at the end of the script?", result.recap_at_end),
            _format_check("visual_narration", "Are Visual Cues consistent with Narration?", result.visual_narration_consistent),
            _format_check("ready_for_review", "Is the script ready for Novice and Domain review?", result.ready_for_review),
        ]
        
        # Formatting criteria
        formatting_checks = [
            _format_check("sentence_length", "Every sentence ≤80 characters (skip LO/Thank You)?", result.sentence_length),
            _format_check("new_lines", "Each sentence starts on a new line?", result.new_lines),
            _format_check("grammatical", "Is the narration grammatically correct?", result.grammatical_correctness),
            _format_check("no_symbols", "No forbidden symbols (->, -->, *, -)?", result.no_forbidden_symbols),
            
        ]
        
        # Link validation (done separately, not by LLM)
        link_check = check_links(json_script)
        
        all_checks = checks + formatting_checks + [link_check]
        
        # Calculate summary
        ai_passed = sum(1 for c in all_checks if c["ai_review"] is True)
        ai_failed = sum(1 for c in all_checks if c["ai_review"] is False)
        
        return {
            "checks": all_checks,
            "summary": {
                "ai_passed": ai_passed,
                "ai_failed": ai_failed,
                "ai_skipped": 0,
                "total": len(all_checks)
            }
        }
        
    except Exception as e:
        print(f"⚠️ Compliance check error: {e}")
        return _get_error_response(str(e))


def _format_check(check_id: str, criteria: str, result: CheckResult) -> dict:
    """Format a single check result."""
    return {
        "id": check_id,
        "criteria": criteria,
        "ai_review": result.passed,
        "ai_notes": result.notes,
        "human_review": None
    }


def _get_error_response(error_msg: str) -> dict:
    """Return error response structure."""
    return {
        "checks": [{
            "id": "error",
            "criteria": "Compliance check failed",
            "ai_review": None,
            "ai_notes": f"Error: {error_msg}",
            "human_review": None
        }],
        "summary": {
            "ai_passed": 0,
            "ai_failed": 0,
            "ai_skipped": 1,
            "total": 1
        }
    }


async def batch_check_compliance(
    scripts: list[dict],
    tutorial_types: list[str] = None
) -> list[dict]:
    """
    Check multiple scripts for compliance in parallel.
    
    Args:
        scripts: List of JSON scripts to check
        tutorial_types: Optional list of tutorial types (one per script).
                       Defaults to 'conceptual' for all.
    
    Returns:
        List of compliance check results, one per script.
        
    Example:
        results = await batch_check_compliance([script1, script2, script3])
        # results[0] = compliance result for script1
        # results[1] = compliance result for script2
        # etc.
    """
    import asyncio
    
    if not scripts:
        return []
    
    # Default all to conceptual if not specified
    if tutorial_types is None:
        tutorial_types = ['conceptual'] * len(scripts)
    elif len(tutorial_types) != len(scripts):
        # Pad with 'conceptual' if lengths don't match
        tutorial_types = list(tutorial_types) + ['conceptual'] * (len(scripts) - len(tutorial_types))
    
    print(f"📋 Batch compliance check: {len(scripts)} scripts in parallel")
    
    # Run all checks in parallel
    tasks = [
        check_compliance(script, tutorial_type)
        for script, tutorial_type in zip(scripts, tutorial_types)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Convert exceptions to error responses
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"⚠️ Script {i+1} failed: {result}")
            processed_results.append(_get_error_response(str(result)))
        else:
            processed_results.append(result)
    
    passed_count = sum(
        1 for r in processed_results 
        if r.get('summary', {}).get('ai_failed', 1) == 0
    )
    print(f"✓ Batch complete: {passed_count}/{len(scripts)} scripts passed all checks")
    
    return processed_results


async def check_outline_compliance(outline_data: dict) -> dict:
    """
    Run AI-powered compliance checks on an outline/tutorial design.
    
    Args:
        outline_data: The outline JSON data (CourseOutlineData format)
    
    Returns:
        Dictionary with checklist results for 3-column display
    """
    # Initialize LLM with structured output
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3,    
    )
    structured_llm = llm.with_structured_output(OutlineComplianceResults)
    
    # Build the prompt
    prompt = f"""You are a Spoken Tutorial outline reviewer. Evaluate this outline/tutorial design against the official compliance checklist.

Use British English spelling and conventions throughout your responses.

=== OUTLINE TO REVIEW ===
{json.dumps(outline_data, indent=2)}

=== COMPLIANCE CHECKLIST ===

### SECTION A: OUTLINE & TUTORIAL DESIGN

A1. **FOSS Introduction**: Is there a clear introduction to the FOSS (what the software is, where it is used, why it is useful)?
   - Check: platform_name, about_course, purpose fields
   - Purpose: Helps learners connect the software to real-world use. Motivates beginners before technical content starts.

A2. **Contributors**: Are contributors clearly mentioned?
   - Check: prepared_by field
   - Purpose: Academic credit and accountability. Identifies subject experts and institutions.

A3. **Target Audience**: Is the target audience clearly defined?
   - Check: target_audience field
   - Purpose: Determines pace, depth, and vocabulary. Prevents mismatch between difficulty level and learner capacity.
   - Example: "This series is intended for absolute beginners with basic computer skills."

A4. **Descriptive Titles**: Are tutorial titles descriptive (concept-based, not sequence-based like "Part 1, Part 2")?
   - Check: tutorial_rows[].title
   - Incorrect: "LibreOffice Part 3"
   - Correct: "Formatting Text"
   - Purpose: Titles should tell learners what skill they will gain. Allows flexible reordering.

A5. **Title Length**: Are all titles under 50 characters?
   - Check: tutorial_rows[].title length
   - Purpose: Keeps URLs short. Improves search visibility. Makes titles readable.

A6. **Difficulty Grouping**: Are tutorials grouped by difficulty level (Beginner/Intermediate/Advanced)?
   - Check: tutorial_rows structure and organization
   - Purpose: Learners can enter at the right level. Avoids cognitive overload.

A7. **Substantial Skill**: Does each tutorial teach a substantial, usable skill?
   - Check: tutorial_rows[].topics_details content
   - Example: Not just "What is layers in GIMP" but "Create, rename, hide, and reorder layers."
   - Purpose: Learners should finish with a new capability, not just awareness.

A8. **Concept-Application Balance**: Is there a balance of concept and application (not only theory, not only procedures)?
   - Check: tutorial_rows[].topics_details - should have both concept introduction and application
   - Purpose: Ensures both understanding and skill development.

A9. **Trivial Topics Avoided**: Are trivial and irrelevant topics avoided?
   - Check: tutorial_rows[].topics_details - avoid obvious actions, rarely used features
   - Purpose: Keeps tutorials meaningful and engaging.

A10. **Objectives Stated**: Are learning objectives clearly stated?
   - Check: course_objectives field
   - Purpose: Provides clear learning contract.

A11. **Objectives Covered**: Are all learning objectives fully covered in the tutorials?
   - Check: course_objectives match tutorial_rows content
   - Purpose: Whatever is promised must be demonstrated and testable.

A12. **Duration 3-5 minutes**: Is each tutorial planned for about 3 to 5 minutes?
   - Check: tutorial_rows[].time_seconds (should be 180-300 seconds)
   - Purpose: Designed for attention span, translation/dubbing, classroom reuse.

A13. **Minimum 5 Bullets**: Does each tutorial have at least 5 bullet points?
   - Check: tutorial_rows[].topics_details length (should be ≥5)
   - Purpose: Acts as content contract, review checklist, scope control.

A14. **Similar Topics Together**: Are similar-level topics kept in the same tutorial?
   - Check: tutorial_rows organization - related actions should not be split
   - Example: Create file, open file, close file → Must be in the same tutorial
   - Purpose: Builds workflow thinking. Prevents fragmented learning.

A15. **Minimise Overlap**: Is overlap between tutorials minimised?
   - Check: tutorial_rows content - avoid re-teaching unnecessarily
   - Purpose: Efficient learning. Avoid learner boredom.

A16. **Logical Sequence**: Are tutorials arranged in a logical learning sequence?
   - Check: tutorial_rows order and prerequisites
   - Purpose: Follows skill progression.

A17. **No Hard-coded Numbers**: Are tutorials free from hard-coded numbering or "previous tutorial"/"next tutorial" references?
   - Check: tutorial_rows[].title, comments, topics_details
   - Purpose: Tutorials may be inserted, removed, or reordered later.

### SECTION B: BEGINNER-FRIENDLY DESIGN CHECK

B1. **Beginner Followable**: Can a true beginner follow without external help?
   - Check: entry_behaviour, prerequisites clarity, tutorial content accessibility
   - Purpose: Self-learning effectiveness.

B2. **One Concept Per Tutorial**: Is only one major concept taught per tutorial?
   - Check: tutorial_rows[].topics_details scope
   - Purpose: Prevents cognitive overload.

B3. **Examples Used**: Are examples used to explain concepts?
   - Check: core_example, allied_examples, tutorial_rows content
   - Purpose: Concrete learning, not abstract.

B4. **Continuing Examples**: Are continuing examples used across tutorials?
   - Check: core_example consistency across tutorial_rows
   - Purpose: Creates continuity. Shows how small skills combine.

B5. **Hands-on**: Is most of the tutorial hands-on?
   - Check: tutorial_rows[].topics_details - should be action-oriented, demonstrable
   - Purpose: Skill replication, practice-oriented education.

B6. **Mistakes and Recovery**: Are common mistakes and recovery shown?
   - Check: tutorial_rows[].topics_details, comments
   - Purpose: Error recovery learning, confidence building.

### SECTION C: EXPERT-FRIENDLY DESIGN CHECK

C1. **Modular and Reusable**: Are tutorials modular and reusable?
   - Check: tutorial_rows structure - each should be self-contained
   - Purpose: Scalability and reuse.

C2. **Scope Bounded**: Is the scope of each tutorial clearly bounded?
   - Check: tutorial_rows[].topics_details - clear start and end
   - Purpose: Clear learning units.

C3. **Reorderable**: Can tutorials be reordered without rewriting?
   - Check: prerequisites structure, no hard-coded dependencies
   - Purpose: Flexibility in course structure.

C4. **Course Structure Mapping**: Can the series map to a formal course structure?
   - Check: overall organization, difficulty levels, learning progression
   - Purpose: Academic integration.

C5. **Consistent Demo Standard**: Is the demonstration standard consistent?
   - Check: tutorial_rows format consistency
   - Purpose: Professional quality.

C6. **Overview Planned**: Is there a plan for an overview tutorial?
   - Check: outline structure, recommended_no_of_tutorials
   - Purpose: Overview should showcase existing material.

### SECTION D: EXAMPLES & DEMONSTRATIONS

D1. **Examples Mandatory**: Does every tutorial include at least one example?
   - Check: `tutorial_rows[].topics_details`
   - Requirement: Pure theory is not allowed. Every concept must be demonstrated with an example.
   - Pass if: Topics mention specific examples (e.g. "Example: Calculation of simple interest").
   - Purpose: Example-driven learning, not abstract explanations.

D2. **Build on Examples**: Do tutorials build on earlier examples/files?
   - Check: `core_example` field and continuity across `tutorial_rows`
   - Requirement: The series should use a "Running Example" that evolves (e.g., creating a file in Tutorial 1, modifying it in Tutorial 2).
   - Purpose: Creates continuity. Shows how small skills combine into real workflows.

D3. **75% Demonstration**: Is at least 75% of each tutorial demonstration?
   - Check: `tutorial_rows[].topics_details`
   - Requirement: Focus on "How-to" (Demonstration) rather than "What-is" (Theory).
   - Pass if: >75% of topics involve user actions (Open, Select, Type, Click).
   - Fail if: Topics are dominated by explanations, definitions, or history.
   - Purpose: Ensures self-learning effectiveness. Visual anchoring.

D4. **Self-learning**: Is the tutorial suitable for self-learning?
   - Check: Logic and flow of `tutorial_rows`
   - Requirement: The sequence should be gap-less. A learner attempting this alone should not get stuck.
   - Purpose: Work without trainers. Support translation.

D5. **Overview After Series**: Is the overview tutorial planned after the series?
   - Check: `tutorial_rows` list
   - Requirement: An "Overview" tutorial should ideally summarize the series or be placed such that it covers the actual content created.
   - Purpose: Overview should showcase existing material, not be created first.

For each check, provide:
- passed: true/false
- notes: Structured feedback following this format:
  - If PASSED: brief confirmation
  - If FAILED: Use numbered lists with EACH ITEM ON A NEW LINE:
    1. "Tutorial X: [specific issue]"
    2. "Field Y: [specific problem]"
    Use newline characters (\n) between each numbered item.
  - Always reference tutorial numbers or field names when applicable
  - Be specific: quote problematic content when helpful
  - Keep each item concise (under 100 chars)
"""

    try:
        result = await structured_llm.ainvoke(prompt)
        
        if result is None:
            return _get_error_response("AI returned no result")
        
        # Convert to checklist format - Section A: Outline & Tutorial Design
        section_a_checks = [
            _format_check("a1_foss_intro", "A1: Is there a clear introduction to the FOSS?", result.a1_foss_intro),
            _format_check("a2_contributors", "A2: Are contributors clearly mentioned?", result.a2_contributors),
            _format_check("a3_target_audience", "A3: Is the target audience clearly defined?", result.a3_target_audience),
            _format_check("a4_descriptive_titles", "A4: Are tutorial titles descriptive (not Part 1, 2…)?", result.a4_descriptive_titles),
            _format_check("a5_title_length", "A5: Are all titles under 50 characters?", result.a5_title_length),
            _format_check("a6_difficulty_grouping", "A6: Are tutorials grouped by difficulty level?", result.a6_difficulty_grouping),
            _format_check("a7_substantial_skill", "A7: Does each tutorial teach a substantial, usable skill?", result.a7_substantial_skill),
            _format_check("a8_concept_application", "A8: Is there a balance of concept and application?", result.a8_concept_application_balance),
            _format_check("a9_trivial_topics", "A9: Are trivial and irrelevant topics avoided?", result.a9_trivial_topics_avoided),
            _format_check("a10_objectives_stated", "A10: Are learning objectives clearly stated?", result.a10_objectives_stated),
            _format_check("a11_objectives_covered", "A11: Are all learning objectives fully covered?", result.a11_objectives_covered),
            _format_check("a12_duration", "A12: Is each tutorial planned for about 3 to 5 minutes?", result.a12_duration_3to5min),
            _format_check("a13_min_5_bullets", "A13: Does each tutorial have at least 5 bullet points?", result.a13_minimum_5_bullets),
            _format_check("a14_similar_topics", "A14: Are similar-level topics kept in the same tutorial?", result.a14_similar_topics_together),
            _format_check("a15_minimise_overlap", "A15: Is overlap between tutorials minimised?", result.a15_minimise_overlap),
            _format_check("a16_logical_sequence", "A16: Are tutorials arranged in a logical learning sequence?", result.a16_logical_sequence),
            _format_check("a17_no_hardcoded", "A17: Are tutorials free from hard-coded numbering?", result.a17_no_hardcoded_numbers),
        ]
        
        # Section B: Beginner-Friendly Design Check
        section_b_checks = [
            _format_check("b1_beginner_followable", "B1: Can a true beginner follow without external help?", result.b1_beginner_followable),
            _format_check("b2_one_concept", "B2: Is only one major concept taught per tutorial?", result.b2_one_concept_per_tutorial),
            _format_check("b3_examples_used", "B3: Are examples used to explain concepts?", result.b3_examples_used),
            _format_check("b4_continuing_examples", "B4: Are continuing examples used across tutorials?", result.b4_continuing_examples),
            _format_check("b5_hands_on", "B5: Is most of the tutorial hands-on?", result.b5_hands_on),
            _format_check("b6_mistakes_recovery", "B6: Are common mistakes and recovery shown?", result.b6_mistakes_recovery),
        ]
        
        # Section C: Expert-Friendly Design Check
        section_c_checks = [
            _format_check("c1_modular", "C1: Are tutorials modular and reusable?", result.c1_modular_reusable),
            _format_check("c2_scope_bounded", "C2: Is the scope of each tutorial clearly bounded?", result.c2_scope_bounded),
            _format_check("c3_reorderable", "C3: Can tutorials be reordered without rewriting?", result.c3_reorderable),
            _format_check("c4_course_structure", "C4: Can the series map to a formal course structure?", result.c4_course_structure),
            _format_check("c5_consistent_demo", "C5: Is the demonstration standard consistent?", result.c5_consistent_demo),
            _format_check("c6_overview_planned", "C6: Is there a plan for an overview tutorial?", result.c6_overview_planned),
        ]
        
        # Section D: Examples & Demonstrations
        section_d_checks = [
            _format_check("d1_examples_mandatory", "D1: Does every tutorial include at least one example?", result.d1_examples_mandatory),
            _format_check("d2_build_on_examples", "D2: Do tutorials build on earlier examples/files?", result.d2_build_on_examples),
            _format_check("d3_75_percent_demo", "D3: Is at least 75% of each tutorial demonstration?", result.d3_75_percent_demo),
            _format_check("d4_self_learning", "D4: Is the tutorial suitable for self-learning?", result.d4_self_learning),
            _format_check("d5_overview_after", "D5: Is the overview tutorial planned after the series?", result.d5_overview_after_series),
        ]
        
        all_checks = section_a_checks + section_b_checks + section_c_checks + section_d_checks
        
        # Calculate summary
        ai_passed = sum(1 for c in all_checks if c["ai_review"] is True)
        ai_failed = sum(1 for c in all_checks if c["ai_review"] is False)
        
        return {
            "checks": all_checks,
            "summary": {
                "ai_passed": ai_passed,
                "ai_failed": ai_failed,
                "ai_skipped": 0,
                "total": len(all_checks)
            }
        }
        
    except Exception as e:
        print(f"⚠️ Outline compliance check error: {e}")
        return _get_error_response(str(e))
