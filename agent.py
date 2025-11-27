from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Optional, List
import os
import subprocess
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from json_to_latex import generate_latex_from_dict
import fitz  # pymupdf
import edge_tts
import asyncio
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
import requests
import urllib.parse
from script_pdf_generator import create_script_pdf
import json # Added for parsing LLM output

load_dotenv()

class Slide(TypedDict):
    type: str
    title: str
    content: List[str]
    narration: List[str]  # List of strings, one per bullet point
    image_prompt: str
    image_path: Optional[str]

class AgentState(TypedDict):
    topic: str
    outline: Optional[str] # Added outline
    mode: str
    json_script: dict
    script_pdf_path: Optional[str]
    slides_pdf_path: Optional[str]
    pdf_path: Optional[str]
    image_paths: List[str]
    latex_content: Optional[str]
    audio_map: dict  # {slide_index: [audio_paths]}
    video_path: Optional[str]


from langchain_core.pydantic_v1 import BaseModel, Field
from typing import List, Union, Literal

class SlideModel(BaseModel):
    type: str = Field(description="Type of slide: 'title_slide' or 'content_slide'")
    title: str = Field(description="Title of the slide")
    content: List[str] = Field(description="List of bullet points for the slide")
    narration: List[str] = Field(description="List of narration segments, one for each bullet point")
    image_prompt: str = Field(description="Prompt for generating an image for the slide")

class Presentation(BaseModel):
    presentation_title: str = Field(description="Title of the entire presentation")
    slides: List[SlideModel] = Field(description="List of slides")

def generate_script(state: AgentState):
    """Generates a presentation script using Gemini 2.5 Flash."""
    print("Generating script...")
    topic = state.get('topic') or state.get('outline')
    
    # Read business requirements
    try:
        with open("business_requirements.md", "r") as f:
            business_requirements = f.read()
    except FileNotFoundError:
        business_requirements = "No specific business requirements."

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=os.getenv("GOOGLE_API_KEY"))
    structured_llm = llm.with_structured_output(Presentation)
    
    prompt = f"""
    You are an expert presentation script writer. Create a presentation script for the topic: "{topic}".
    
    STRICT REQUIREMENTS:
    1. Create an appropriate number of slides (typically 4-7) based on the topic.
    2. For "content", provide a list of bullet points (strings).
       - MAX 5 bullet points per slide. This is a HARD LIMIT.
       - Keep bullet points VERY CONCISE (max 10 words).
    3. For "narration", provide a LIST of strings.
       - CRITICAL: The number of narration items MUST BE EXACTLY (number of content items) + 1.
       - Narration[0] MUST introduce the slide title/topic (before any bullets appear).
       - Narration[1] corresponds to Content[0], Narration[2] to Content[1], etc.
       - Each narration segment should explain that specific part.
    4. For "image_prompt", provide a detailed description for an AI image generator.
    5. For "content", provide a list of bullet points (strings).
       - NO fixed number of bullets. Use what is needed (typically 3-6).
       - Keep bullet points CONCISE (max 10-15 words).  
    Business Requirements:
    {business_requirements}
    
    Return JSON format:
    {{
        "presentation_title": "Title",
        "slides": [
            {{
                "type": "title_slide",
                "title": "Presentation Title",
                "content": [],
                "narration": ["Welcome to this presentation on..."], 
                "image_prompt": "..."
            }},
            {{
                "type": "content_slide",
                "title": "Slide Title",
                "content": ["Point 1", "Point 2"],
                "narration": ["Let's start by discussing the slide title...", "First, regarding point 1...", "Next, point 2..."],
                "image_prompt": "..."
            }}
        ]
    }}
    """
    
    try:
        presentation = structured_llm.invoke(prompt)
        json_script = presentation.dict()
        
        # Debug: Show what we got from LLM
        print(f"DEBUG: Generated {len(json_script.get('slides', []))} slides")
        
        # Post-processing: Validate and fix empty content fields
        for slide in json_script.get('slides', []):
            print(f"DEBUG: Slide '{slide.get('title')}' has content: {slide.get('content')}")
            
            # Check if content is truly empty or contains only empty dicts
            content = slide.get('content', [])
            valid_content = [item for item in content if item and isinstance(item, str) and item.strip()]
            
            if not valid_content and slide.get('type') == 'content_slide':
                print(f"WARNING: Slide '{slide.get('title')}' has empty or invalid content. Adding default bullet points.")
                # Extract key points from narration as fallback
                narration = slide.get('narration', [])
                
                # Handle legacy/string narration
                if isinstance(narration, str):
                    sentences = [s.strip() + '.' for s in narration.split('.') if s.strip() and len(s.strip()) > 20]
                    slide['content'] = sentences[:min(5, len(sentences))]
                    # Convert narration to list to match new format (Title + Content)
                    slide['narration'] = ["Introduction to this slide."] + sentences[:min(5, len(sentences))]
                elif isinstance(narration, list) and narration:
                    # Use narration items as content if content is missing
                    # Assume Narration[0] is title, rest are content
                    if len(narration) > 1:
                        slide['content'] = narration[1:]
                    else:
                        slide['content'] = narration # Fallback
                else:
                    # Total fallback
                    slide['content'] = [
                        "Key concept from this section",
                        "Important detail to remember",  
                        "Summary point"
                    ]
                    slide['narration'] = ["Here is an overview of this section."] + slide['content']
                
                print(f"DEBUG: Fixed content for '{slide.get('title')}': {slide.get('content')}")
            
            # Ensure narration is list and matches content length + 1
            # This is critical for the 1-to-1 video generation logic
            
            # CRITICAL FIX: Filter out empty strings from content HERE
            raw_content = slide.get('content', [])
            clean_content = [c for c in raw_content if isinstance(c, str) and c.strip()]
            slide['content'] = clean_content
            
            current_content = slide.get('content', [])
            current_narration = slide.get('narration', [])
            
            if isinstance(current_narration, str):
                current_narration = ["Introduction."] + [current_narration] * len(current_content)
            
            # Sanitize narration: Replace empty strings with placeholder to prevent skipping
            current_narration = [n if isinstance(n, str) and n.strip() else "Next point." for n in current_narration]

            target_length = len(current_content) + 1
            if len(current_narration) < target_length:
                # Pad with generic narration
                diff = target_length - len(current_narration)
                current_narration.extend([f"Details for point {k+1}." for k in range(diff)])
            elif len(current_narration) > target_length:
                # Truncate (keep first N+1)
                current_narration = current_narration[:target_length]
            
            slide['narration'] = current_narration
            
            # REMOVED LEGACY LOGIC that truncated back to len(content)
            # This was causing the N vs N+1 mismatch.
            
        return {"json_script": json_script}
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Failed to generate structured output: {e}")
        return {"json_script": {}}

def generate_script_pdf(state: AgentState):
    """Generates a PDF for script review."""
    print("Generating script review PDF...")
    json_script = state['json_script']
    pdf_path = create_script_pdf(json_script)
    print(f"Script review PDF generated at {pdf_path}")
    return {"script_pdf_path": pdf_path}

def generate_images(state: AgentState):
    """Generates images for each slide using Pollinations.ai (free API)."""
    print("Generating images...")
    json_script = state.get('json_script')
    if not json_script or 'slides' not in json_script:
        print("No slides found in script.")
        return {"json_script": json_script}
        
    slides = json_script['slides']
    
    if not os.path.exists("generated_images"):
        os.makedirs("generated_images")
        
    for i, slide in enumerate(slides):
        prompt = slide.get('image_prompt')
        if prompt:
            try:
                image_path = f"generated_images/slide_{i}.png"
                if os.path.exists(image_path):
                    print(f"Image for slide {i+1} already exists. Skipping generation.")
                    slide['image_path'] = os.path.abspath(image_path)
                    continue

                print(f"Generating image for slide {i+1}...")
                
                # Pollinations.ai API (simple and fast)
                encoded_prompt = urllib.parse.quote(prompt)
                image_url = f"https://pollinations.ai/p/{encoded_prompt}?width=1024&height=1024&seed={i}&nologo=true"
                
                # Download image with retry
                max_retries = 2
                for attempt in range(max_retries):
                    response = requests.get(image_url)
                    
                    if response.status_code == 200:
                        img_data = response.content
                        image_path = f"generated_images/slide_{i}.png"
                        with open(image_path, 'wb') as handler:
                            handler.write(img_data)
                            
                        # Update slide data with local image path for LaTeX
                        slide['image_path'] = os.path.abspath(image_path)
                        break
                    else:
                        if attempt < max_retries - 1:
                            print(f"Retry {attempt + 1} for slide {i+1}...")
                            import time
                            time.sleep(2)
                        else:
                            print(f"Failed to generate image for slide {i+1}: Status {response.status_code}")
                
            except Exception as e:
                print(f"Failed to generate image for slide {i+1}: {e}")
                
    return {"json_script": json_script}

def convert_to_latex(state: AgentState):
    """Converts JSON script to LaTeX content."""
    print("Converting JSON to LaTeX...")
    json_data = state['json_script']
    if not json_data:
        raise ValueError("No JSON script available to convert.")
    latex_content = generate_latex_from_dict(json_data)
    return {"latex_content": latex_content}

def compile_pdf(state: AgentState):
    """Compiles LaTeX content to PDF."""
    print("Compiling LaTeX to PDF...")
    latex_content = state['latex_content']
    output_tex = "output.tex"
    
    with open(output_tex, "w") as f:
        f.write(latex_content)
        
    # Run pdflatex
    try:
        # Add likely paths for pdflatex on macOS
        env = os.environ.copy()
        env["PATH"] = f"/Library/TeX/texbin:/usr/local/bin:{env['PATH']}"
        
        subprocess.run(["pdflatex", "-interaction=nonstopmode", "-file-line-error", output_tex], check=True, capture_output=True, env=env)
        pdf_path = "output.pdf"
        print(f"PDF generated at {pdf_path}")
        
        # Cleanup intermediate files
        extensions_to_remove = [".aux", ".log", ".out", ".snm", ".toc", ".nav"]
        for ext in extensions_to_remove:
            try:
                os.remove(output_tex.replace(".tex", ext))
            except OSError:
                pass # File might not exist
                
        return {"pdf_path": pdf_path}
    except subprocess.CalledProcessError as e:
        print(f"Error compiling PDF.")
        print(f"STDOUT: {e.stdout.decode() if e.stdout else 'None'}")
        print(f"STDERR: {e.stderr.decode() if e.stderr else 'None'}")
        return {"pdf_path": None}
    except FileNotFoundError:
        print("pdflatex not found. Please install it.")
        return {"pdf_path": None}

async def generate_audio(state: AgentState):
    """Generates audio narration for each slide using Edge TTS."""
    print("Generating audio narration...")
    json_script = state['json_script']
    slides = json_script['slides']
    audio_map = {} # Map slide index to list of audio paths
    
    if not os.path.exists("audio"):
        os.makedirs("audio")
    
    tasks = []
    for i, slide in enumerate(slides):
        narrations = slide.get('narration', [])
        # Handle case where narration is a string (legacy/error fallback)
        if isinstance(narrations, str):
            narrations = [narrations]
        
        # Ensure we have at least one narration part
        if not narrations:
            narrations = [slide.get('title', 'Slide')]
        
        slide_audio_paths = []
        for j, narration_part in enumerate(narrations):
            # Clean markdown formatting
            narration_part = narration_part.replace('**', '')
            narration_part = narration_part.replace('__', '')
            narration_part = narration_part.replace('*', '')
            narration_part = narration_part.replace('_', '')
            narration_part = narration_part.replace('#', '')
            
            audio_path = f"audio/slide_{i}_part_{j}.mp3"
            slide_audio_paths.append(audio_path)
            
            # Use Edge TTS voice
            communicate = edge_tts.Communicate(narration_part, "en-US-AriaNeural")
            tasks.append(communicate.save(audio_path))
        
        audio_map[i] = slide_audio_paths
    
    # Generate all audio files concurrently
    if tasks:
        await asyncio.gather(*tasks)
    
    return {"audio_map": audio_map}

def create_video(state: AgentState):
    """Creates video from PDF slides and audio."""
    print("Creating video...")
    pdf_path = state['pdf_path']
    audio_map = state['audio_map']
    
    if not pdf_path or not audio_map:
        print("Missing PDF path or audio map.")
        return {"video_path": None}
        
    # Open PDF to extract images
    doc = fitz.open(pdf_path)
    clips = []
    
    current_page_index = 0
    slides = state['json_script']['slides']
    
    for i, slide in enumerate(slides):
        if slide.get('type') == 'title_slide':
            # Title slide usually has 1 page and 1 narration
            # But check audio map to be safe
            audio_paths = audio_map.get(i, [])
            if not audio_paths:
                continue
                
            # For title slide, just use the first page and first audio
            # (Assuming title slide doesn't have bullet animations)
            page = doc.load_page(current_page_index)
            pix = page.get_pixmap(dpi=300)
            img_path = f"temp_slide_{i}_0.png"
            pix.save(img_path)
            
            audio_clip = AudioFileClip(audio_paths[0])
            video_clip = ImageClip(img_path).with_duration(audio_clip.duration)
            video_clip = video_clip.with_audio(audio_clip)
            clips.append(video_clip)
            
            current_page_index += 1 # Move to next PDF page
            
        else:
            # Content slide with potential animations
            audio_paths = audio_map.get(i, [])
            
            print(f"DEBUG: Slide {i} ('{slide.get('title')}') has {len(audio_paths)} audio parts.")
            print(f"DEBUG: Current PDF page index: {current_page_index}")
            
            # We expect one PDF page per audio segment (bullet point)
            # But Beamer might generate differently.
            # Strategy: Iterate through audio parts and consume PDF pages.
            # If we run out of PDF pages for this slide, reuse the last one.
            
            # How many pages does this slide have in PDF?
            # It's hard to know exactly from here without parsing LaTeX log.
            # BUT, we know Beamer <+-> generates 1 page per item.
            # And we enforced len(narration) == len(content).
            # So ideally: num_audio_parts == num_pdf_pages_for_slide.
            
            for j, audio_path in enumerate(audio_paths):
                # Load the corresponding PDF page
                # Safety check: ensure we don't go out of bounds of PDF
                if current_page_index >= len(doc):
                    print(f"Warning: PDF has fewer pages than expected. Reusing last page.")
                    current_page_index = len(doc) - 1
                
                page = doc.load_page(current_page_index)
                pix = page.get_pixmap(dpi=300)
                img_path = f"temp_slide_{i}_{j}.png"
                pix.save(img_path)
                
                audio_clip = AudioFileClip(audio_path)
                video_clip = ImageClip(img_path).with_duration(audio_clip.duration)
                video_clip = video_clip.with_audio(audio_clip)
                clips.append(video_clip)
                
                # Advance PDF page
                # Logic: If this is the last audio part, we move to next slide's pages.
                # If Beamer generated fewer pages than audio parts (unlikely with our setup),
                # we might desync.
                # Assumption: 1-to-1 mapping holds.
                current_page_index += 1
                
    final_video = concatenate_videoclips(clips)
    video_path = "presentation.mp4"
    final_video.write_videofile(video_path, fps=24, codec='libx264', audio_codec='aac')
    
    return {"video_path": os.path.abspath(video_path)}

def route_step(state: AgentState):
    mode = state.get("mode", "script_only")
    print(f"DEBUG: route_step called with mode={mode}, outline={state.get('outline')}")
    
    if mode == "slides_only":
        return "generate_images"
    elif mode == "video_production":
        return "generate_audio"
        
    if state.get("topic") or state.get("outline"):
        return "generate_script"
    return "generate_script_pdf"

# Build the graph
builder = StateGraph(AgentState)

builder.add_node("generate_script", generate_script)
builder.add_node("generate_script_pdf", generate_script_pdf)
builder.add_node("generate_images", generate_images)
builder.add_node("convert_to_latex", convert_to_latex)
builder.add_node("compile_pdf", compile_pdf)
builder.add_node("generate_audio", generate_audio)
builder.add_node("create_video", create_video)

builder.add_conditional_edges(START, route_step)

# Phase 1: Script generation
builder.add_edge("generate_script", "generate_script_pdf")
builder.add_edge("generate_script_pdf", END)

# Phase 2: Slides generation (slides_only mode)
builder.add_edge("generate_images", "convert_to_latex")
builder.add_edge("convert_to_latex", "compile_pdf")
builder.add_edge("compile_pdf", END)  # Stop after PDF for slides_only mode

# Phase 3: Video generation (video_production mode)
builder.add_edge("generate_audio", "create_video")
builder.add_edge("create_video", END)

graph = builder.compile()

if __name__ == "__main__":
    # Example usage
    # Phase 1: Generate Script PDF
    print("--- Phase 1: Generating Script ---")
    initial_state = {"outline": "The Life Cycle of a Star", "mode": "script_only"}
    result = graph.invoke(initial_state)
    
    if result.get("script_pdf_path"):
        print(f"Please review the script at: {result['script_pdf_path']}")
        
        # Simulate user approval (in a real app, this would be a separate call)
        user_approval = input("Do you approve the script? (yes/no): ")
        
        if user_approval.lower() == "yes":
            # Phase 2: Video Production
            print("\n--- Phase 2: Producing Video ---")
            # Pass the generated script from Phase 1 to Phase 2
            print(f"DEBUG: json_script keys: {result.get('json_script', {}).keys()}")
            phase2_state = {
                "json_script": result['json_script'], 
                "mode": "video_production"
            }
            final_result = graph.invoke(phase2_state)
            
            if final_result.get("video_path"):
                print(f"Final Video available at: {final_result['video_path']}")
        else:
            print("Workflow stopped by user.")
