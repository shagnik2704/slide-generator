"""
Merge node for the script generation pipeline.
Combines metadata + boilerplate slides + content slides into final json_script.

Input:
- metadata: ScriptMetadata from metadata_node
- boilerplate_slides: 7 slides from boilerplate_node
- content_slides: Learning content from content_node

Output:
- json_script: Complete script ready for downstream processing
"""
from src.core.state import AgentState


def merge_script(state: AgentState) -> dict:
    """
    Merges all components into the final json_script.
    
    Order:
    1. Title Slide (boilerplate[0])
    2. Learning Objectives (boilerplate[1])
    3. System Requirements (boilerplate[2])
    4. Prerequisites (boilerplate[3])
    5. Content Slides (all from content_node)
    6. Summary (boilerplate[4])
    7. Assignment (boilerplate[5])
    8. Acknowledgement (boilerplate[6])
    """
    print("🔗 Merging script components...")
    
    metadata = state.get('metadata')
    boilerplate_slides = state.get('boilerplate_slides')
    content_slides = state.get('content_slides')
    
    # Validate inputs
    if not metadata:
        print("⚠️ No metadata provided")
        return {"json_script": None}
    
    if not boilerplate_slides or len(boilerplate_slides) < 7:
        print("⚠️ Incomplete boilerplate slides")
        return {"json_script": None}
    
    if not content_slides:
        print("⚠️ No content slides provided")
        return {"json_script": None}
    
    # Build final slide order
    slides = []
    
    # Opening boilerplate (first 4)
    slides.append(boilerplate_slides[0])  # Title
    slides.append(boilerplate_slides[1])  # Learning Objectives
    slides.append(boilerplate_slides[2])  # System Requirements
    slides.append(boilerplate_slides[3])  # Prerequisites
    
    # Content slides
    slides.extend(content_slides)
    
    # Closing boilerplate (last 3)
    slides.append(boilerplate_slides[4])  # Summary
    slides.append(boilerplate_slides[5])  # Assignment
    slides.append(boilerplate_slides[6])  # Acknowledgement
    
    # Build final json_script
    json_script = {
        "presentation_title": metadata.get("presentation_title", ""),
        "module": metadata.get("module", ""),
        "episode": metadata.get("episode", ""),
        "learning_objectives": metadata.get("learning_objectives", []),
        "duration": metadata.get("duration", "3-4 min"),
        "outline": metadata.get("outline", []),
        "meta_tags": metadata.get("meta_tags", []),
        "prerequisites": metadata.get("prerequisites", ""),
        "slides": slides
    }
    
    print(f"✓ Merged script: {len(slides)} total slides")
    print(f"   - 4 opening boilerplate")
    print(f"   - {len(content_slides)} content slides")
    print(f"   - 3 closing boilerplate")
    
    return {"json_script": json_script}
