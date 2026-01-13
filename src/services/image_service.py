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
    aspect_ratio: str = "1:1",
    reference_image_paths: Optional[List[Path]] = None
) -> bool:
    """
    Generate a single image from a prompt, optionally using reference images.
    
    Args:
        prompt: The image generation prompt
        output_path: Path to save the generated image
        aspect_ratio: Image aspect ratio (1:1, 16:9, 4:3)
        reference_image_paths: Optional list of paths to reference images for image-to-image generation
    
    Returns:
        True if successful, False otherwise
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")
    
    client = genai.Client(api_key=api_key)
    
    try:
        # Import shared style prefix for consistent image generation
        from src.services.image_styles import IMAGE_STYLE_PREFIX, CHARACTER_PROMPT
        
        
        # Build contents: reference images (if provided) + style-prefixed prompt
        styled_prompt = IMAGE_STYLE_PREFIX + prompt + CHARACTER_PROMPT
        
        if reference_image_paths:
            # Load all valid reference images
            from PIL import Image
            ref_images = []
            for path in reference_image_paths:
                if path and path.exists():
                    ref_images.append(Image.open(path))
            
            if ref_images:
                print(f"  🎨 Editing with {len(ref_images)} reference image(s): {prompt[:50]}...")
                contents = [*ref_images, styled_prompt]  # Multiple images + prompt
            else:
                print(f"  🎨 Generating image: {prompt[:50]}...")
                contents = styled_prompt
        else:
            print(f"  🎨 Generating image: {prompt[:50]}...")
            contents = styled_prompt
        
        response = client.models.generate_content(
            model='gemini-3-pro-image-preview',
            contents=contents,
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
        prompts: List of dicts with 'slide_number', 'prompt', and optionally 'sentence_index' keys
        project_id: Project ID for file naming
        aspect_ratio: Image aspect ratio
    
    Returns:
        Dictionary with:
        - images: List of {slide_number, sentence_index, url, success}
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
        sentence_index = item.get('sentence_index', None)  # None for backwards compatibility
        prompt = item.get('prompt', '')
        reference_images = item.get('reference_image_paths', [])  # List of reference image paths
        
        if not prompt:
            results.append({
                "slide_number": slide_number,
                "sentence_index": sentence_index,
                "url": None,
                "success": False,
                "error": "No prompt provided"
            })
            failed_count += 1
            continue
        
        # Generate filename based on whether sentence_index is provided
        if sentence_index is not None:
            filename = f"row_{slide_number}_sent_{sentence_index}.png"
        else:
            filename = f"slide_{slide_number}.png"
        
        output_path = output_dir / filename
        
        # Convert reference_image strings to Path list
        ref_paths = [Path(p) for p in reference_images if p] if reference_images else None
        
        try:
            success = generate_single_image(prompt, output_path, aspect_ratio, ref_paths)
            
            if success:
                # Build URL relative to output directory
                url = f"/output/images/{project_id}/{filename}"
                results.append({
                    "slide_number": slide_number,
                    "sentence_index": sentence_index,
                    "url": url,
                    "success": True
                })
                generated_count += 1
            else:
                results.append({
                    "slide_number": slide_number,
                    "sentence_index": sentence_index,
                    "url": None,
                    "success": False,
                    "error": "No image returned from API"
                })
                failed_count += 1
                
        except Exception as e:
            results.append({
                "slide_number": slide_number,
                "sentence_index": sentence_index,
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
                # Add all PNG files in the directory (supports both naming conventions)
                for png_file in output_dir.glob("*.png"):
                    zipf.write(str(png_file), png_file.name)
            zip_url = f"/output/images/{project_id}/project_{project_id}_images.zip"
            print(f"\n📦 Created ZIP: {zip_path.name} with {len(list(output_dir.glob('*.png')))} images")
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
