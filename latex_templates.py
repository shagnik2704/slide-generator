import os
import re

def escape_latex(text):
    """Escapes special LaTeX characters while preserving markdown bold formatting."""
    if not isinstance(text, str):
        return str(text)
    
    # First, convert **bold** markdown to \textbf{bold} using a placeholder approach
    bold_parts = []
    
    def save_bold(match):
        bold_parts.append(match.group(1))
        return f'XBOLDMARKER{len(bold_parts)-1}X'
    
    # Extract bold text and replace with placeholders
    text = re.sub(r'\*\*(.+?)\*\*', save_bold, text)
    
    # Now escape special LaTeX characters
    replacements = {
        '\\': r'\textbackslash{}',
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    
    # Restore bold text with LaTeX formatting
    for i, bold_text in enumerate(bold_parts):
        text = text.replace(f'XBOLDMARKER{i}X', r'\textbf{' + bold_text + '}')
    
    return text

def generate_bullets(content_list):
    """Helper to generate itemize block"""
    if not content_list:
        return ""
    latex = "\\begin{itemize}\n"
    for item in content_list:
        latex += f"    \\item {escape_latex(item)}\n"
    latex += "\\end{itemize}"
    return latex

def add_logo_overlay():
    """Adds bottom-left logo overlay for intro/outro slides only."""
    logo_path = os.path.abspath("static/logo.png")
    return f"""\\begin{{tikzpicture}}[remember picture,overlay]
    \\node[anchor=south west, xshift=1.5mm, yshift=5mm]
      at (current page.south west) {{\\includegraphics[height=1.2cm]{{{logo_path}}}}};
  \\end{{tikzpicture}}
"""

# ============== NEW TEMPLATE-BASED RENDERERS ==============

def render_learning_objectives(slide):
    """Learning Objectives: Intro text + bullets + logo"""
    title = escape_latex(slide.get('title', 'Learning Objectives'))
    content = slide.get('content', [])
    
    latex = f"\\begin{{frame}}\n\\frametitle{{{title}}}\n"
    latex += add_logo_overlay()
    latex += "In this tutorial, we will learn,\n"
    latex += generate_bullets(content) + "\n"
    latex += "\\end{frame}\n"
    return latex

def render_system_requirements(slide):
    """System Requirements: Just bullets + logo"""
    title = escape_latex(slide.get('title', 'System Requirements'))
    content = slide.get('content', [])
    
    latex = f"\\begin{{frame}}\n\\frametitle{{{title}}}\n"
    latex += add_logo_overlay()
    latex += generate_bullets(content) + "\n"
    latex += "\\end{frame}\n"
    return latex

def render_prerequisites(slide):
    """Prerequisites: Just bullets + logo"""
    title = escape_latex(slide.get('title', 'Prerequisites'))
    content = slide.get('content', [])
    
    latex = f"\\begin{{frame}}\n\\frametitle{{{title}}}\n"
    latex += add_logo_overlay()
    latex += generate_bullets(content) + "\n"
    latex += "\\end{frame}\n"
    return latex


def render_content_blank(slide):
    """Content slide with no text - just title (for image-only slides)"""
    title = escape_latex(slide.get('title', ''))
    image_path = slide.get('image_path')
    
    latex = f"\\begin{{frame}}\n\\frametitle{{{title}}}\n"
    if image_path and os.path.exists(image_path):
        abs_image_path = os.path.abspath(image_path)
        latex += "\\begin{center}\n"
        latex += f"    \\includegraphics[width=0.8\\textwidth,height=0.7\\textheight,keepaspectratio]{{{abs_image_path}}}\n"
        latex += "\\end{center}\n"
    latex += "\\end{frame}\n"
    return latex

def render_content_centered(slide):
    """Content slide with centered text (no bullets)"""
    title = escape_latex(slide.get('title', ''))
    content = slide.get('content', [])
    
    latex = f"\\begin{{frame}}\n\\frametitle{{{title}}}\n"
    latex += "\\begin{center}\n"
    for item in content:
        latex += f"    {escape_latex(item)} \\\\\n"
    latex += "\\end{center}\n"
    latex += "\\end{frame}\n"
    return latex

def render_two_column(slide):
    """Two-column layout: Image Left, Text Right"""
    title = escape_latex(slide.get('title', ''))
    content = slide.get('content', [])
    image_path = slide.get('image_path')
    
    latex = f"\\begin{{frame}}\n\\frametitle{{{title}}}\n"
    latex += "\\begin{columns}\n"
    
    # Image Column (Left)
    latex += "    \\begin{column}{0.5\\textwidth}\n"
    latex += "        \\centering\n"
    if image_path and os.path.exists(image_path):
        abs_image_path = os.path.abspath(image_path)
        latex += f"        \\includegraphics[width=0.9\\textwidth,height=0.7\\textheight,keepaspectratio]{{{abs_image_path}}}\n"
    latex += "    \\end{column}\n"
    
    # Text Column (Right)
    latex += "    \\begin{column}{0.5\\textwidth}\n"
    for item in content:
        latex += f"        {escape_latex(item)} \\\\\n"
    latex += "    \\end{column}\n"
    
    latex += "\\end{columns}\n"
    latex += "\\end{frame}\n"
    return latex

def render_summary(slide):
    """Summary: Intro text + bullets + logo"""
    title = escape_latex(slide.get('title', 'Summary'))
    content = slide.get('content', [])
    
    latex = f"\\begin{{frame}}\n\\frametitle{{{title}}}\n"
    latex += add_logo_overlay()
    latex += "In this tutorial, we learned that:\n"
    latex += generate_bullets(content) + "\n"
    latex += "\\end{frame}\n"
    return latex

def render_assignment(slide):
    """Assignment: Just bullets + logo"""
    title = escape_latex(slide.get('title', 'Assignment'))
    content = slide.get('content', [])
    
    latex = f"\\begin{{frame}}\n\\frametitle{{{title}}}\n"
    latex += add_logo_overlay()
    latex += generate_bullets(content) + "\n"
    latex += "\\end{frame}\n"
    return latex

def render_thank_you(slide):
    """Domain Expert / Thank You slide"""
    content = slide.get('content', [])
    # Try to extract domain expert info from content
    expert_name = content[0] if len(content) > 0 else "(Domain Expert)"
    affiliation = content[1] if len(content) > 1 else "Affiliation"
    
    latex = "\\begin{frame}\n"
    latex += "  \\centering   \\vspace{12pt}\n"
    latex += "{ \\small Domain Expert}\\\\[12pt]\n"
    latex += f"{{\\textcolor{{blue}}{{{escape_latex(expert_name)}}}}}\\\\\n"
    latex += f" {{ {escape_latex(affiliation)}}}\\\\  [1.5cm]\n"
    latex += " \\large Thank you\n"
    latex += "\\end{frame}\n"
    return latex

def render_standard(slide):
    """Standard layout: Title + Bullets Left + Image Right (if image exists)"""
    title = escape_latex(slide.get('title', ''))
    content = slide.get('content', [])
    image_path = slide.get('image_path')
    
    latex = f"\\begin{{frame}}\n\\frametitle{{{title}}}\n"
    
    if image_path and os.path.exists(image_path):
        abs_image_path = os.path.abspath(image_path)
        latex += "\\begin{columns}\n"
        latex += "    \\begin{column}{0.5\\textwidth}\n"
        latex += generate_bullets(content) + "\n"
        latex += "    \\end{column}\n"
        latex += "    \\begin{column}{0.5\\textwidth}\n"
        latex += "        \\centering\n"
        latex += f"        \\includegraphics[width=\\textwidth,height=0.7\\textheight,keepaspectratio]{{{abs_image_path}}}\n"
        latex += "    \\end{column}\n"
        latex += "\\end{columns}\n"
    else:
        latex += generate_bullets(content) + "\n"
        
    latex += "\\end{frame}\n"
    return latex

def render_text_only(slide):
    """Text Only Layout: Just title + bullets, no image"""
    title = escape_latex(slide.get('title', ''))
    content = slide.get('content', [])
    
    latex = f"\\begin{{frame}}\n\\frametitle{{{title}}}\n"
    latex += generate_bullets(content) + "\n"
    latex += "\\end{frame}\n"
    return latex

def get_renderer(layout_name):
    """Factory to get the correct renderer based on layout name"""
    renderers = {
        # New template-based layouts
        "learning_objectives": render_learning_objectives,
        "system_requirements": render_system_requirements,
        "prerequisites": render_prerequisites,
        "content_blank": render_content_blank,
        "content_centered": render_content_centered,
        "two_column": render_two_column,
        "summary": render_summary,
        "assignment": render_assignment,
        "thank_you": render_thank_you,
        # Standard layouts
        "standard": render_standard,
        "text_only": render_text_only,
        "bullets_left_image_right": render_standard,
        "image_left": render_two_column,
        # Image-only layouts
        "full_image": render_content_blank,
    }
    return renderers.get(layout_name, render_standard)

def get_renderer_by_title(slide_title):
    """Auto-detect renderer based on slide title"""
    title_lower = slide_title.lower().strip()
    
    if 'learning objective' in title_lower:
        return render_learning_objectives
    elif 'system requirement' in title_lower:
        return render_system_requirements
    elif 'prerequisite' in title_lower or 'pre-requisite' in title_lower:
        return render_prerequisites
    elif 'summary' in title_lower:
        return render_summary
    elif 'assignment' in title_lower:
        return render_assignment
    elif 'thank you' in title_lower or 'thank-you' in title_lower:
        return render_thank_you
    else:
        return render_standard
