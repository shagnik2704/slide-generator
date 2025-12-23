"""
AI-powered compliance checking service for Spoken Tutorial scripts.
Uses Gemini LLM to evaluate scripts against the official checklist.
"""
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
    demo_75_percent: CheckResult = Field(description="Is 75% of the tutorial devoted to demonstration?")
    sufficient_slides: CheckResult = Field(description="Are there sufficient slides for the content?")
    recap_at_end: CheckResult = Field(description="Is there a quick recap at the end of the script?")
    visual_narration_consistent: CheckResult = Field(description="Are Visual Cues consistent with Narration?")
    ready_for_review: CheckResult = Field(description="Is the script ready for Novice and Domain review?")
    
    # Formatting criteria
    sentence_length: CheckResult = Field(description="Are all sentences ≤80 characters? (Skip LO, System Req, Prerequisites, Summary, Assignment, Thank You slides)")
    new_lines: CheckResult = Field(description="Does each sentence start on a new line?")
    no_forbidden_symbols: CheckResult = Field(description="No forbidden symbols (->, -->, *, - at line start) in narration?")
    


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


def check_compliance(json_script: dict, tutorial_type: str = "conceptual") -> dict:
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
    structured_llm = llm.with_structured_output(ComplianceResults)
    
    # Build the prompt
    prompt = f"""You are a Spoken Tutorial script reviewer. Evaluate this script against the official compliance checklist.

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
7. **75% Demonstration**: Is at least 75% of the content focused on hands-on demonstration (not just theory)?
    - SKIP this check for: Learning Objectives, System Requirements, Prerequisites, Summary, Assignment, and Thank You slides
    - These slides typically have bullet points that naturally exceed 80 characters
    - Only check content/demonstration slides

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
    
13. **New Lines**: Each sentence must start on a new line (\\n between sentences).
    - Multiple sentences on the same line = FAILED
    
14. **No Forbidden Symbols**: Check narration for forbidden symbols:
    - FORBIDDEN: ->, -->, *, - at the start of lines
    - ALLOWED: **bold** markers are OK
    - ALLOWED: • bullets ONLY in Learning Objectives slide

For each check, provide:
- passed: true/false
- notes: Brief explanation (specific issue if failed, or "OK" if passed)
"""

    try:
        result = structured_llm.invoke(prompt)
        
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
            _format_check("demo_percentage", "Is 75% of the tutorial devoted to demonstration?", result.demo_75_percent),
            _format_check("sufficient_slides", "Are there sufficient slides for the content?", result.sufficient_slides),
            _format_check("recap", "Is a quick recap given at the end of the script?", result.recap_at_end),
            _format_check("visual_narration", "Are Visual Cues consistent with Narration?", result.visual_narration_consistent),
            _format_check("ready_for_review", "Is the script ready for Novice and Domain review?", result.ready_for_review),
        ]
        
        # Formatting criteria
        formatting_checks = [
            _format_check("sentence_length", "Every sentence ≤80 characters (skip LO/Thank You)?", result.sentence_length),
            _format_check("new_lines", "Each sentence starts on a new line?", result.new_lines),
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
