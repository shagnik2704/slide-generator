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
                "narration": slide.get('narration', ''),
                "enhanced": None,
                "skip_reason": "Boilerplate slide (no image needed)"
            })
        elif not original_prompt:
            skip_results.append({
                "slide_number": slide_number,
                "title": title,
                "original": "",
                "narration": slide.get('narration', ''),
                "enhanced": None,
                "skip_reason": "No visual cue provided"
            })
        else:
            slides_to_enhance.append({
                "slide_number": slide_number,
                "title": title,
                "original": original_prompt,
                "narration": slide.get('narration', '')
            })
    
    if not slides_to_enhance:
        return {"enhanced_prompts": skip_results, "project_id": project_id}
    
    # Call LLM to enhance prompts
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    
    # Import shared system prompt for enhancement
    from src.services.image_styles import ENHANCEMENT_SYSTEM_PROMPT
    system_prompt = ENHANCEMENT_SYSTEM_PROMPT

    human_prompt = f"""Create image generation prompts for these slides:

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
                "narration": slide_info.get("narration", ""),
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
                "narration": slide_info.get("narration", ""),
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
