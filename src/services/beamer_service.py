"""
Beamer slide template generation service.
Generates LaTeX Beamer templates with boilerplate slides filled in.
"""
import re
from typing import Optional, List


# The slate grey the decks have always used, as a hex colour.
DEFAULT_THEME_COLOR = "#708094"

_HEX_COLOR_RE = re.compile(r"^#?(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$")


def normalize_theme_color(value: Optional[str]) -> str:
    """Validate a caller-supplied theme colour, returning 6 uppercase hex digits.

    The result is interpolated straight into a .tex file that the user then
    compiles, so anything that is not a plain hex colour is rejected outright
    rather than escaped.
    """
    if value is None or value == "":
        value = DEFAULT_THEME_COLOR
    if not isinstance(value, str) or not _HEX_COLOR_RE.match(value.strip()):
        raise ValueError(
            f"Invalid theme colour {value!r}; expected a hex colour such as {DEFAULT_THEME_COLOR}"
        )

    digits = value.strip().lstrip("#").upper()
    if len(digits) == 3:  # #abc -> #aabbcc
        digits = "".join(char * 2 for char in digits)
    return digits


def generate_beamer_template(
    tutorial_name: str = "Tutorial Name",
    learning_objectives: Optional[List[str]] = None,
    learning_objectives_intro: Optional[str] = None,
    prerequisites: Optional[List[str]] = None,
    prerequisites_intro: Optional[str] = None,
    prerequisites_footer: Optional[str] = None,
    system_requirements: Optional[List[str]] = None,
    system_requirements_intro: Optional[str] = None,
    summary_points: Optional[List[str]] = None,
    summary_intro: Optional[str] = None,
    assignment_items: Optional[List[str]] = None,
    assignment_intro: Optional[str] = None,
    domain_expert: Optional[str] = None,
    domain_expert_org: Optional[str] = None,
    code_file_info: Optional[str] = None,
    theme_color: Optional[str] = None,
) -> str:
    """
    Generate a Beamer LaTeX template with boilerplate slides.
    
    Args:
        tutorial_name: Name of the tutorial (appears on title slide)
        learning_objectives: List of learning objective bullet points
        learning_objectives_intro: Custom intro phrase (e.g., "In this tutorial, you will learn how to")
        prerequisites: List of prerequisite bullet points
        prerequisites_intro: Custom intro phrase for prerequisites
        prerequisites_footer: Footer text like 'For prerequisite tutorials please visit this website'
        system_requirements: List of system requirement bullet points
        system_requirements_intro: Custom intro phrase for system requirements
        summary_points: List of summary bullet points
        summary_intro: Custom intro phrase for summary
        assignment_items: List of assignment bullet points
        assignment_intro: Custom intro phrase for assignment
        domain_expert: Name of the domain expert (for Thank You slide)
        domain_expert_org: Organization of domain expert
        code_file_info: Optional code file description
        theme_color: Hex colour for frame titles, bullets and title-slide
            accents (e.g. "#1F4E79"). Defaults to the slate grey used so far.

    Returns:
        Complete LaTeX Beamer document as a string

    Raises:
        ValueError: If theme_color is not a hex colour.
    """
    theme_hex = normalize_theme_color(theme_color)

    # Default content if not provided
    lo_items = learning_objectives or ["Sample learning objective 1", "Sample learning objective 2"]
    prereq_items = prerequisites or ["familiar with basic concepts", "No coding knowledge is required"]
    sys_req_items = system_requirements or [
        "A computer/laptop/smartphone",
        "A stable internet connection", 
        "An updated web browser, such as Google Chrome/Microsoft Edge/Mozilla Firefox"
    ]
    summary_items = summary_points or ["Key concept 1", "Key concept 2"]
    assignment_list = assignment_items or ["Practice exercise 1", "Practice exercise 2"]
    expert_name = domain_expert or ""
    expert_org = domain_expert_org or ""
    
    # Default intro phrases (can be overridden by LLM extraction)
    lo_intro = learning_objectives_intro or "In this tutorial, you will learn to"
    prereq_intro = prerequisites_intro or "To follow this tutorial you should be"
    sys_req_intro = system_requirements_intro or "For this tutorial, you will need"
    summary_intro_text = summary_intro or "In this tutorial, you learned about"
    assignment_intro_text = assignment_intro or ""  # Assignment typically has no intro
    
    # Clean up tutorial name (remove trailing punctuation and markdown)
    tutorial_name = tutorial_name.replace('**', '').replace('*', '').rstrip('.!?').strip()
    
    # Build the LaTeX document
    tex_content = rf'''\documentclass[17pt,xcolor=table]{{beamer}} 
\setbeamersize{{text margin left=0.50cm,text margin right=0.50cm}}

% --- Packages ---
\mathversion{{bold}}
\usepackage{{beamerthemesplit}}
\usepackage{{graphicx}}
\usepackage{{tikz}}
\usetikzlibrary{{calc}}

% --- Colors and beamer setup ---
\definecolor{{themecolor}}{{HTML}}{{{theme_hex}}}
\setbeamercolor{{structure}}{{fg=themecolor}}
\setbeamercolor{{alerted text}}{{fg=themecolor}}

% --- Bottom-right logo on ALL slides via background template ---
\addtobeamertemplate{{background}}{{%
  \begin{{tikzpicture}}[remember picture,overlay]
    \node[anchor=south west, xshift=110mm, yshift=7mm]
      at (current page.south west) {{\includegraphics[height=1cm]{{logo.png}}}};
  \end{{tikzpicture}}%
}}{{}}


% --- Title info ---
 \title [{tutorial_name}\hspace{{0.5cm}}]
{{{tutorial_name}}}\date{{}}
\author [EduPyramids]{{\\ \vspace {{0.75cm}}
  {{ \small Spoken Tutorial brought to you by EduPyramids}}\\ 
 {{\textcolor{{blue}}{{https://EduPyramids.org}}}}
}}
\date{{}} % empty date

\begin{{document}}
\sffamily\bfseries

% ---- Title slide ----
\begin{{frame}}
  \titlepage
\end{{frame}}

% ---- Content slide: Learning Objectives ----
\begin{{frame}}
\frametitle{{Learning Objectives}}
{lo_intro}:\\
\begin{{itemize}}
'''
    
    # Add learning objectives
    for item in lo_items:
        tex_content += f"\\item {item}\n"
    
    tex_content += rf'''\end{{itemize}}
\end{{frame}}


% ---- Content slide: System Requirements ----
\begin{{frame}}
\frametitle{{System Requirements}}
{sys_req_intro}: \\
\begin{{itemize}}
'''
    
    # Add system requirements
    for item in sys_req_items:
        tex_content += f"\\item {item}\n"
    
    tex_content += rf'''\end{{itemize}}
\end{{frame}}

% ---- Content slide: Pre-requisites ----
\begin{{frame}}
\frametitle{{Pre-requisites}}
{prereq_intro}: \\
\begin{{itemize}}
'''
    
    # Add prerequisites
    for item in prereq_items:
        tex_content += f"\\item {item}\n"

    tex_content += r'''\end{itemize}
'''
    
    # Add footer text if provided, otherwise use default
    footer_text = prerequisites_footer or "For the prerequisite tutorials please visit this website."
    tex_content += rf''' \vspace{{0.5cm}}
{footer_text} \\
 \large \textcolor{{blue}}{{https://EduPyramids.org}}
\end{{frame}}

'''

    # Code file slide - always included as standard boilerplate
    tex_content += r'''% ---- Content slide: Code file ----
\begin{frame}
\frametitle{Code file}
% Add code file name/description here \\[8pt]
This file is provided in the Code Files link of this tutorial page
\end{frame}

'''


    tex_content += r'''% ============================================
% CONTENT SLIDES - Add your content here
% ============================================

'''
    
    # Add Summary slide
    tex_content += rf'''% ---- Content slide: Summary ----
\begin{{frame}}
\frametitle{{Summary}}
{summary_intro_text}: \\
\begin{{itemize}}
'''
    
    # Add summary points
    for item in summary_items:
        tex_content += f"\\item {item}\n"
    
    tex_content += r'''\end{itemize}
\end{frame}


% ---- Content slide: Assignment ----
\begin{frame}
\frametitle{Assignment}
'''

    # Add assignment intro if provided
    if assignment_intro_text:
        tex_content += f"{assignment_intro_text} \\\\\n"
    
    tex_content += r'''\begin{itemize}
'''
    
    # Add assignment items
    for item in assignment_list:
        tex_content += f"\\item {item}\n"
    
    tex_content += r'''\end{itemize}
\end{frame}


% ---- Domain expert / closing slide ----
\begin{frame}
  \centering
  \vspace{1cm}
  {\small Domain Expert}\\
  {\textcolor{blue}{Expert Name}}\\
  {Organization}\\[50pt]
  {\large Thank you}\\[20pt]
\end{frame}

\end{document}
'''
    
    return tex_content

