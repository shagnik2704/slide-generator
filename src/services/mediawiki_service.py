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


# Boilerplate slide labels, longest/most specific first so substring matching
# picks "Pre-requisite Slide" over the bare "Pre-requisites".
STANDARD_SLIDE_LABELS = [
    "Learning Objectives Slide",
    "System Requirements Slide",
    "Acknowledgement Slide",
    "Pre-requisite Slide",
    "Prerequisites Slide",
    "Disclaimer Slide",
    "Assignment Slide",
    "Code file Slide",
    "Thank You Slide",
    "Closing Slide",
    "Summary Slide",
    "Title Slide",
    "Pre-requisites",
    "Prerequisites",
]

# "Slide 5", "Slide [N-3]" — the leading line of a current-format visual cue.
_SLIDE_NUMBER_RE = re.compile(r"^Slide\s+[\w\[\]\-]+$", re.IGNORECASE)

EDUPYRAMIDS_URL = "https://EduPyramids.org"


def _is_prerequisite_label(line: str) -> bool:
    """Whether a slide-label line is the boilerplate Pre-requisites slide."""
    return "requisit" in line.lower()


def format_visual_cue(image_prompt: str, title: str = "") -> str:
    """Format the visual cue column for a legacy slide (title + image_prompt).

    Legacy slides keep the on-screen text in `image_prompt` (with `title` as a
    fallback). This used to collapse any boilerplate slide to its bare bold
    label, dropping the names on the Acknowledgement slide and the sentences on
    the Disclaimer / Thank-You slides. It now preserves every line, exactly like
    the current-format path (which also bolds slide labels and keeps the
    prerequisite EduPyramids link).
    """
    return format_visual_cue_text(image_prompt or title)


def _is_slide_label(line: str) -> bool:
    """Whether a visual cue line is a boilerplate slide heading worth bolding."""
    if line.startswith("'''"):
        return False
    if _SLIDE_NUMBER_RE.match(line):
        return True
    return line.lower() in {label.lower() for label in STANDARD_SLIDE_LABELS}


def format_visual_cue_text(visual_cue: str) -> str:
    """Format a current-format visual cue.

    Unlike the legacy `image_prompt` (a bare label such as "Summary Slide"), a
    script-chat `visual_cue` carries real multi-line content — the slide
    heading, on-screen bullets and links like the EduPyramids URL. Collapsing it
    to a label would drop that, so every line is preserved here.
    """
    if not visual_cue:
        return ""

    text = convert_newlines_to_mediawiki(convert_markdown_bold_to_mediawiki(visual_cue))

    formatted_lines = []
    is_prerequisite = False
    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('•'):
            formatted_lines.append(f"* {stripped[1:].strip()}")
        elif stripped.startswith('- '):
            formatted_lines.append(f"* {stripped[2:].strip()}")
        else:
            # A slide label sometimes arrives already wrapped in bold from the
            # source (markdown ** **), even as one bold span running across two
            # lines ("Slide 5" + "Pre-requisite slide"). Detect on the unbolded
            # text so the label — and the prerequisite link — is still found, and
            # re-emit a single clean bold label.
            plain = stripped.replace("'''", "").strip()
            if _is_slide_label(plain):
                if _is_prerequisite_label(plain):
                    is_prerequisite = True
                formatted_lines.append(f"'''{plain}'''")
            else:
                formatted_lines.append(stripped)

    # Space the blocks so the visual-cue column reads like the narration one:
    # a blank line between paragraphs/headings, but consecutive bullets stay a
    # tight list so MediaWiki renders them cleanly.
    parts = []
    for index, line in enumerate(formatted_lines):
        if index:
            both_bullets = line.startswith('* ') and formatted_lines[index - 1].startswith('* ')
            parts.append('\n' if both_bullets else '<br><br>\n')
        parts.append(line)
    result = ''.join(parts)

    # The prerequisite slide always points to EduPyramids, even when the source
    # cue only carried the bare label.
    if is_prerequisite and "edupyramids" not in result.lower():
        result += f"<br><br>\n{EDUPYRAMIDS_URL}"

    return result


def resolve_slides(json_data: dict) -> list:
    """Return the slide list, accepting both `slides` (legacy) and `script`."""
    return json_data.get('slides') or json_data.get('script') or []


def resolve_slide_visual_cue(slide: dict) -> str:
    """Format a slide's visual cue, whichever script format it came from."""
    if slide.get('visual_cue') is not None:
        return format_visual_cue_text(str(slide['visual_cue']))
    return format_visual_cue(
        slide.get('image_prompt', ''),
        slide.get('title', '') or slide.get('slide_type', ''),
    )


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
    for slide in resolve_slides(json_data):
        # Add row separator
        wiki_content += "|-\n"

        # Format Visual Cue column
        visual_cue = resolve_slide_visual_cue(slide)
        wiki_content += f"|| {visual_cue}\n"

        # Format Narration column
        formatted_narration = format_narration(slide.get('narration', ''))
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


def resolve_metadata(json_data: dict) -> dict:
    """Read script metadata from either format.

    Legacy payloads keep these keys flat at the top level; script-chat nests
    them under `metadata` with a few different names (`title`,
    `outline_topics`).
    """
    nested = json_data.get('metadata') or {}

    def pick(flat_key: str, nested_key: str = None):
        return json_data.get(flat_key) or nested.get(nested_key or flat_key)

    return {
        'title': pick('presentation_title', 'title') or 'Spoken Tutorial Script',
        'module': pick('module') or pick('series') or '',
        'episode': pick('episode') or pick('tutorial') or '',
        'duration': pick('duration') or '',
        'prerequisites': pick('prerequisites') or '',
        'system_requirements': pick('system_requirements') or '',
        'learning_objectives': pick('learning_objectives') or [],
        'outline': pick('outline', 'outline_topics') or [],
        'meta_tags': pick('meta_tags') or [],
    }


def generate_metadata_section(json_data: dict) -> str:
    """Generate the metadata section in MediaWiki format."""
    metadata_values = resolve_metadata(json_data)
    title = metadata_values['title']
    module = metadata_values['module']
    episode = metadata_values['episode']
    duration = metadata_values['duration']
    prerequisites = metadata_values['prerequisites']
    system_requirements = metadata_values['system_requirements']
    learning_objectives = metadata_values['learning_objectives']
    meta_tags = metadata_values['meta_tags']
    outline = metadata_values['outline']

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

    # System Requirements
    if system_requirements:
        metadata += f"|-\n! System Requirements\n| {convert_markdown_bold_to_mediawiki(system_requirements)}\n"

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
    title_slug = resolve_metadata(json_data)['title'].replace(' ', '_')[:30]
    filename = output_dir / f"{title_slug}_{timestamp}.wiki"
    
    # Render once, then persist that same content
    wiki_content = create_mediawiki_script(json_data)
    filename.write_text(wiki_content, encoding='utf-8')

    return {
        "content": wiki_content,
        "file_path": str(filename)
    }
