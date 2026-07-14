"""Beamer slides generation route handler."""
from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path
import zipfile
import traceback

from src.api.auth import get_current_user, TokenData

router = APIRouter(tags=["slides"])


@router.post("/generate_slides")
async def generate_slides_endpoint(data: dict, current_user: TokenData = Depends(get_current_user)):
    """
    Generate a Beamer LaTeX template for presentation slides.
    
    Uses LLM-powered content extraction to intelligently parse scripts
    with context-aware intro phrasing (e.g., "learn to" vs "learn how to").
    
    Args:
        json_script: Optional - parsed script to extract content from
        tutorial_name: Name of the tutorial (optional, defaults to "Tutorial Name")
        num_content_slides: Number of blank content slides (optional, defaults to 10)
    
    Returns:
        tex_content: The complete LaTeX file content
        filename: Suggested filename for download
        zip_url: URL to download ZIP with .tex and assets
    """
    print("🎴 Generating Beamer slides template...")
    
    try:
        json_script = data.get('json_script')
        tutorial_name = data.get('tutorial_name', 'Tutorial Name')
        
        # Initialize template parameters
        template_params = {
            "tutorial_name": tutorial_name,
        }
        
        # Extract content from script using LLM if provided
        if json_script:
            print("🤖 Using LLM for intelligent content extraction...")
            
            from src.services.content_extractor import extract_slide_content_with_fallback
            extracted = extract_slide_content_with_fallback(json_script)
            
            # Update template params with extracted content
            template_params.update({
                "tutorial_name": extracted.get("tutorial_name", tutorial_name),
                "learning_objectives": extracted.get("learning_objectives"),
                "learning_objectives_intro": extracted.get("learning_objectives_intro"),
                "prerequisites": extracted.get("prerequisites"),
                "prerequisites_intro": extracted.get("prerequisites_intro"),
                "prerequisites_footer": extracted.get("prerequisites_footer"),
                "system_requirements": extracted.get("system_requirements"),
                "system_requirements_intro": extracted.get("system_requirements_intro"),
                "summary_points": extracted.get("summary_points"),
                "summary_intro": extracted.get("summary_intro"),
                "assignment_items": extracted.get("assignment_items"),
                "assignment_intro": extracted.get("assignment_intro"),
                "domain_expert": extracted.get("domain_expert"),
                "domain_expert_org": extracted.get("domain_expert_org"),
                "code_file_info": extracted.get("code_file_info"),
            })
            
            print(f"📝 LLM Extracted: LO={extracted.get('learning_objectives') is not None}, "
                  f"Prereq={extracted.get('prerequisites') is not None}, "
                  f"Summary={extracted.get('summary_points') is not None}, "
                  f"Assignment={extracted.get('assignment_items') is not None}")
            print(f"📝 Intro phrases: LO='{extracted.get('learning_objectives_intro', '')[:50]}...'")
        
        from src.services.beamer_service import generate_beamer_template
        tex_content = generate_beamer_template(**template_params)
        
        # Generate a safe filename
        safe_name = template_params["tutorial_name"].replace(' ', '_').replace('/', '-')[:50]
        tex_filename = f"{safe_name}_slides.tex"
        zip_filename = f"{safe_name}_slides.zip"
        
        # Create ZIP file with .tex and logo
        # Get project root for static assets
        project_root = Path(__file__).parent.parent.parent.parent
        logo_path = project_root / "static" / "logo.png"
        
        # Create output directory if needed
        output_dir = project_root / "output" / "slides"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        zip_path = output_dir / zip_filename
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add the .tex file
            zipf.writestr(tex_filename, tex_content)
            
            # Add the logo if it exists
            if logo_path.exists():
                zipf.write(logo_path, "logo.png")
            else:
                print(f"⚠️ Logo not found at {logo_path}")
        
        auto_filled = json_script is not None
        print(f"✅ Generated Beamer ZIP: {zip_filename}" + (" (LLM-extracted)" if auto_filled else ""))
        
        return {
            "tex_content": tex_content,
            "filename": tex_filename,
            "zip_filename": zip_filename,
            "zip_url": f"/output/slides/{zip_filename}",
            "num_boilerplate_slides": 8,  # Title, LO, SysReq, Prereq, Code, Summary, Assignment, Thanks
            "auto_filled": auto_filled
        }
        
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in generate_slides: {e}")
        raise HTTPException(status_code=500, detail=str(e))
