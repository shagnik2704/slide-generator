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


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences using regex.
    Handles common abbreviations and edge cases.
    """
    if not text:
        return []
    
    import re
    # Split on sentence-ending punctuation followed by space or end of string
    # Handles ., !, ? but avoids splitting on abbreviations like "e.g." or "Dr."
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    
    # Filter out empty sentences and strip whitespace
    return [s.strip() for s in sentences if s.strip()]


class SentencePrompt(BaseModel):
    """Schema for a single sentence's enhanced prompt."""
    index: int = Field(description="The sentence index within the row (0-indexed)")
    text: str = Field(description="The original sentence text from the narration")
    enhanced: Optional[str] = Field(description="The enhanced prompt for image generation")


class EnhancedPrompt(BaseModel):
    """Schema for a single enhanced prompt with sentence-level data."""
    slide_number: int = Field(description="The slide/row number (1-indexed)")
    title: str = Field(description="The slide title")
    original: str = Field(description="The original visual cue from the script")
    narration: str = Field(default="", description="The full narration text")
    sentences: List[SentencePrompt] = Field(default_factory=list, description="Sentence-level prompts")
    skip_reason: Optional[str] = Field(description="Reason for skipping, if applicable")


def is_boilerplate(prompt: str) -> bool:
    """Check if a prompt is a boilerplate slide that should be skipped."""
    if not prompt:
        return False  # Empty prompts are NOT boilerplate - let user add one
    prompt_lower = prompt.lower().strip()
    return any(bp in prompt_lower for bp in BOILERPLATE_PROMPTS)


def enhance_prompts(json_script: dict, project_id: Optional[int] = None) -> dict:
    """
    Enhance visual cues from a script using Gemini LLM.
    Now generates prompts for each SENTENCE within a row's narration.
    
    Args:
        json_script: The parsed script JSON with slides containing image_prompt fields
        project_id: Optional project ID for tracking
    
    Returns:
        Dictionary with enhanced_prompts list containing sentence-level data
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
        narration = slide.get('narration', '')
        
        if is_boilerplate(original_prompt):
            skip_results.append({
                "slide_number": slide_number,
                "title": title,
                "original": original_prompt,
                "narration": narration,
                "sentences": [],
                "skip_reason": "Boilerplate slide (no image needed)"
            })
        else:
            # Split narration into sentences
            sentences = split_into_sentences(narration)
            
            if not sentences:
                # No sentences found, use the visual cue as a single item
                sentences = [original_prompt or "(No narration)"]
            
            slides_to_enhance.append({
                "slide_number": slide_number,
                "title": title,
                "original": original_prompt or "(No visual cue)",
                "narration": narration,
                "sentences": [{"index": idx, "text": sent} for idx, sent in enumerate(sentences)]
            })
    
    if not slides_to_enhance:
        return {"enhanced_prompts": skip_results, "project_id": project_id}
    
    # Call LLM to enhance prompts - now sentence-level
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    
    # Import shared system prompt for enhancement
    from src.services.image_styles import ENHANCEMENT_SYSTEM_PROMPT
    
    # Build sentence-level prompt data for LLM
    sentence_data = []
    for slide in slides_to_enhance:
        for sent in slide["sentences"]:
            sentence_data.append({
                "slide_number": slide["slide_number"],
                "sentence_index": sent["index"],
                "visual_cue": slide["original"],
                "sentence": sent["text"]
            })
    
    system_prompt = ENHANCEMENT_SYSTEM_PROMPT + """

IMPORTANT: You are now generating image prompts for INDIVIDUAL SENTENCES.
Each input has a visual_cue (context) and a sentence (the specific action/scene to visualize).
Generate a unique, detailed prompt for each sentence that:
- Captures the specific action or concept in that sentence
- Uses the visual_cue as stylistic/contextual guidance
- Creates visual continuity within the same slide_number
"""

    human_prompt = f"""Create image generation prompts for each sentence below.
Each entry has a slide_number, sentence_index, visual_cue (context), and sentence (to visualize).

{json.dumps(sentence_data, indent=2)}

Return a JSON object with this structure:
{{
  "sentence_prompts": [
    {{"slide_number": 1, "sentence_index": 0, "enhanced": "detailed prompt here"}},
    {{"slide_number": 1, "sentence_index": 1, "enhanced": "detailed prompt here"}},
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
        
        # Build a map: (slide_number, sentence_index) -> enhanced prompt
        enhanced_map = {}
        for sp in enhanced_data.get("sentence_prompts", []):
            key = (sp["slide_number"], sp["sentence_index"])
            enhanced_map[key] = sp["enhanced"]
        
        # Merge enhanced results with original data
        enhanced_results = []
        total_sentences = 0
        for slide_info in slides_to_enhance:
            slide_num = slide_info["slide_number"]
            sentences_with_prompts = []
            
            for sent in slide_info["sentences"]:
                key = (slide_num, sent["index"])
                sentences_with_prompts.append({
                    "index": sent["index"],
                    "text": sent["text"],
                    "enhanced": enhanced_map.get(key, sent["text"])  # Fallback to sentence text
                })
                total_sentences += 1
            
            enhanced_results.append({
                "slide_number": slide_num,
                "title": slide_info["title"],
                "original": slide_info["original"],
                "narration": slide_info["narration"],
                "sentences": sentences_with_prompts,
                "skip_reason": None
            })
        
        # Combine skipped and enhanced, sort by slide number
        all_results = skip_results + enhanced_results
        all_results.sort(key=lambda x: x["slide_number"])
        
        return {
            "enhanced_prompts": all_results,
            "project_id": project_id,
            "total_slides": len(slides),
            "total_sentences": total_sentences,
            "enhanced_count": len(enhanced_results),
            "skipped_count": len(skip_results)
        }
        
    except Exception as e:
        print(f"Error enhancing prompts: {e}")
        # Fallback: return sentences without enhancement
        fallback_results = []
        for slide_info in slides_to_enhance:
            sentences_fallback = [
                {"index": sent["index"], "text": sent["text"], "enhanced": sent["text"]}
                for sent in slide_info["sentences"]
            ]
            fallback_results.append({
                "slide_number": slide_info["slide_number"],
                "title": slide_info["title"],
                "original": slide_info["original"],
                "narration": slide_info["narration"],
                "sentences": sentences_fallback,
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
            "warning": f"LLM enhancement failed, using original sentences: {str(e)}"
        }

