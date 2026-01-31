"""
Slide Content Node - LLM-powered layout and content extraction.

This node uses Gemini to analyze each slide's narration and:
1. Choose the best layout for the slide
2. Extract appropriate bullet points (or none for image-only slides)
"""

from google import genai
from google.genai import types
import json
import os
from src.core.state import AgentState

# Available layouts the LLM can choose from
AVAILABLE_LAYOUTS = {
    "standard": "Text bullets on left, image on right (default for content slides)",
    "full_image": "Full-screen image with title only, no bullets (for visual/analogy slides)",
    "text_only": "Text bullets only, no image (for info-heavy slides)",
    "two_column": "Image on left, text on right",
    "content_centered": "Centered text, no bullets (for quotes or key points)",
}

# Slides that use fixed templates (skip LLM processing)
FIXED_LAYOUT_SLIDES = {
    'title slide': 'skip',
    'welcome': 'skip',
    'learning objective': 'learning_objectives',
    'system requirement': 'system_requirements',
    'prerequisite': 'prerequisites',
    'pre-requisite': 'prerequisites',
    'summary': 'summary',
    'assignment': 'assignment',
    'thank you': 'thank_you',
    'thank-you': 'thank_you',
}


def generate_slide_content(state: AgentState):
    """
    Uses LLM to analyze each slide's narration and decide layout + bullets.
    """
    print("Generating slide content with LLM...")
    json_script = state['json_script']
    slides = json_script.get('slides', [])
    
    # Metadata for context
    learning_objectives = json_script.get('learning_objectives', [])
    prerequisites = json_script.get('prerequisites', '')
    
    api_key = os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    
    for i, slide in enumerate(slides):
        slide_title = slide.get('title', '').lower()
        narration = slide.get('narration', '')
        
        # Check if this slide uses a fixed template
        fixed_layout = get_fixed_layout(slide_title)
        
        if fixed_layout == 'skip':
            # Title/thank you slides - no content needed
            slide['content'] = []
            slide['layout'] = 'text_only'
            print(f"⏭️  Skipping slide {i+1}: {slide.get('title')}")
            continue
        
        if fixed_layout:
            # Use fixed layout and populate content
            slide['layout'] = fixed_layout
            slide['content'] = get_fixed_content(
                fixed_layout, narration, learning_objectives, prerequisites
            )
            print(f"📋 Fixed layout for slide {i+1}: {fixed_layout}")
            continue
        
        # For content slides, use LLM to decide layout and extract bullets
        try:
            result = analyze_slide_with_llm(client, slide.get('title', ''), narration)
            slide['layout'] = result.get('layout', 'standard')
            slide['content'] = result.get('bullets', [])
            print(f"🤖 LLM decided for slide {i+1}: layout={result.get('layout')}, {len(result.get('bullets', []))} bullets")
        except Exception as e:
            print(f"⚠️  LLM error for slide {i+1}, using fallback: {e}")
            slide['layout'] = 'standard'
            slide['content'] = extract_bullets_fallback(narration)
    
    return {"json_script": json_script}


def get_fixed_layout(slide_title: str):
    """Returns fixed layout for template slides, or None for content slides."""
    for pattern, layout in FIXED_LAYOUT_SLIDES.items():
        if pattern in slide_title:
            return layout
    return None


def get_fixed_content(layout, narration, learning_objectives, prerequisites):
    """Populates content for fixed-template slides."""
    if layout == 'learning_objectives':
        return learning_objectives if learning_objectives else extract_bullets_fallback(narration)
    
    if layout == 'prerequisites':
        if prerequisites:
            return [p.strip() for p in prerequisites.split('.') if p.strip() and len(p.strip()) > 3]
        return extract_bullets_fallback(narration)
    
    if layout in ['summary', 'assignment', 'system_requirements']:
        return extract_bullets_fallback(narration)
    
    return []


def analyze_slide_with_llm(client, title: str, narration: str) -> dict:
    """
    Calls Gemini to analyze a slide and decide layout + generate bullet content.
    """
    prompt = f"""Analyze this slide and decide the best layout. Then GENERATE concise bullet points that summarize the key concepts.

SLIDE TITLE: {title}

NARRATION (context only - DO NOT copy verbatim):
{narration}

AVAILABLE LAYOUTS:
- "standard": Text bullets on left, image on right (best for explaining concepts with supporting visual)
- "full_image": Full-screen centered image, title only, NO bullets (best for visual demos, analogies, or "let's see" moments)
- "text_only": Text bullets only, no image (best for info-heavy slides)
- "two_column": Image on left, text on right (alternative layout)

DECISION RULES:
1. If narration contains "imagine", "picture this", "let's see", or is about a visual example → use "full_image"
2. If narration has 3+ distinct points to explain → use "standard" with bullets
3. If slide is very info-heavy with many facts → use "text_only"

BULLET GENERATION RULES:
- DO NOT copy text from the narration verbatim
- GENERATE concise  points that SUMMARIZE the key concepts
- Each point: SHORT (under 50 characters), punchy, keyword-focused
- Use noun phrases or short statements, not full sentences
- Example: "Clear instructions = Better results" instead of copying narration
- If layout is "full_image", points should be empty []

Respond with ONLY valid JSON:
{{"layout": "standard|full_image|text_only|two_column", "points": ["Point 1", "Point 2"]}}
"""
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",                      
            response_schema={
                "type": "object",
                "properties": {
                    "layout": {"type": "string"},
                    "points": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["layout", "points"]
            }
        )
    )
    
    result_text = response.text.strip()
    return json.loads(result_text)


def extract_bullets_fallback(narration: str, max_bullets: int = 4) -> list:
    """Fallback bullet extraction using simple heuristics."""
    if not narration:
        return []
    
    sentences = narration.replace('\\n', '\n').split('\n')
    sentences = [s.strip() for s in sentences if s.strip()]
    
    skip_patterns = [
        'welcome', 'thank you', 'hello', 'let us', "let's", 
        'in this tutorial', 'we will learn', 'we learned',
        'as an assignment', 'please do', 'this spoken tutorial'
    ]
    
    bullets = []
    for sentence in sentences:
        sentence_lower = sentence.lower()
        
        if any(pattern in sentence_lower for pattern in skip_patterns):
            continue
        
        if len(sentence) < 15:
            continue
        
        # Clean up - keep bullets reasonably sized but not truncated prematurely
        bullet = sentence.replace('**', '')
        if len(bullet) > 150:
            break_point = bullet[:150].rfind(' ')
            if break_point > 80:
                bullet = bullet[:break_point] + '...'
        
        bullets.append(bullet.strip())
        
        if len(bullets) >= max_bullets:
            break
    
    return bullets
