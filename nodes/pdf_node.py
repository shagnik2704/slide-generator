"""
PDF generation nodes (script PDF, LaTeX conversion, compilation).
"""
import os
import subprocess
from datetime import datetime
from script_pdf_generator import create_script_pdf
from latex_templates import render_standard, render_split_vertical, render_quote, render_immersive, render_big_number, escape_latex
import latex_templates
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from models.state import AgentState

def generate_script_pdf(state: AgentState):
    """Generates a PDF for script review."""
    print("Generating script review PDF...")
    json_script = state['json_script']
    project_id = state.get('project_id', 'temp')
    
    filename = f"static/script_review_{project_id}.pdf"
    pdf_path = create_script_pdf(json_script, output_filename=filename)
    return {"script_pdf_path": pdf_path}

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
    
    if os.path.exists("generated_images"):
        shutil.rmtree("generated_images")
    os.makedirs("generated_images")
    
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
        prompt = slide.get('image_prompt')
        if prompt:
            # Check if this is a video slide
            if slide.get('is_video_slide'):
                try:
                    # Use dedicated video prompt if available, otherwise fallback to image prompt
                    raw_video_prompt = slide.get('video_prompt') or prompt
                    print(f"Generating VIDEO for slide {i+1} (Audience: {target_audience}) using Veo...")
                    video_prompt = f"{style_prefix} {raw_video_prompt}. Cinematic, smooth motion, high quality."
                    
                    # Use generate_videos instead of generate_content
                    operation = client.models.generate_videos(
                        model='veo-3.1-generate-preview',
                        prompt=video_prompt,
                    )
                    print(f"Operation started: {operation.name}")
                    
                    # Poll for completion
                    while True:
                        time.sleep(5)
                        print(".", end="", flush=True)
                        op_status = client.operations.get(operation)
                        if op_status.done:
                            print("\nOperation done!")
                            if op_status.result:
                                video_uri = op_status.result.generated_videos[0].video.uri
                                print(f"Downloading video from {video_uri}...")
                                
                                # Download video
                                import requests
                                headers = {"x-goog-api-key": api_key}
                                vid_response = requests.get(video_uri, headers=headers)
                                
                                if vid_response.status_code == 200:
                                    video_path = f"generated_images/slide_{i}.mp4"
                                    with open(video_path, "wb") as f:
                                        f.write(vid_response.content)
                                    slide['image_path'] = os.path.abspath(video_path)
                                    print(f"✓ Video generated for slide {i+1}")
                                else:
                                    raise Exception(f"Failed to download video: {vid_response.status_code}")
                            else:
                                raise Exception("Operation completed but no result returned")
                            break
                    
                except Exception as e:
                    print(f"Failed to generate video for slide {i+1}: {e}")
                    # Fallback to image generation if video fails
                    print("Falling back to image generation...")
                    try:
                        prompt = f"{style_prefix} {prompt}"
                        response = client.models.generate_content(
                            model='gemini-2.5-flash-image',
                            contents=prompt,
                        config=types.GenerateContentConfig(
                            response_modality=["IMAGE"],
                            image_config=types.ImageConfig(aspect_ratio="1:1"),
                        ),
                        )
                        if response.parts:
                            for part in response.parts:
                                if part.inline_data:
                                    try:
                                        generated_image = part.as_image()
                                        image_path = f"generated_images/slide_{i}.png"
                                        generated_image.save(image_path)
                                        slide['image_path'] = os.path.abspath(image_path)
                                        print(f"✓ Fallback image generated for slide {i+1}")
                                        break
                                    except Exception as e_img:
                                        print(f"Error saving fallback image for slide {i+1}: {e_img}")
                        else:
                            print(f"No image parts returned for fallback slide {i+1}")
                    except Exception as e2:
                        print(f"Failed to generate fallback image for slide {i+1}: {e2}")

            else:
                # Standard Image Generation
                prompt = f"{style_prefix} {prompt}"
                try:
                    print(f"Generating image for slide {i+1} (Audience: {target_audience})...")
                    response = client.models.generate_content(
                        model='gemini-2.5-flash-image',
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
                                    image_path = f"generated_images/slide_{i}.png"
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

from latex_templates import (
    render_standard, render_split_vertical, render_quote, 
    render_immersive, render_big_number, escape_latex
)

def convert_to_latex(state: AgentState):
    """Converts JSON script to LaTeX using the Template Library."""
    print("Converting JSON to LaTeX with Templates...")
    json_data = state['json_script']
    
    # Escape title
    safe_title = escape_latex(json_data.get('presentation_title', 'Presentation'))
    
    # Date Format: Day Month Year (e.g., 29 November 2025)
    current_date = datetime.now().strftime("%d %B %Y")
    
    latex_content = r"""
\documentclass[17pt]{beamer}
\usepackage{graphicx}
\usepackage{tikz}
\usetheme{Madrid}
\usecolortheme{default}

% Remove navigation symbols
\setbeamertemplate{navigation symbols}{}

% Remove footer (slide numbers)
\setbeamertemplate{footline}{}

\title{""" + safe_title + r"""}
\author{Madhulika Goyal \\ IIT Bombay}
\date{""" + current_date + r"""}

% Global Background Logo (Bottom Right)
\addtobeamertemplate{background canvas}{}{
    \begin{tikzpicture}[remember picture,overlay]
        \node[anchor=south east, inner sep=0.5cm] at (current page.south east) {
            \includegraphics[width=2.5cm]{""" + os.path.abspath("assets/logo.png") + r"""}
        };
    \end{tikzpicture}
}
\begin{document}

\frame{\titlepage}
"""
    
    # Slides
    for slide in json_data.get('slides', []):
        layout = 'standard'
        
        # Use the factory to get the right renderer
        renderer = latex_templates.get_renderer(layout)
        latex_content += renderer(slide)
        
    latex_content += r"\end{document}"
    
    return {"latex_content": latex_content}

def compile_pdf(state: AgentState):
    """Compiles LaTeX content to PDF."""
    print("Compiling LaTeX to PDF...")
    latex_content = state['latex_content']
    output_tex = "output.tex"
    
    with open(output_tex, "w") as f:
        f.write(latex_content)
        
    try:
        env = os.environ.copy()
        env["PATH"] = f"/Library/TeX/texbin:/usr/local/bin:{env['PATH']}"
        subprocess.run(["pdflatex", "-interaction=nonstopmode", "-file-line-error", output_tex], check=True, capture_output=True, env=env)
        return {"pdf_path": "output.pdf"}
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
