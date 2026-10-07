"""
LLM-powered content extraction for Beamer slide templates.
Intelligently extracts and cleans content from JSON scripts with context-aware intro phrasing.
"""
import os
import json
import time
from typing import List, Optional, Tuple, Any
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from src.core.metrics import (
    SLIDE_EXTRACTION_DURATION_SECONDS,
    SLIDE_EXTRACTION_FALLBACK_TOTAL,
)


class SectionContent(BaseModel):
    """Content for a slide section with intro phrase and items."""
    intro: str = Field(description="The intro phrase for this section (e.g., 'In this tutorial, you will learn to')")
    items: List[str] = Field(description="Clean bullet point items without any intro text")


class ExtractedSlideContent(BaseModel):
    """Structured output for complete slide content extraction."""
    
    tutorial_name: str = Field(
        description="Clean tutorial name without trailing punctuation or markdown"
    )
    
    learning_objectives: SectionContent = Field(
        description="Learning objectives with context-appropriate intro (learn to/learn how to/learn about/understand)"
    )
    
    prerequisites: SectionContent = Field(
        description="Prerequisites with appropriate intro phrase"
    )
    
    prerequisites_footer: Optional[str] = Field(
        default=None,
        description="Footer text like 'For prerequisite tutorials please visit this website' - if present in the script"
    )
    
    system_requirements: SectionContent = Field(
        description="System requirements with appropriate intro phrase"
    )
    
    summary: SectionContent = Field(
        description="Summary points with appropriate intro phrase"
    )
    
    assignment: SectionContent = Field(
        description="Assignment items with appropriate intro phrase"
    )
    
    domain_expert: Optional[str] = Field(
        default=None,
        description="Name of the domain expert if mentioned"
    )
    
    domain_expert_org: Optional[str] = Field(
        default=None,
        description="Organization of the domain expert if mentioned"
    )
    
    code_file_info: Optional[str] = Field(
        default=None,
        description="Code file description if a code file slide exists"
    )


def get_candidate_extractors() -> List[Tuple[str, Any]]:
    """
    Returns prioritized list of LLM candidates for slide extraction:
    1. Sarvam AI (glm5.3) - High performance, fast structured outputs (~2-5s)
    2. OpenAI (gpt-4o-mini / gpt-5.2) - Fast secondary fallback
    3. Google Gemini (gemini-2.5-flash) - Tertiary fallback
    """
    candidates = []

    # 1. Sarvam AI (GLM-5.3)
    sarvam_key = (os.getenv("SARVAM_API_KEY") or "").strip()
    if sarvam_key and not sarvam_key.startswith("mock-"):
        try:
            from langchain_openai import ChatOpenAI
            llm_sarvam = ChatOpenAI(
                model=os.getenv("SARVAM_SLIDES_MODEL", "glm5.3"),
                api_key=sarvam_key,
                base_url="https://api.sarvam.ai/v2",
                default_headers={"api-subscription-key": sarvam_key},
                temperature=0.0,
                timeout=15.0,
                max_retries=1,
            )
            candidates.append(("Sarvam GLM-5.3", llm_sarvam))
        except Exception as e:
            print(f"⚠️ Failed initializing Sarvam LLM: {e}")

    # 2. OpenAI
    openai_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if openai_key and not openai_key.startswith("mock-"):
        try:
            from langchain_openai import ChatOpenAI
            model_name = os.getenv("OPENAI_SLIDES_MODEL", "gpt-4o-mini")
            llm_openai = ChatOpenAI(
                model=model_name,
                api_key=openai_key,
                temperature=0.0,
                timeout=15.0,
                max_retries=1,
            )
            candidates.append((f"OpenAI ({model_name})", llm_openai))
        except Exception as e:
            print(f"⚠️ Failed initializing OpenAI LLM: {e}")

    # 3. Google Gemini
    google_key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
    if google_key and not google_key.startswith("mock-"):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm_gemini = ChatGoogleGenerativeAI(
                model=os.getenv("GEMINI_SLIDES_MODEL", "gemini-2.5-flash"),
                google_api_key=google_key,
                temperature=0.0,
                timeout=15.0,
                max_retries=1,
            )
            candidates.append(("Google Gemini", llm_gemini))
        except Exception as e:
            print(f"⚠️ Failed initializing Gemini LLM: {e}")

    return candidates


def _rule_based_slide_content(json_script: dict) -> ExtractedSlideContent:
    """Rule-based construction of ExtractedSlideContent when LLM is unavailable or fails."""
    fb = _fallback_extraction(json_script)
    return ExtractedSlideContent(
        tutorial_name=fb.get("tutorial_name") or json_script.get("title", "Tutorial"),
        learning_objectives=SectionContent(
            intro=fb.get("learning_objectives_intro") or "In this tutorial, you will learn to",
            items=fb.get("learning_objectives") or ["Sample learning objective"]
        ),
        prerequisites=SectionContent(
            intro=fb.get("prerequisites_intro") or "To follow this tutorial, you should be",
            items=fb.get("prerequisites") or ["familiar with basic concepts"]
        ),
        prerequisites_footer=fb.get("prerequisites_footer"),
        system_requirements=SectionContent(
            intro=fb.get("system_requirements_intro") or "For this tutorial, you will need",
            items=fb.get("system_requirements") or ["A computer with internet connection"]
        ),
        summary=SectionContent(
            intro=fb.get("summary_intro") or "In this tutorial, you learned about",
            items=fb.get("summary_points") or ["Key concepts covered"]
        ),
        assignment=SectionContent(
            intro=fb.get("assignment_intro") or "As an assignment",
            items=fb.get("assignment_items") or ["Practice exercise"]
        ),
        domain_expert=fb.get("domain_expert"),
        domain_expert_org=fb.get("domain_expert_org"),
        code_file_info=fb.get("code_file_info")
    )


def extract_slide_content(json_script: dict) -> ExtractedSlideContent:
    """
    Use LLM to intelligently extract and clean content from a script
    for Beamer template slots.
    
    Args:
        json_script: The parsed script JSON with slides
        
    Returns:
        ExtractedSlideContent with context-aware intro phrases and clean items
    """
    # Convert script to readable format
    script_text = json.dumps(json_script, indent=2)
    
    system_prompt = """You are a content extractor for educational slide presentations (Beamer LaTeX format).

Given a script JSON, extract CLEAN content for template slots.

## CRITICAL RULES

### For Each Section, Extract TWO Parts:
1. **intro**: The FULL introductory sentence(s) that set up the list - include instruction text
2. **items**: ONLY the actual list items (nouns or short action phrases), NOT instruction sentences

### Key Distinction - Intro vs Items:
- **Intro text** = Sentences that explain what to do ("Please install the following applications")
- **Items** = The actual things being listed (application names, topics, steps)

### Intro Phrase Examples (preserve the original wording):
- "In this tutorial, you will learn to" (action-based)
- "In this tutorial, you will learn how to" (process-based)  
- "In this tutorial, you will learn about" (conceptual)
- "In this tutorial, you will understand" (understanding)
- "To follow this tutorial, you should be" (prerequisites)
- "For this tutorial, you will need" (system requirements)
- "In this tutorial, you learned about" (summary)
- "As an assignment, please install the following applications" (assignment with instruction)

### Item Cleaning Rules:
- Remove ALL intro/instruction phrases from items
- Remove bullet markers (•, -, *, ►, etc.)
- Remove numbering (1., 2., etc.)
- Each item should be a standalone noun/phrase that can directly follow \\item in LaTeX

### EXAMPLE 1 - Learning Objectives:
Script says:
"In this tutorial, you will learn how to:
• In this tutorial, we will learn how to:
• Install and uninstall applications"

Extract:
- intro: "In this tutorial, you will learn how to"
- items: ["Install and uninstall applications"]

### EXAMPLE 2 - Assignment (IMPORTANT):
Script says:
"As an assignment,
• Please install the required applications using Ubuntu Software.
• Calculator
• LibreOffice
• GIMP"

Extract:
- intro: "As an assignment, please install the required applications using Ubuntu Software"
- items: ["Calculator", "LibreOffice", "GIMP"]

NOTE: "Please install the required applications..." is an INSTRUCTION, not an item!
The actual items are just the application names.

### EXAMPLE 3 - Summary:
Script says:
"In this tutorial, you learned about:
• How to open Ubuntu Software Center
• Installing applications
• Uninstalling applications"

Extract:
- intro: "In this tutorial, you learned about"
- items: ["How to open Ubuntu Software Center", "Installing applications", "Uninstalling applications"]

### Prerequisites Footer Extraction:
Look for a line in the Prerequisites slide like "For the prerequisite tutorials please visit this website" or similar.
This is a footer line that appears after the bullet items and before the website URL.
Extract this as `prerequisites_footer` if present.

### Domain Expert Extraction:
Look for the "Thank You" slide or "Acknowledgement" slide which typically contains:
- Domain Expert name (e.g., "This tutorial was created by John Smith")
- Organization name (e.g., "from IIT Bombay" or "University of Mumbai")
Extract these if present. The domain expert is usually credited in the closing slide.

### Tutorial Name:
- Remove markdown (**bold**, *italic*)
- Remove trailing punctuation
- Extract clean, readable name"""

    human_prompt = f"""Extract slide content from this script JSON:

```json
{script_text}
```

For each section (learning_objectives, prerequisites, system_requirements, summary, assignment):
1. Extract the EXACT intro phrase used in the script
2. Extract ONLY the clean content items (no intro text, no bullets, no redundancy)

Also extract:
- tutorial_name (clean, no markdown or punctuation)
- domain_expert and domain_expert_org (if mentioned)
- code_file_info (if there's a code file slide)"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]

    candidates = get_candidate_extractors()
    for provider_name, llm in candidates:
        t0 = time.perf_counter()
        try:
            print(f"🤖 Attempting slide content extraction with {provider_name}...")
            structured_llm = llm.with_structured_output(ExtractedSlideContent)
            result = structured_llm.invoke(messages)
            elapsed = time.perf_counter() - t0
            SLIDE_EXTRACTION_DURATION_SECONDS.labels(provider=provider_name).observe(elapsed)
            if result is not None:
                print(f"✅ Slide content extracted successfully with {provider_name}")
                return result
        except Exception as e:
            SLIDE_EXTRACTION_FALLBACK_TOTAL.labels(from_provider=provider_name, to_provider="next").inc()
            print(f"⚠️ Content extraction with {provider_name} failed: {e}. Trying next provider...")

    print("ℹ️ Falling back to rule-based slide content extraction")
    SLIDE_EXTRACTION_FALLBACK_TOTAL.labels(from_provider="llm_candidates", to_provider="rule_based").inc()
    return _rule_based_slide_content(json_script)


def extract_slide_content_with_fallback(json_script: dict) -> dict:
    """
    Extract content with LLM, returning a dictionary suitable for beamer_service.
    
    Falls back to rule-based extraction if LLM fails.
    
    Returns:
        Dictionary with keys matching generate_beamer_template parameters
    """
    try:
        content = extract_slide_content(json_script)
        
        return {
            "tutorial_name": content.tutorial_name,
            "learning_objectives": content.learning_objectives.items,
            "learning_objectives_intro": content.learning_objectives.intro,
            "prerequisites": content.prerequisites.items,
            "prerequisites_intro": content.prerequisites.intro,
            "prerequisites_footer": content.prerequisites_footer,
            "system_requirements": content.system_requirements.items,
            "system_requirements_intro": content.system_requirements.intro,
            "summary_points": content.summary.items,
            "summary_intro": content.summary.intro,
            "assignment_items": content.assignment.items,
            "assignment_intro": content.assignment.intro,
            "domain_expert": content.domain_expert,
            "domain_expert_org": content.domain_expert_org,
            "code_file_info": content.code_file_info,
        }
        
    except Exception as e:
        print(f"⚠️ LLM extraction failed, using fallback: {e}")
        return _fallback_extraction(json_script)


def _fallback_extraction(json_script: dict) -> dict:
    """Rule-based fallback extraction when LLM fails."""
    slides = json_script.get('slides', [])
    
    # Simple extraction with defaults
    result = {
        "tutorial_name": json_script.get('title', 'Tutorial').replace('**', '').strip(),
        "learning_objectives": None,
        "learning_objectives_intro": "In this tutorial, you will learn to",
        "prerequisites": None,
        "prerequisites_intro": "To follow this tutorial, you should be",
        "prerequisites_footer": None,
        "system_requirements": None,
        "system_requirements_intro": "For this tutorial, you will need",
        "summary_points": None,
        "summary_intro": "In this tutorial, you learned about",
        "assignment_items": None,
        "assignment_intro": "As an assignment",
        "domain_expert": None,
        "domain_expert_org": None,
        "code_file_info": None,
    }
    
    # Try to extract from slides
    for slide in slides:
        title = slide.get('title', '').lower()
        narration = slide.get('narration', '')
        
        if 'learning objective' in title and not result['learning_objectives']:
            lines = [l.strip().lstrip('•-*').strip() for l in narration.split('\n') if l.strip()]
            result['learning_objectives'] = [l for l in lines if l and 'tutorial' not in l.lower()][:5]
        
        elif 'prerequisite' in title and not result['prerequisites']:
            lines = [l.strip().lstrip('•-*').strip() for l in narration.split('\n') if l.strip()]
            result['prerequisites'] = [l for l in lines if l and 'tutorial' not in l.lower()][:5]
        
        elif 'system' in title and 'requirement' in title and not result['system_requirements']:
            lines = [l.strip().lstrip('•-*').strip() for l in narration.split('\n') if l.strip()]
            result['system_requirements'] = [l for l in lines if l][:5]
        
        elif 'summary' in title and not result['summary_points']:
            lines = [l.strip().lstrip('•-*').strip() for l in narration.split('\n') if l.strip()]
            result['summary_points'] = [l for l in lines if l and 'tutorial' not in l.lower()][:5]
        
        elif 'assignment' in title and not result['assignment_items']:
            lines = [l.strip().lstrip('•-*').strip() for l in narration.split('\n') if l.strip()]
            result['assignment_items'] = [l for l in lines if l][:5]
        
        # Extract domain expert from Thank You / Acknowledgement slides
        elif ('thank' in title or 'acknowledgement' in title) and not result['domain_expert']:
            # Look for patterns like "Domain Expert: Name" or "created by Name"
            import re
            
            # Try to find domain expert name
            expert_patterns = [
                r'[Dd]omain [Ee]xpert[:\s]+([A-Z][a-zA-Z\s\.]+?)(?:\s+from|\n|$)',
                r'[Cc]reated by[:\s]+([A-Z][a-zA-Z\s\.]+?)(?:\s+from|\n|$)',
                r'[Pp]repared by[:\s]+([A-Z][a-zA-Z\s\.]+?)(?:\s+from|\n|$)',
                r'[Aa]uthor[:\s]+([A-Z][a-zA-Z\s\.]+?)(?:\s+from|\n|$)',
            ]
            for pattern in expert_patterns:
                match = re.search(pattern, narration)
                if match:
                    result['domain_expert'] = match.group(1).rstrip('.').strip()
                    break
            
            # Try to find organization
            org_patterns = [
                r'from\s+([A-Z0-9][a-zA-Z0-9\s,]+?)(?:\.|\n|$)',
                r'([A-Z][a-zA-Z\s]*(?:University|Institute|College|IIT|IIIT|NIT)[a-zA-Z0-9\s,]*)',
            ]
            for pattern in org_patterns:
                match = re.search(pattern, narration)
                if match:
                    result['domain_expert_org'] = match.group(1).rstrip('.').strip()
                    break
    
    return result
