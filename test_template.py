"""
Test script to generate a sample PDF with the new EduPyramids templates.
"""
import os
import subprocess
from pathlib import Path

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.services.latex_service import (
    escape_latex,
    render_learning_objectives,
    render_system_requirements,
    render_prerequisites,
    render_summary,
    render_assignment,
    render_thank_you,
    render_standard,
)

def generate_test_pdf():
    """Generate a test PDF with all slide types."""
    
    project_root = Path(__file__).parent
    logo_path = project_root / "static" / "logo.png"
    logo_abs_path = str(logo_path).replace('\\', '/')
    
    # Sample data - using episode field for title
    episode = "5. Introduction to API"
    import re
    topic_match = re.match(r'^\d+\.\s*(.+)$', episode)
    if topic_match:
        safe_title = topic_match.group(1).strip()
    else:
        safe_title = episode
    
    # Build LaTeX document
    latex_content = r"""
\documentclass[17pt,xcolor=table]{beamer} 
\setbeamersize{text margin left=0.75cm,text margin right=0.75cm}

% --- Packages ---
\mathversion{bold}
\usepackage{beamerthemesplit}
\usepackage{graphicx}
\usepackage{tikz}
\usetikzlibrary{calc}

% --- Colors and beamer setup ---
\definecolor{grey}{rgb}{0.44, 0.5, 0.58}
\setbeamercolor{structure}{fg=grey}
\setbeamercolor{alerted text}{fg=grey}

% --- Remove navigation symbols ---
\setbeamertemplate{navigation symbols}{}

% --- Bottom right logo on ALL slides via background template ---
\addtobeamertemplate{background}{%
  \begin{tikzpicture}[remember picture,overlay]
    \node[anchor=south west, xshift=110mm, yshift=7mm]
      at (current page.south west) {\includegraphics[height=1cm]{""" + logo_abs_path + r"""}};  
  \end{tikzpicture}%
}{}

% --- Title info ---
\title [""" + safe_title + r"""\hspace{0.5cm}]
{\large """ + safe_title + r"""}\date{}
\author [EduPyramids Educational Services Pvt.\ Ltd.]{%
{Spoken Tutorial}\\
  { \small brought to you by }\\
{EduPyramids Educational Services Pvt.\ Ltd.}\\
  {\textcolor{blue}{https://EduPyramids.org}}
}
\date{} % empty date

\begin{document}
\sffamily\bfseries

% ---- Title slide ----
\begin{frame}
  \titlepage
\end{frame}
"""
    
    # Add Learning Objectives slide
    lo_slide = {
        'title': 'Learning Objectives',
        'content': ['Define what an API is', 'Explain how APIs work', 'Identify common API use cases']
    }
    latex_content += render_learning_objectives(lo_slide)
    
    # Add System Requirements slide
    sysreq_slide = {
        'title': 'System Requirements',
        'content': ['A web browser', 'Internet connection', 'Google account (optional)']
    }
    latex_content += render_system_requirements(sysreq_slide)
    
    # Add Prerequisites slide (this now generates 2 slides)
    prereq_slide = {
        'title': 'Prerequisites',
        'content': ['Basic understanding of web browsing', 'Familiarity with URLs']
    }
    latex_content += render_prerequisites(prereq_slide)
    
    # Add a content slide
    content_slide = {
        'title': 'What is an API?',
        'content': ['Application Programming Interface', 'Bridge between applications', 'Enables data exchange']
    }
    latex_content += render_standard(content_slide)
    
    # Add Summary slide
    summary_slide = {
        'title': 'Summary',
        'content': ['APIs connect applications', 'They enable data sharing', 'Used in everyday apps']
    }
    latex_content += render_summary(summary_slide)
    
    # Add Assignment slide
    assignment_slide = {
        'title': 'Assignment',
        'content': ['Explore a public API', 'Try making a simple request', 'Compare results with a classmate']
    }
    latex_content += render_assignment(assignment_slide)
    
    # Add Thank You slide
    thankyou_slide = {'title': 'Thank You'}
    latex_content += render_thank_you(thankyou_slide)
    
    latex_content += r"\end{document}"
    
    # Write LaTeX file
    output_dir = project_root / "output"
    output_dir.mkdir(exist_ok=True)
    output_tex = output_dir / "test_template.tex"
    
    with open(str(output_tex), "w") as f:
        f.write(latex_content)
    
    print(f"✅ LaTeX written to: {output_tex}")
    
    # Compile PDF
    try:
        env = os.environ.copy()
        env["PATH"] = f"/Library/TeX/texbin:/usr/local/bin:{env['PATH']}"
        
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(output_dir), str(output_tex)],
            capture_output=True,
            env=env
        )
        
        output_pdf = output_dir / "test_template.pdf"
        if output_pdf.exists():
            print(f"✅ PDF generated: {output_pdf}")
            print(f"\n📂 Open with: open {output_pdf}")
        else:
            print("❌ PDF not generated. Check LaTeX errors:")
            print(result.stdout.decode()[-2000:])  # Last 2000 chars of output
            
    except Exception as e:
        print(f"❌ Compilation error: {e}")

if __name__ == "__main__":
    generate_test_pdf()
