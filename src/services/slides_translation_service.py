"""
Slides Translation Service - Translate .tex Beamer files to different languages.

This service:
1. Reads a .tex file
2. Uses LLM to translate human-readable text while preserving LaTeX structure
3. Adds XeLaTeX packages for Unicode font support
4. Returns the translated .tex file
"""

import re
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)


# ============================================
# LANGUAGE CONFIGURATION
# ============================================

LANGUAGE_CONFIG = {
    "hi": {
        "name": "Hindi",
        "native": "हिंदी",
        "font": "Noto Sans Devanagari",
        "polyglossia": "hindi"
    },
    "ta": {
        "name": "Tamil",
        "native": "தமிழ்",
        "font": "Noto Sans Tamil",
        "polyglossia": "tamil"
    },
    "te": {
        "name": "Telugu",
        "native": "తెలుగు",
        "font": "Noto Sans Telugu",
        "polyglossia": "telugu"
    },
    "mr": {
        "name": "Marathi",
        "native": "मराठी",
        "font": "Noto Sans Devanagari",
        "polyglossia": "marathi"
    },
    "bn": {
        "name": "Bengali",
        "native": "বাংলা",
        "font": "Noto Sans Bengali",
        "polyglossia": "bengali"
    },
    "gu": {
        "name": "Gujarati",
        "native": "ગુજરાતી",
        "font": "Noto Sans Gujarati",
        "polyglossia": "gujarati"
    },
    "kn": {
        "name": "Kannada",
        "native": "ಕನ್ನಡ",
        "font": "Noto Sans Kannada",
        "polyglossia": "kannada"
    },
    "ml": {
        "name": "Malayalam",
        "native": "മലയാളം",
        "font": "Noto Sans Malayalam",
        "polyglossia": "malayalam"
    },
    "pa": {
        "name": "Punjabi",
        "native": "ਪੰਜਾਬੀ",
        "font": "Noto Sans Gurmukhi",
        "polyglossia": "punjabi"
    },
    "or": {
        "name": "Odia",
        "native": "ଓଡ଼ିଆ",
        "font": "Noto Sans Oriya",
        "polyglossia": "odia"
    },
    "as": {
        "name": "Assamese",
        "native": "অসমীয়া",
        "font": "Noto Sans Bengali",
        "polyglossia": "assamese"
    },
}


@dataclass
class SlidesTranslationResult:
    """Result of translating a .tex file."""
    success: bool
    filename: str
    download_url: str
    language_code: str
    language_name: str
    language_native: str
    font_name: str
    error: Optional[str] = None


def get_supported_languages() -> dict:
    """Return the dictionary of supported languages for slides translation."""
    return {code: {"name": info["name"], "native": info["native"]} 
            for code, info in LANGUAGE_CONFIG.items()}


def translate_tex_content(tex_content: str, target_language: str) -> str:
    """
    Use LLM to translate the human-readable text in a .tex file.
    
    Args:
        tex_content: The original .tex file content
        target_language: Language code (e.g., 'hi', 'ta')
    
    Returns:
        Translated .tex content
    """
    config = LANGUAGE_CONFIG.get(target_language)
    if not config:
        raise ValueError(f"Unsupported language: {target_language}")
    
    language_name = config["name"]
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.2  # Low temperature for consistent translation
    )
    
    prompt = f"""You are a LaTeX document translator. Translate the human-readable text in this Beamer presentation to {language_name}.

## CRITICAL RULES - YOU MUST FOLLOW EXACTLY:

### What to TRANSLATE:
- Slide titles inside \\frametitle{{...}}
- Bullet point text after \\item
- Introductory sentences before \\begin{{itemize}}
- Footer/description text
- \\title{{...}} content (both short and long forms)
- Plain text paragraphs

### What to KEEP UNCHANGED (DO NOT TRANSLATE):
- ALL LaTeX commands (\\begin, \\end, \\item, \\frametitle, \\usepackage, etc.)
- ALL LaTeX special characters, braces {{}}, brackets [], and backslashes \\
- ALL LaTeX environments and their names
- Software names: Python, Linux, Ubuntu, Windows, VS Code, Firefox, LibreOffice, etc.
- Brand names: Spoken Tutorial, EduPyramids, FOSSEE, IIT Bombay
- Technical terms: terminal, command line, script, variable, function, GUI, CLI
- URLs and file paths (anything with http, www, or file extensions)
- Numbers and version numbers (e.g., "Python 3.x", "Ubuntu 22.04")
- Email addresses
- Code snippets inside verbatim or lstlisting environments

### TRANSLATION STYLE:
- Use **SIMPLE, everyday language** that common people can easily understand
- Avoid formal, literary, or highly Sanskritized words
- Prefer colloquial/spoken style over written/formal style
- Use short, clear sentences
- If there are simpler alternatives to complex words, use the simpler one
- The target audience is students and beginners learning technology
- Use {config["native"]} script for all translated text

### EXAMPLES:
BEFORE: \\frametitle{{Learning Objectives}}
AFTER:  \\frametitle{{सीखने के उद्देश्य}}

BEFORE: \\item Install Python on Ubuntu
AFTER:  \\item Ubuntu पर Python इंस्टॉल करें

BEFORE: In this tutorial, you will learn to:
AFTER:  इस ट्यूटोरियल में, आप सीखेंगे:

BEFORE: For prerequisites, visit: https://spoken-tutorial.org
AFTER:  इसकी पूर्व-आवश्यकताओं के लिए, देखें: https://spoken-tutorial.org

### OUTPUT FORMAT:
Return ONLY the complete translated .tex file content.
- No explanations before or after
- No markdown code blocks (no ```)
- The output must start with \\documentclass and end with \\end{{document}}

### INPUT .tex FILE:
{tex_content}
"""

    logger.info(f"🌐 Translating .tex file to {language_name}...")
    
    response = llm.invoke(prompt)
    translated_content = response.content.strip()
    
    # Clean up any markdown code blocks if the LLM added them
    if translated_content.startswith("```"):
        # Remove opening code block
        translated_content = re.sub(r'^```\w*\n', '', translated_content)
        # Remove closing code block
        translated_content = re.sub(r'\n```$', '', translated_content)
    
    logger.info(f"✅ Translation to {language_name} complete")
    return translated_content


def add_xelatex_packages(tex_content: str, target_language: str) -> str:
    """
    Add XeLaTeX packages for Unicode font support.
    
    Args:
        tex_content: The translated .tex content
        target_language: Language code
    
    Returns:
        .tex content with XeLaTeX packages added
    """
    config = LANGUAGE_CONFIG.get(target_language)
    if not config:
        return tex_content  # Return unchanged if language not found
    
    # Check if packages are already present
    if "\\usepackage{fontspec}" in tex_content:
        logger.info("XeLaTeX packages already present, skipping injection")
        return tex_content
    
    xelatex_preamble = f'''% ================================================
% XeLaTeX Support for {config["name"]}
% COMPILE WITH: xelatex filename.tex
% ================================================
\\usepackage{{fontspec}}
\\usepackage{{xunicode}}
\\setmainfont{{FreeSerif}}
\\setsansfont{{FreeSans}}

'''
    
    # Find the end of \documentclass line and insert after it
    # Use string manipulation instead of re.sub to avoid escape issues
    match = re.search(r'\\documentclass(?:\[[^\]]*\])?\{[^}]*\}\s*\n', tex_content)
    
    if match:
        insert_pos = match.end()
        tex_content = tex_content[:insert_pos] + xelatex_preamble + tex_content[insert_pos:]
        logger.info(f"✅ Added XeLaTeX packages for {config['name']}")
    else:
        # Fallback: prepend after first line
        lines = tex_content.split('\n')
        lines.insert(1, xelatex_preamble)
        tex_content = '\n'.join(lines)
        logger.warning("⚠️ Could not find \\documentclass, inserted XeLaTeX packages after first line")
    
    return tex_content


def validate_translated_tex(original: str, translated: str) -> tuple[bool, str]:
    """
    Validate the translated .tex preserves basic structure.
    
    Args:
        original: Original .tex content
        translated: Translated .tex content
    
    Returns:
        (is_valid, error_message)
    """
    # Check document markers
    if "\\begin{document}" not in translated:
        return False, "Missing \\begin{document} in translated content"
    
    if "\\end{document}" not in translated:
        return False, "Missing \\end{document} in translated content"
    
    # Count frames
    orig_frames = len(re.findall(r'\\begin\{frame\}', original))
    trans_frames = len(re.findall(r'\\begin\{frame\}', translated))
    
    if orig_frames != trans_frames:
        return False, f"Frame count mismatch: original has {orig_frames}, translated has {trans_frames}"
    
    # Check for common corruption patterns
    if "\\begin{itemize}" in original and "\\begin{itemize}" not in translated:
        return False, "Missing \\begin{itemize} - LaTeX structure may be corrupted"
    
    return True, ""


async def translate_slides(
    tex_content: str,
    target_language: str,
    original_filename: str,
    output_dir: Path
) -> SlidesTranslationResult:
    """
    Main function to translate a .tex file.
    
    Args:
        tex_content: The original .tex file content
        target_language: Language code (e.g., 'hi', 'ta')
        original_filename: Original filename for generating output name
        output_dir: Directory to save the translated file
    
    Returns:
        SlidesTranslationResult with file info or error
    """
    config = LANGUAGE_CONFIG.get(target_language)
    if not config:
        return SlidesTranslationResult(
            success=False,
            filename="",
            download_url="",
            language_code=target_language,
            language_name="Unknown",
            language_native="",
            font_name="",
            error=f"Unsupported language: {target_language}"
        )
    
    try:
        # Step 1: Translate content with LLM
        logger.info(f"📝 Step 1: Translating content to {config['name']}...")
        translated_content = translate_tex_content(tex_content, target_language)
        
        # Step 2: Add XeLaTeX packages
        logger.info(f"📦 Step 2: Adding XeLaTeX packages...")
        translated_content = add_xelatex_packages(translated_content, target_language)
        
        # Step 3: Validate
        logger.info(f"✅ Step 3: Validating translated content...")
        is_valid, error_msg = validate_translated_tex(tex_content, translated_content)
        
        if not is_valid:
            logger.warning(f"⚠️ Validation warning: {error_msg}")
            # Continue anyway - the LLM output might still be usable
        
        # Step 4: Save to file
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename
        base_name = Path(original_filename).stem
        output_filename = f"{base_name}_{target_language}.tex"
        output_path = output_dir / output_filename
        
        # Write with UTF-8 encoding
        output_path.write_text(translated_content, encoding='utf-8')
        logger.info(f"💾 Saved translated file: {output_path}")
        
        # Generate download URL (relative to output directory)
        download_url = f"/output/slides/translated/{output_filename}"
        
        return SlidesTranslationResult(
            success=True,
            filename=output_filename,
            download_url=download_url,
            language_code=target_language,
            language_name=config["name"],
            language_native=config["native"],
            font_name="FreeSans (Unicode)"  # Universal font for Overleaf compatibility
        )
        
    except Exception as e:
        logger.error(f"❌ Translation failed: {str(e)}", exc_info=True)
        return SlidesTranslationResult(
            success=False,
            filename="",
            download_url="",
            language_code=target_language,
            language_name=config["name"],
            language_native=config["native"],
            font_name=config["font"],
            error=str(e)
        )
