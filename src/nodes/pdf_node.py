"""
PDF generation nodes (script PDF, LaTeX conversion, compilation).
"""
import os
import subprocess
import shutil
from datetime import datetime
from src.services.pdf_service import create_script_pdf
from src.services.latex_service import escape_latex, get_renderer, get_renderer_by_title
import src.services.latex_service as latex_templates
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from src.core.state import AgentState

def generate_script_pdf(state: AgentState):
    """Generates a PDF for script review."""
    print("Generating script review PDF...")
    json_script = state['json_script']
    
    # Generate unique filename using timestamp
    import time
    from pathlib import Path
    project_id = int(time.time())
    project_root = Path(__file__).parent.parent.parent
    static_dir = project_root / "static"
    
    filename = static_dir / f"script_review_{project_id}.pdf"
    pdf_path = create_script_pdf(json_script, output_filename=str(filename))
    return {"script_pdf_path": pdf_path, "project_id": project_id}

@retry(
    retry=retry_if_exception_type((ResourceExhausted, ServiceUnavailable)),
    wait=wait_exponential(multiplier=4, min=4, max=60),
    stop=stop_after_attempt(5)
)
def generate_images(state: AgentState):
    """Generates images."""
    print("Generating images...")
    json_script = state.get('json_script')
    slides = json_script['slides']
    target_audience = state.get('target_audience', 'general')
    
    if os.path.exists("output/images"):
        shutil.rmtree("output/images")
    os.makedirs("output/images")
    
    # Audience-specific image style prefixes
    audience_style_prefix = {
        'kids': "Hand-drawn crayon sketch, colorful, playful, child-friendly illustration,",
        'students': "Hand-drawn pencil sketch, educational diagram, clear and informative,",
        'professionals': "Minimalist architectural sketch, clean lines, professional, blueprint style,",
        'general': "Artistic ink sketch, hand-drawn illustration, high quality,"
    }
    
    style_prefix = audience_style_prefix.get(target_audience, audience_style_prefix['general'])
    
    api_key = os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
        
    for i, slide in enumerate(slides):
        slide_title = slide.get('title', '').lower()
        
        # Skip image generation for intro and ending slides
        skip_titles = [
            'title slide', 'learning objective', 'system requirement', 
            'prerequisite', 'pre-requisite', 'summary', 'assignment', 
            'thank you', 'thank-you', 'what we did', 'recap'
        ]
        
        should_skip = any(skip in slide_title for skip in skip_titles)
        
        if should_skip:
            print(f"⏭️  Skipping image generation for slide {i+1}: {slide.get('title', 'Untitled')}")
            continue
        
        prompt = slide.get('image_prompt')
        if prompt:
            # Standard Image Generation for content slides only
            prompt = f"{style_prefix} {prompt}"
            try:
                print(f"Generating image for slide {i+1} (Audience: {target_audience})...")
                response = client.models.generate_content(
                    model='gemini-3-pro-image-preview',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=types.ImageConfig(aspect_ratio="1:1"),
                    ),
                )
                if response.parts:
                    for part in response.parts:
                        if part.inline_data:
                            try:
                                generated_image = part.as_image()
                                image_path = str(images_dir / f"slide_{i}.png")
                                generated_image.save(image_path)
                                slide['image_path'] = os.path.abspath(image_path)
                                print(f"✓ Image generated for slide {i+1}")
                                break
                            except Exception as e_img:
                                print(f"Error saving image for slide {i+1}: {e_img}")
                else:
                     print(f"No image parts returned for slide {i+1}")
            except Exception as e:
                print(f"Failed to generate image for slide {i+1}: {e}")
                
    return {"json_script": json_script}

def convert_to_latex(state: AgentState):
    """Converts JSON script to LaTeX using the Template Library."""
    print("Converting JSON to LaTeX with Templates...")
    json_data = state['json_script']
    
    # Escape title
    safe_title = escape_latex(json_data.get('presentation_title', 'Presentation'))
    
    # Get absolute path to logo
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent
    logo_path = project_root / "static" / "logo.png"
    
    latex_content = r"""
\documentclass[17pt,xcolor=table]{beamer} 
\setbeamersize{text margin left=0.75cm,text margin right=0.75cm}

% --- Packages ---
\mathversion{bold}
\usepackage{beamerthemesplit}
\usepackage{graphicx}
\usepackage{tikz}
\usetikzlibrary{calc}

% --- Colors and beamer setup ---
\definecolor{grey}{rgb}{0.44, 0.5, 0.58}
\setbeamercolor{structure}{fg=grey}
\setbeamercolor{alerted text}{fg=grey}

% --- Remove navigation symbols ---
\setbeamertemplate{navigation symbols}{}

% --- Logo is now added per-slide for intro/outro slides only ---
% Content slides with images do NOT show the logo

% --- Title info ---
\title [""" + safe_title + r"""\hspace{0.5cm}]
{""" + safe_title + r"""}\date{}
\author [\ EduPyramids Educational Services Pvt.\ Ltd.]{%
{Spoken Tutorial}\\[5pt]
  { \small brought to you by }\\[5pt]
{EduPyramids Educational Services Pvt.\ Ltd.}\\[10pt]
  { \textcolor{blue}{https://spoken-tutorial.org}}
}
\date{} % empty date

\begin{document}
\sffamily\bfseries

% ---- Title slide ----
\begin{frame}
  \titlepage
\end{frame}
"""
    
    # Slides - skip title slide since titlepage is already rendered above
    for slide in json_data.get('slides', []):
        slide_title = slide.get('title', '').lower()
        
        # Skip title slide (already rendered above)
        if 'title slide' in slide_title:
            continue
        
        # First check if explicit layout is set
        layout = slide.get('layout')
        if layout:
            renderer = latex_templates.get_renderer(layout)
        else:
            # Auto-detect renderer based on slide title
            renderer = latex_templates.get_renderer_by_title(slide.get('title', ''))
        
        latex_content += renderer(slide)
        
    latex_content += r"\end{document}"
    
    return {"latex_content": latex_content}

def compile_pdf(state: AgentState):
    """Compiles LaTeX content to PDF."""
    print("Compiling LaTeX to PDF...")
    latex_content = state['latex_content']
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent
    output_dir = project_root / "output"
    output_dir.mkdir(exist_ok=True)
    output_tex = output_dir / "output.tex"
    
    with open(str(output_tex), "w") as f:
        f.write(latex_content)
        
    try:
        env = os.environ.copy()
        env["PATH"] = f"/Library/TeX/texbin:/usr/local/bin:{env['PATH']}"
        subprocess.run(["pdflatex", "-interaction=nonstopmode", "-file-line-error", "-output-directory", str(output_dir), str(output_tex)], check=True, capture_output=True, env=env)
        
        # Move PDF to static folder with timestamp
        import time
        import shutil
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        static_dir = project_root / "static"
        static_dir.mkdir(exist_ok=True)
        timestamp = int(time.time())
        static_pdf_path = static_dir / f"slides_{timestamp}.pdf"
        
        # Move the compiled PDF to static folder
        output_pdf = output_dir / "output.pdf"
        if output_pdf.exists():
            shutil.move(str(output_pdf), str(static_pdf_path))
            print(f"✅ PDF moved to {static_pdf_path}")
            return {"pdf_path": str(static_pdf_path)}
        else:
            return {"error": "PDF compilation succeeded but output.pdf not found"}
            
    except subprocess.CalledProcessError as e:
        error_msg = e.stdout.decode() if e.stdout else str(e)
        print(f"Error compiling PDF: {error_msg}")
        
        # Log to file for debugging
        with open("latex_error.log", "w") as f:
            f.write(f"Error: {error_msg}\n")
            f.write("-" * 50 + "\n")
            f.write("LaTeX Content:\n")
            f.write(latex_content)
            
        return {"error": f"LaTeX compilation failed: {error_msg}"}
