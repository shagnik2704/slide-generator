"""
Image generation service for Spoken Tutorial scripts.
Uses Gemini 3 Pro Image Preview for generating images from prompts.

This is a clean, decoupled service with no layout/position logic.
"""
import os
import zipfile
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable

load_dotenv()


def get_output_dir(project_id: int) -> Path:
    """Get or create the output directory for a project's images."""
    project_root = Path(__file__).parent.parent.parent
    images_dir = project_root / "output" / "images" / str(project_id)
    images_dir.mkdir(parents=True, exist_ok=True)
    return images_dir


@retry(
    retry=retry_if_exception_type((ResourceExhausted, ServiceUnavailable)),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    stop=stop_after_attempt(3)
)
def generate_single_image(
    prompt: str,
    output_path: Path,
    aspect_ratio: str = "1:1"
) -> bool:
    """
    Generate a single image from a prompt.
    
    Args:
        prompt: The image generation prompt
        output_path: Path to save the generated image
        aspect_ratio: Image aspect ratio (1:1, 16:9, 4:3)
    
    Returns:
        True if successful, False otherwise
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")
    
    client = genai.Client(api_key=api_key)
    
    try:
        print(f"  🎨 Generating image: {prompt[:50]}...")
        
        response = client.models.generate_content(
            model='gemini-3-pro-image-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
            ),
        )
        
        if response.parts:
            for part in response.parts:
                if part.inline_data:
                    generated_image = part.as_image()
                    generated_image.save(str(output_path))
                    print(f"  ✓ Saved: {output_path.name}")
                    return True
        
        print(f"  ⚠️ No image returned for prompt")
        return False
        
    except Exception as e:
        print(f"  ❌ Error generating image: {e}")
        raise


def generate_images(
    prompts: List[Dict],
    project_id: int,
    aspect_ratio: str = "1:1"
) -> dict:
    """
    Generate images for multiple prompts.
    
    Args:
        prompts: List of dicts with 'slide_number' and 'prompt' keys
        project_id: Project ID for file naming
        aspect_ratio: Image aspect ratio
    
    Returns:
        Dictionary with:
        - images: List of {slide_number, url, success}
        - zip_url: URL to download all images as ZIP
        - generated: Count of successfully generated images
        - failed: Count of failed generations
    """
    print(f"\n🖼️ Starting image generation for project {project_id}")
    print(f"   Generating {len(prompts)} images...\n")
    
    output_dir = get_output_dir(project_id)
    results = []
    generated_count = 0
    failed_count = 0
    
    for item in prompts:
        slide_number = item.get('slide_number')
        prompt = item.get('prompt', '')
        
        if not prompt:
            results.append({
                "slide_number": slide_number,
                "url": None,
                "success": False,
                "error": "No prompt provided"
            })
            failed_count += 1
            continue
        
        output_path = output_dir / f"slide_{slide_number}.png"
        
        try:
            success = generate_single_image(prompt, output_path, aspect_ratio)
            
            if success:
                # Build URL relative to output directory
                url = f"/output/images/{project_id}/slide_{slide_number}.png"
                results.append({
                    "slide_number": slide_number,
                    "url": url,
                    "success": True
                })
                generated_count += 1
            else:
                results.append({
                    "slide_number": slide_number,
                    "url": None,
                    "success": False,
                    "error": "No image returned from API"
                })
                failed_count += 1
                
        except Exception as e:
            results.append({
                "slide_number": slide_number,
                "url": None,
                "success": False,
                "error": str(e)
            })
            failed_count += 1
    
    # Create ZIP if we have any successful images
    zip_url = None
    if generated_count > 0:
        zip_path = output_dir / f"project_{project_id}_images.zip"
        try:
            with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zipf:
                for result in results:
                    if result.get("success"):
                        img_path = output_dir / f"slide_{result['slide_number']}.png"
                        if img_path.exists():
                            zipf.write(str(img_path), img_path.name)
            zip_url = f"/output/images/{project_id}/project_{project_id}_images.zip"
            print(f"\n📦 Created ZIP: {zip_path.name}")
        except Exception as e:
            print(f"⚠️ Failed to create ZIP: {e}")
    
    print(f"\n✅ Image generation complete:")
    print(f"   Generated: {generated_count}")
    print(f"   Failed: {failed_count}")
    
    return {
        "images": results,
        "zip_url": zip_url,
        "generated": generated_count,
        "failed": failed_count,
        "project_id": project_id
    }
