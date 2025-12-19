"""
MediaWiki export service for Spoken Tutorial scripts.
Converts JSON script data to MediaWiki table format for upload to script.spoken-tutorial.org
"""
import re
from pathlib import Path


def convert_markdown_bold_to_mediawiki(text: str) -> str:
    """Convert **text** to '''text''' for MediaWiki."""
    if not text:
        return text
    return re.sub(r'\*\*([^*]+)\*\*', r"'''\1'''", str(text))


def convert_newlines_to_mediawiki(text: str) -> str:
    """Convert \\n to line breaks for MediaWiki."""
    if not text:
        return text
    # MediaWiki handles newlines directly, but we need to preserve them
    return text.replace('\\n', '\n')


def escape_mediawiki(text: str) -> str:
    """Escape special MediaWiki characters if needed."""
    if not text:
        return text
    # Pipe characters inside cells need special handling
    # For now, we'll leave them as-is since they're typically inside cell content
    return text


def format_visual_cue(image_prompt: str, title: str = "") -> str:
    """Format the visual cue column content."""
    if not image_prompt:
        return "'''" + title + "'''" if title else ""
    
    # Convert bold markers
    visual_cue = convert_markdown_bold_to_mediawiki(image_prompt)
    
    # Standard slides are formatted with 'Show Slide'
    standard_slides = [
        "Title Slide",
        "Learning Objectives Slide",
        "System Requirements Slide",
        "Pre-requisite Slide",
        "Prerequisites Slide",
        "Assignment Slide",
        "Summary Slide",
        "Acknowledgement Slide",
        "Thank You Slide",
        "Closing Slide"
    ]
    
    # Check if it's a standard slide
    for slide_name in standard_slides:
        if slide_name.lower() in image_prompt.lower():
            # For Pre-requisite slide, include the URL if present
            if "pre-requisite" in slide_name.lower() and "edupyramids" in image_prompt.lower():
                return f"'''Pre-requisite Slide'''<br><br>EduPyramids.org"
            return f"'''{slide_name}'''"
    
    # For content slides, use the image_prompt as descriptor
    return visual_cue


def format_narration(narration: str) -> str:
    """Format the narration column content."""
    if not narration:
        return ""
    
    # Convert bold markers from markdown to MediaWiki
    text = convert_markdown_bold_to_mediawiki(narration)
    
    # Convert newlines
    text = convert_newlines_to_mediawiki(text)
    
    # Convert bullet points (• or -) to MediaWiki format (*)
    lines = text.split('\n')
    formatted_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:  # Skip empty lines
            continue
        # Check for bullet markers
        if stripped.startswith('•') or stripped.startswith('- '):
            if stripped.startswith('•'):
                content = stripped[1:].strip()
            else:
                content = stripped[2:].strip()
            formatted_lines.append(f"* {content}")
        else:
            formatted_lines.append(stripped)
    
    # Use double <br> for more spacing between lines (like original Spoken Tutorial format)
    return '<br><br>\n'.join(formatted_lines)


def create_mediawiki_script(json_data: dict, output_filename: str = None) -> str:
    """
    Generate a MediaWiki-formatted script from JSON data.
    
    Args:
        json_data: The JSON script data with slides, metadata, etc.
        output_filename: Optional path to save the output. If None, only returns string.
    
    Returns:
        The MediaWiki-formatted script as a string.
    """
    # Start the MediaWiki table with column widths
    wiki_content = "{| border=1\n"
    wiki_content += "|-\n"
    wiki_content += "! width=\"35%\" | '''Visual Cue'''\n"
    wiki_content += "! width=\"65%\" | '''Narration'''\n\n"
    
    # Process each slide
    for slide in json_data.get('slides', []):
        title = slide.get('title', '')
        narration = slide.get('narration', '')
        image_prompt = slide.get('image_prompt', '')
        
        # Add row separator
        wiki_content += "|-\n"
        
        # Format Visual Cue column
        visual_cue = format_visual_cue(image_prompt, title)
        wiki_content += f"|| {visual_cue}\n"
        
        # Format Narration column
        formatted_narration = format_narration(narration)
        wiki_content += f"|| {formatted_narration}\n\n"
    
    # Close the table
    wiki_content += "|}"
    
    # Add metadata section above the table (optional, as comment or separate section)
    # This can be added as a header section before the table
    metadata_section = generate_metadata_section(json_data)
    
    full_content = metadata_section + "\n\n" + wiki_content
    
    # Save to file if path provided
    if output_filename:
        output_path = Path(output_filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        return str(output_path)
    
    return full_content


def generate_metadata_section(json_data: dict) -> str:
    """Generate the metadata section in MediaWiki format."""
    title = json_data.get('presentation_title', 'Spoken Tutorial Script')
    module = json_data.get('module', '')
    episode = json_data.get('episode', '')
    duration = json_data.get('duration', '')
    prerequisites = json_data.get('prerequisites', '')
    learning_objectives = json_data.get('learning_objectives', [])
    meta_tags = json_data.get('meta_tags', [])
    outline = json_data.get('outline', [])
    
    # Build metadata as a MediaWiki table
    metadata = "== Script Metadata ==\n\n"
    metadata += "{| class=\"wikitable\"\n"
    
    # Title
    metadata += f"|-\n! Title\n| '''{title}'''\n"
    
    # Module
    if module:
        metadata += f"|-\n! Module\n| {module}\n"
    
    # Tutorial (Episode)
    if episode:
        metadata += f"|-\n! Tutorial\n| {episode}\n"
    
    # Duration
    if duration:
        metadata += f"|-\n! Duration\n| {duration}\n"
    
    # Prerequisites
    if prerequisites:
        metadata += f"|-\n! Prerequisites\n| {convert_markdown_bold_to_mediawiki(prerequisites)}\n"
    
    # Learning Objectives
    if learning_objectives:
        obj_list = "\n".join([f"* {convert_markdown_bold_to_mediawiki(obj)}" for obj in learning_objectives])
        metadata += f"|-\n! Learning Objectives\n| {obj_list}\n"
    
    # Outline
    if outline:
        outline_list = "\n".join([f"* {convert_markdown_bold_to_mediawiki(item)}" for item in outline])
        metadata += f"|-\n! Outline\n| {outline_list}\n"
    
    # Meta Tags
    if meta_tags:
        tags_str = ", ".join(meta_tags)
        metadata += f"|-\n! Meta Tags\n| {tags_str}\n"
    
    metadata += "|}\n"
    
    # Add the script header
    metadata += "\n== Script ==\n"
    
    return metadata


def export_to_mediawiki(json_data: dict, output_dir: str = None) -> dict:
    """
    Export JSON script to MediaWiki format.
    
    Args:
        json_data: The JSON script data
        output_dir: Directory to save the output file. If None, uses static/ directory.
    
    Returns:
        Dictionary with 'content' (string) and 'file_path' (if saved to file)
    """
    from pathlib import Path
    import time
    
    # Generate filename
    project_root = Path(__file__).parent.parent.parent
    if output_dir is None:
        output_dir = project_root / "static"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    timestamp = int(time.time())
    title_slug = json_data.get('presentation_title', 'script').replace(' ', '_')[:30]
    filename = output_dir / f"{title_slug}_{timestamp}.wiki"
    
    # Generate content and save
    content = create_mediawiki_script(json_data, str(filename))
    
    # Also return the raw content (if filename was provided, content is the path)
    wiki_content = create_mediawiki_script(json_data)  # Get content without saving
    
    return {
        "content": wiki_content,
        "file_path": str(filename)
    }
