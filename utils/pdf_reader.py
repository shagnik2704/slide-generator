"""
Utility to extract text from PDF sample scripts.
"""
import os
from pathlib import Path

def load_sample_scripts(sample_dir="sample_scripts"):
    """
    Load text content from sample script PDFs.
    Returns a string containing all sample scripts concatenated.
    """
    try:
        import PyPDF2
    except ImportError:
        print("⚠ PyPDF2 not installed. Install with: pip install PyPDF2")
        return ""
    
    sample_path = Path(sample_dir)
    if not sample_path.exists():
        print(f"⚠ Sample scripts directory not found: {sample_dir}")
        return ""
    
    pdf_files = list(sample_path.glob("*.pdf"))
    if not pdf_files:
        print(f"⚠ No PDF files found in {sample_dir}")
        return ""
    
    all_samples = []
    
    for pdf_file in pdf_files[:2]:  # Limit to 2 samples to avoid token limits
        try:
            with open(pdf_file, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text_content = []
                
                # Extract text from all pages
                for page in pdf_reader.pages:
                    text_content.append(page.extract_text())
                
                sample_text = "\n".join(text_content)
                all_samples.append(f"=== SAMPLE SCRIPT: {pdf_file.name} ===\n{sample_text}\n")
                print(f"✓ Loaded sample: {pdf_file.name} ({len(sample_text)} chars)")
                
        except Exception as e:
            print(f"⚠ Error reading {pdf_file.name}: {e}")
            continue
    
    return "\n\n".join(all_samples)


def load_sample_scripts_as_json(sample_dir="sample_scripts/json", max_samples=4):
    """
    Load sample scripts from JSON files for few-shot prompting.
    Returns a formatted string containing complete example scripts.
    """
    sample_path = Path(sample_dir)
    if not sample_path.exists():
        print(f"⚠ Sample JSON directory not found: {sample_dir}")
        return ""
    
    json_files = list(sample_path.glob("*.json"))
    if not json_files:
        print(f"⚠ No JSON files found in {sample_dir}")
        return ""
    
    all_samples = []
    
    for json_file in json_files[:max_samples]:  # Limit to avoid token limits
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                script_data = json.load(f)
            
            # Format as a complete example script
            sample_text = f"""
=== COMPLETE EXAMPLE SCRIPT: {script_data.get('presentation_title', json_file.name)} ===

**MATCH THIS STYLE EXACTLY:**

METADATA:
- Module: {script_data.get('module', 'N/A')}
- Episode: {script_data.get('episode', 'N/A')}
- Learning Objectives: {', '.join(script_data.get('learning_objectives', []))}
- Duration: {script_data.get('duration', 'N/A')}
- Prerequisites: {script_data.get('prerequisites', 'N/A')}

ALL SLIDES:
"""
            # Load ALL slides (complete script)
            for i, slide in enumerate(script_data.get('slides', []), start=1):
                title = slide.get('title', '') or 'Untitled'
                sample_text += f"\n\nSlide {i}: {title}\n"
                sample_text += f"Visual Cue: {slide.get('image_prompt', 'N/A')}\n"
                sample_text += f"Narration: {slide.get('narration', 'N/A')}\n"
            
            sample_text += "\n\n**KEY PATTERNS TO MATCH:**\n"
            sample_text += "- Short sentences (5-10 words)\n"
            sample_text += "- Conversational, friendly tone\n"
            sample_text += "- Smooth transitions between slides\n"
            sample_text += "- Each sentence on a new line (\\n)\n"
            sample_text += "- Simple analogies for complex concepts\n"
            
            all_samples.append(sample_text)
            print(f"✓ Loaded sample: {json_file.name}")
            
        except Exception as e:
            print(f"⚠ Error loading {json_file.name}: {e}")
            continue
    
    return "\n\n".join(all_samples)


import json

def get_sample_script_summary():
    """Returns a concise summary of sample script standards without full text."""
    return """
REFERENCE STANDARDS (from sample scripts):

**Structure:**
- Metadata table (Module, Episode, Learning Objectives, Duration, Outline, Meta Tags, Prerequisites)
- Title slide with clean introduction
- 8-12 content slides with consistent format
- Assignment slide at the end

**Visual Cues:**
- Use CARTOONISH, ILLUSTRATED, SIMPLE visual descriptions
- Avoid photorealistic or abstract imagery
- Prefer relatable analogies (parent-child, classroom, everyday scenarios)
- Include transitions and animations where appropriate
- Each slide should have distinct, memorable visuals

**Narration Style:**
- Conversational tone, short sentences (10-15 words ideal)
- Active voice, direct address to viewer
- Use rhetorical questions and smooth transitions
- Natural flow, avoid robotic or overly formal language
- Clear pauses between concepts

**Content Quality:**
- Progressive difficulty (hook → develop → compare → apply)
- Real-world examples and practical applications
- Balance theory with hands-on demonstration
- Clear section headers for each slide
- 3-5 bullet points per slide maximum
"""
