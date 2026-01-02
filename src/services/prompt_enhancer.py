"""
Prompt enhancement service for image generation.
Uses Gemini LLM to expand short visual cues into detailed image prompts.
"""
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
import json

load_dotenv()

# Boilerplate prompts that should be skipped (no image generation needed)
BOILERPLATE_PROMPTS = [
    "title slide",
    "learning objectives slide",
    "learning objectives",
    "system requirements slide",
    "system requirements",
    "pre-requisite slide",
    "prerequisite slide",
    "summary slide",
    "assignment slide",
    "thank you slide",
    "thank you",
    "edupyramids logo",
]


class EnhancedPrompt(BaseModel):
    """Schema for a single enhanced prompt."""
    slide_number: int = Field(description="The slide/row number (1-indexed)")
    title: str = Field(description="The slide title")
    original: str = Field(description="The original visual cue from the script")
    enhanced: Optional[str] = Field(description="The enhanced prompt for image generation, or null if skipped")
    skip_reason: Optional[str] = Field(description="Reason for skipping, if applicable")


class EnhancedPromptsResponse(BaseModel):
    """Schema for the batch response."""
    enhanced_prompts: List[EnhancedPrompt] = Field(description="List of enhanced prompts for each slide")


def is_boilerplate(prompt: str) -> bool:
    """Check if a prompt is a boilerplate slide that should be skipped."""
    if not prompt:
        return True
    prompt_lower = prompt.lower().strip()
    return any(bp in prompt_lower for bp in BOILERPLATE_PROMPTS)


def enhance_prompts(json_script: dict, project_id: Optional[int] = None) -> dict:
    """
    Enhance visual cues from a script using Gemini LLM.
    
    Args:
        json_script: The parsed script JSON with slides containing image_prompt fields
        project_id: Optional project ID for tracking
    
    Returns:
        Dictionary with enhanced_prompts list
    """
    slides = json_script.get('slides', [])
    
    if not slides:
        return {"enhanced_prompts": [], "project_id": project_id}
    
    # Collect slides that need enhancement
    slides_to_enhance = []
    skip_results = []
    
    for i, slide in enumerate(slides):
        slide_number = i + 1
        title = slide.get('title', f'Slide {slide_number}')
        original_prompt = slide.get('image_prompt', '')
        
        if is_boilerplate(original_prompt):
            skip_results.append({
                "slide_number": slide_number,
                "title": title,
                "original": original_prompt,
                "enhanced": None,
                "skip_reason": "Boilerplate slide (no image needed)"
            })
        elif not original_prompt:
            skip_results.append({
                "slide_number": slide_number,
                "title": title,
                "original": "",
                "enhanced": None,
                "skip_reason": "No visual cue provided"
            })
        else:
            slides_to_enhance.append({
                "slide_number": slide_number,
                "title": title,
                "original": original_prompt,
                "narration": slide.get('narration', '')[:200]  # Include context (truncated)
            })
    
    if not slides_to_enhance:
        return {"enhanced_prompts": skip_results, "project_id": project_id}
    
    # Call LLM to enhance prompts
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    
    system_prompt = """You are an expert at writing image generation prompts for educational tutorials.

Given short visual cues from a Spoken Tutorial script, expand them into detailed, high-quality prompts suitable for AI image generation.

=== STYLE RULES (IMPORTANT) ===

**FOR SOFTWARE/SCREENSHOTS/UI:**
- Keep realistic, professional software aesthetic
- Describe UI elements, colors, layout accurately
- Example: "A clean screenshot of VS Code with Python code visible, dark theme, blue sidebar"

**FOR PEOPLE/CONCEPTS/ABSTRACT:**
- Use FLAT STYLE GRAPHIC  (NOT photorealistic)
- Think: modern educational illustrations, 2D vector art, simple cartoon characters
- Avoid: realistic humans, stock photo aesthetics
- Example: "Flat design illustration of a friendly cartoon developer at a laptop, vibrant colors, simple shapes"

=== GENERAL RULES ===
1. Keep the educational context in mind
2. Add visual details: composition, colors, mood
3. For screenshots: describe the software interface accurately
4. For people: use "flat design illustration", "cartoon character", "2D vector style"
5. For concepts: use "educational infographic", "simple icon-based illustration"
6. Do NOT include any text that should appear in the image (AI generators are bad at text)

Return a JSON array with enhanced prompts for each slide."""

    human_prompt = f"""Enhance these visual cues into detailed image generation prompts:

{json.dumps(slides_to_enhance, indent=2)}

Return a JSON object with this structure:
{{
  "enhanced_prompts": [
    {{"slide_number": 1, "enhanced": "detailed prompt here"}},
    ...
  ]
}}"""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ])
        
        # Parse LLM response
        response_text = response.content.strip()
        
        # Extract JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        enhanced_data = json.loads(response_text)
        
        # Merge enhanced results with original data
        enhanced_map = {ep["slide_number"]: ep["enhanced"] for ep in enhanced_data.get("enhanced_prompts", [])}
        
        enhanced_results = []
        for slide_info in slides_to_enhance:
            slide_num = slide_info["slide_number"]
            enhanced_results.append({
                "slide_number": slide_num,
                "title": slide_info["title"],
                "original": slide_info["original"],
                "enhanced": enhanced_map.get(slide_num, slide_info["original"]),
                "skip_reason": None
            })
        
        # Combine skipped and enhanced, sort by slide number
        all_results = skip_results + enhanced_results
        all_results.sort(key=lambda x: x["slide_number"])
        
        return {
            "enhanced_prompts": all_results,
            "project_id": project_id,
            "total_slides": len(slides),
            "enhanced_count": len(enhanced_results),
            "skipped_count": len(skip_results)
        }
        
    except Exception as e:
        print(f"Error enhancing prompts: {e}")
        # Fallback: return originals as enhanced
        fallback_results = []
        for slide_info in slides_to_enhance:
            fallback_results.append({
                "slide_number": slide_info["slide_number"],
                "title": slide_info["title"],
                "original": slide_info["original"],
                "enhanced": slide_info["original"],  # Use original as fallback
                "skip_reason": None
            })
        
        all_results = skip_results + fallback_results
        all_results.sort(key=lambda x: x["slide_number"])
        
        return {
            "enhanced_prompts": all_results,
            "project_id": project_id,
            "total_slides": len(slides),
            "enhanced_count": len(fallback_results),
            "skipped_count": len(skip_results),
            "warning": f"LLM enhancement failed, using original prompts: {str(e)}"
        }
