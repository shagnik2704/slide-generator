import os

def escape_latex(text):
    """Escapes special LaTeX characters."""
    if not isinstance(text, str):
        return str(text)
    
    # Note: Backslash must be replaced first to avoid escaping the backslashes 
    # introduced by other replacements.
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
    return text

def generate_bullets(content_list):
    """Helper to generate itemize block"""
    if not content_list:
        return ""
    latex = "\\begin{itemize}\n"
    for i, item in enumerate(content_list):
        # Start from overlay 2, so overlay 1 is empty (Title only)
        # This aligns with the audio generation which has (Intro + N bullets) segments.
        latex += f"    \\item<{i+2}-> {escape_latex(item)}\n"
    latex += "\\end{itemize}"
    return latex

def render_standard(slide):
    """
    Standard layout: Title, Bullets Left, Image Right (if image exists)
    Otherwise just bullets.
    """
    title = escape_latex(slide.get('title', ''))
    content = slide.get('content', [])
    image_path = slide.get('image_path')
    
    latex = f"\\begin{{frame}}{{{title}}}\n"
    
    if image_path and not image_path.lower().endswith('.mp4'):
        latex += "    \\begin{columns}\n"
        latex += "        \\column{0.5\\textwidth}\n"
        latex += f"{generate_bullets(content)}\n"
        latex += "        \\column{0.5\\textwidth}\n"
        latex += "        \\begin{center}\n"
        latex += f"            \\includegraphics[width=\\textwidth,height=0.7\\textheight,keepaspectratio]{{{image_path}}}\n"
        latex += "        \\end{center}\n"
        latex += "    \\end{columns}\n"
    else:
        latex += f"{generate_bullets(content)}\n"
        
    latex += "\\end{frame}\n"
    return latex

def render_split_vertical(slide):
    """
    Split Vertical: Image Left, Text Right
    """
    title = escape_latex(slide.get('title', ''))
    content = slide.get('content', [])
    image_path = slide.get('image_path')
    
    latex = f"\\begin{{frame}}{{{title}}}\n"
    latex += "    \\begin{columns}\n"
    
    # Image Column (Left)
    latex += "        \\column{0.45\\textwidth}\n"
    if image_path and not image_path.lower().endswith('.mp4'):
        latex += "        \\begin{center}\n"
        latex += f"            \\includegraphics[width=\\textwidth,height=0.8\\textheight,keepaspectratio]{{{image_path}}}\n"
        latex += "        \\end{center}\n"
    
    # Text Column (Right)
    latex += "        \\column{0.55\\textwidth}\n"
    latex += f"{generate_bullets(content)}\n"
    
    latex += "    \\end{columns}\n"
    latex += "\\end{frame}\n"
    return latex

def render_quote(slide):
    """
    Quote Layout: Large centered text, no bullets, optional background image
    """
    content = slide.get('content', [])
    quote_text = escape_latex(content[0]) if content else ""
    author = escape_latex(content[1]) if len(content) > 1 else ""
    image_path = slide.get('image_path')
    
    latex = "\\begin{frame}[plain]\n"
    
    if image_path and not image_path.lower().endswith('.mp4'):
        # Background image with opacity
        latex += "    \\begin{tikzpicture}[remember picture,overlay]\n"
        latex += "        \\node[opacity=0.2,at=(current page.center)] {\n"
        latex += f"            \\includegraphics[width=\\paperwidth,height=\\paperheight,keepaspectratio]{{{image_path}}}\n"
        latex += "        };\n"
        latex += "    \\end{tikzpicture}\n"
    
    latex += "    \\begin{center}\n"
    latex += "        \\vspace{1cm}\n"
    latex += "        \\Huge\\itshape\n"
    latex += f"        ``{quote_text}''\n"
    latex += "        \\vspace{1cm}\n"
    latex += "        \\Large\\upshape\n"
    if author:
        latex += f"        --- {author}\n"
    latex += "    \\end{center}\n"
    latex += "\\end{frame}\n"
    return latex

def render_immersive(slide):
    """
    Immersive Layout: Full screen image with text overlay
    """
    title = escape_latex(slide.get('title', ''))
    content = slide.get('content', [])
    main_point = escape_latex(content[0]) if content else ""
    image_path = slide.get('image_path')
    
    latex = "\\begin{frame}[plain]\n"
    
    if image_path and not image_path.lower().endswith('.mp4'):
        latex += "    \\begin{tikzpicture}[remember picture,overlay]\n"
        latex += "        \\node[at=(current page.center)] {\n"
        latex += f"            \\includegraphics[width=\\paperwidth,height=\\paperheight]{{{image_path}}}\n"
        latex += "        };\n"
        # Text overlay box
        latex += "        \\node[text width=0.8\\paperwidth,fill=black,fill opacity=0.7,text opacity=1,\n"
        latex += "              text=white,rounded corners,inner sep=1cm,align=center] at (current page.center) {\n"
        latex += f"            \\Huge\\textbf{{{title}}}\\\\[1em]\n"
        latex += f"            \\Large {main_point}\\\\[2em]\n"
        latex += "            \\large Madhulika Goyal \\\\ IIT Bombay \\\\ \\insertdate\n"
        latex += "        };\n"
        # Logo overlay (Bottom Right)
        latex += "        \\node[anchor=south east, inner sep=0.5cm] at (current page.south east) {\n"
        latex += f"            \\includegraphics[width=2.5cm]{{{os.path.abspath('assets/logo.png')}}}\n"
        latex += "        };\n"
        latex += "    \\end{tikzpicture}\n"
    else:
        # Fallback if no image
        latex += f"    \\frametitle{{{title}}}\n"
        latex += f"    \\begin{{center}}\\Huge {main_point}\\\\[2em] Madhulika Goyal \\\\ IIT Bombay \\\\ \\insertdate\\end{{center}}\n"
        
    latex += "\\end{frame}\n"
    return latex

def render_big_number(slide):
    """
    Big Number Layout: For statistics or key figures
    """
    title = escape_latex(slide.get('title', ''))
    content = slide.get('content', [])
    number = escape_latex(content[0]) if content else ""
    description = escape_latex(content[1]) if len(content) > 1 else ""
    
    latex = f"\\begin{{frame}}{{{title}}}\n"
    latex += "    \\begin{center}\n"
    latex += "        \\vspace{1cm}\n"
    latex += f"        \\resizebox{{!}}{{3cm}}{{\\textbf{{{number}}}}}\\\\[1em]\n"
    latex += f"        \\Large {description}\n"
    latex += "    \\end{center}\n"
    latex += "\\end{frame}\n"
    return latex

def get_renderer(layout_name):
    """Factory to get the correct renderer"""
    renderers = {
        "standard": render_standard,
        "image_left": render_split_vertical,
        "quote": render_quote,
        "immersive": render_immersive,
        "big_number": render_big_number
    }
    return renderers.get(layout_name, render_standard)
