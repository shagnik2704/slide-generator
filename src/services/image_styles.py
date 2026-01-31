"""
Shared image style guide for consistent image generation.

This module contains style constants used by:
- prompt_enhancer.py (for expanding visual cues into scene descriptions)
- image_service.py (applies styling at generation time)

SEPARATION OF CONCERNS:
- IMAGE_STYLE_PREFIX: ALL stylistic rules (applied at image generation)
- ENHANCEMENT_SYSTEM_PROMPT: Scene-setting ONLY (no style instructions)
"""

# =============================================================================
# STYLE PREFIX - Applied at IMAGE GENERATION time
# Handles: artistic style, colors, aesthetics, no-text rule, etc.
# =============================================================================
IMAGE_STYLE_PREFIX = """
Generate an educational illustration using the following strict style rules.

STYLE & RENDERING:
- Flat 2D vector illustration (NOT photorealistic)
- Modern educational / infographic aesthetic
- Consistent visual style across all images

HUMAN CHARACTERS (if present):
- Simple cartoon-style illustrated people
- Indian appearance when depicting humans

SOFTWARE / UI ELEMENTS (if present):
- Simplified but realistic interface layouts
- Clearly recognizable UI components (buttons, panels, icons)
- No readable text or symbols
- Avoid brand-specific designs unless explicitly required

COMPOSITION & QUALITY:
- Single clear focal point
- Clean, uncluttered background
- High visual clarity at presentation resolution
- Balanced spacing suitable for slide-based videos

STRICT CONSTRAINTS:
- NO TEXT, LETTERS, NUMBERS, OR SYMBOLS of any kind
- NO watermarks, logos, or branding
- NO photorealism or 3D rendering
- NO visual noise or clutter

Create the image based on the following description:

"""

# =============================================================================
# ENHANCEMENT PROMPT - Used to expand visual cues into scene descriptions
# Handles: What's in the scene, composition, objects, layout
# Does NOT include style instructions (style is applied later)
# =============================================================================
ENHANCEMENT_SYSTEM_PROMPT = """
You are an expert visual prompt engineer for educational videos.

Your task is to convert narration text and a visual cue into a single,
high-quality image generation prompt suitable for AI image models


The output prompt must:
- Be visually concrete (describe what is visible)
- Match the narration’s meaning
- Respect the visual cue strictly
- Avoid abstract concepts unless visualized
- Be suitable for educational content
- Avoid text-heavy visuals unless explicitly requested
- Use neutral, inclusive visuals
- Use a consistent illustration style

=== CRITICAL: NO TEXT ===
- NEVER mention text, labels, titles, or words to appear in the image
- WRONG: "Text saying 'Welcome'" or "Title: Introduction"  

Return a JSON array with enhanced prompts for each slide."""



CHARACTER_PROMPT = "Use the exact same characters with the same facial details."