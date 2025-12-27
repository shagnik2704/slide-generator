"""
Course Outline PDF Export Service.
Converts outline_data JSON to PDF matching the ST Course Outline template.
"""
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER


def create_outline_pdf(outline_data: dict, output_path: str = None) -> str:
    """
    Generate a PDF from course outline data matching the ST template.
    
    Args:
        outline_data: The outline_data dict from outline_chat
        output_path: Optional output path. If None, saves to static/
        
    Returns:
        Path to the generated PDF
    """
    # Get project root
    project_root = Path(__file__).parent.parent.parent
    static_dir = project_root / "static"
    static_dir.mkdir(exist_ok=True)
    
    if output_path is None:
        base_name = outline_data.get('outline_name') or outline_data.get('tutorial_name') or 'outline'
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in base_name)
        output_path = static_dir / f"course_outline_{safe_name[:30]}.pdf"
    
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=1*cm,
        bottomMargin=1*cm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=20
    )
    heading_style = ParagraphStyle(
        'HeadingStyle',
        parent=styles['Heading2'],
        fontSize=12,
        spaceBefore=15,
        spaceAfter=8,
        textColor=colors.HexColor('#333333')
    )
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14
    )
    
    story = []
    
    # === TITLE ===
    story.append(Paragraph("Course Outline - Format", title_style))
    story.append(Spacer(1, 10))
    
    # === METADATA TABLE ===
    # Determine outline type (FOSS or ICT)
    outline_type = outline_data.get('outline_type', 'FOSS').upper()
    
    # Get platform name (FOSS/ICT tool name and version)
    platform_name = outline_data.get('platform_name', 'Not Applicable for this series')
    if not platform_name or platform_name.strip() == '':
        platform_name = 'Not Applicable for this series'
    
    # Use appropriate label based on outline type
    if outline_type == 'ICT':
        platform_label = "ICT Platform/Program"
    else:
        platform_label = "FOSS Version"
    
    metadata_rows = [
        ["Course Outline Name", outline_data.get('outline_name', outline_data.get('tutorial_name', ''))],
        [platform_label, platform_name],
        ["Target Audience", outline_data.get('target_audience', '')],
        ["Entry Behaviour", outline_data.get('entry_behaviour', '')],
        ["Purpose", outline_data.get('purpose', '')],
        ["OS version", outline_data.get('os_version', 'Not Applicable for this series')],
        ["Recommended no. of tutorials", str(outline_data.get('recommended_no_of_tutorials', ''))],
        ["Prepared by", outline_data.get('prepared_by', '')],
        ["Domain", outline_data.get('domain', '')],
        ["Reviewer", outline_data.get('reviewer', 'IITB ST Team')],
        ["Client Side Reviewer", "Will be from the IITB ST Team. Hence you may leave this blank."],
        ["Date", outline_data.get('date', '')],
        ["Keywords", "; ".join(outline_data.get('keywords', []))],
    ]
    
    # Convert to Paragraphs for word wrap
    metadata_table_data = []
    for label, value in metadata_rows:
        metadata_table_data.append([
            Paragraph(f"<b>{label}</b>", normal_style),
            Paragraph(str(value), normal_style)
        ])
    
    metadata_table = Table(metadata_table_data, colWidths=[4*cm, 14*cm])
    metadata_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f5f5')),
    ]))
    story.append(metadata_table)
    story.append(Spacer(1, 20))
    
    # === COURSE OBJECTIVES ===
    story.append(Paragraph("<b>Course Objectives:</b>", heading_style))
    objectives = outline_data.get('course_objectives', [])
    if objectives:
        for obj in objectives:
            story.append(Paragraph(f"• {obj}", normal_style))
    story.append(Spacer(1, 15))
    
    # === TOPICS INCLUDED ===
    story.append(Paragraph("<b>Topics Included</b>", heading_style))
    topics_included = outline_data.get('topics_included', [])
    if topics_included:
        for topic in topics_included:
            story.append(Paragraph(f"• {topic}", normal_style))
    story.append(Spacer(1, 15))
    
    # === TOPICS NOT INCLUDED ===
    story.append(Paragraph("<b>Topics Not Included</b>", heading_style))
    topics_not_included = outline_data.get('topics_not_included', [])
    if topics_not_included:
        for topic in topics_not_included:
            story.append(Paragraph(f"• {topic}", normal_style))
    story.append(Spacer(1, 15))
    
    # === EXAMPLES ===
    # Use appropriate labels based on outline type
    if outline_type == 'ICT':
        core_example_label = "Teaching Scenarios/Examples (core use case)"
        allied_example_label = "Allied examples/scenarios"
    else:
        core_example_label = "Core example used in the series"
        allied_example_label = "Allied examples used in this series"
    
    examples_rows = [
        [core_example_label, outline_data.get('core_example', '')],
        [allied_example_label, "; ".join(outline_data.get('allied_examples', []))],
    ]
    examples_table_data = []
    for label, value in examples_rows:
        examples_table_data.append([
            Paragraph(f"<b>{label}</b>", normal_style),
            Paragraph(str(value), normal_style)
        ])
    
    examples_table = Table(examples_table_data, colWidths=[5*cm, 13*cm])
    examples_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f5f5')),
    ]))
    story.append(examples_table)
    story.append(Spacer(1, 20))
    
    # === COURSE OUTLINE GUIDELINES ===
    story.append(Paragraph("<b>Course Outline Guidelines</b>", heading_style))
    if outline_type == 'ICT':
        guidelines = [
            "Focus on skill-building and practical application (what learners will DO or TEACH).",
            "Include teaching methodologies and integration strategies.",
            "Use relatable teaching scenarios and real-world educational applications.",
            "Keep content practical and actionable (avoid pure theory).",
            "Organize topics by categories or skill areas when helpful.",
            "Each tutorial should focus on a specific skill, methodology, or integration strategy.",
            "Avoid repetition across tutorials.",
            "Flag topics that are too advanced or off-scope."
        ]
    else:  # FOSS
        guidelines = [
            "Every script should be written such that 75-80% of the content is the demonstration.",
            "Keep theory to a minimum.",
            "Do not use the Menu-based approach to explain the features of the software.",
            "Cover crucial and important features in detail.",
            "Avoid repetitions across the outline or across scripts or within a script.",
            "Provide quick pointers for less important features.",
            "Avoid spending too much time on topics which learners can figure out on their own.",
            "Refer to other features in assignments with an appropriate number of hints to help the learner."
        ]
    for g in guidelines:
        story.append(Paragraph(f"• {g}", normal_style))
    story.append(Spacer(1, 20))
    
    # === TUTORIAL TABLE ===
    tutorial_rows = outline_data.get('tutorial_rows', [])
    
    for tutorial in tutorial_rows:
        tutorial_num = tutorial.get('tutorial_number', 1)
        title = tutorial.get('title', f'Tutorial {tutorial_num}')
        
        story.append(Paragraph(f"<b>Tutorial Title {tutorial_num}: {title}</b>", heading_style))
        
        # Handle prerequisites as list or string (for backward compatibility)
        prerequisites_data = tutorial.get('prerequisites', [])
        if isinstance(prerequisites_data, list):
            prerequisites = '; '.join(prerequisites_data) if prerequisites_data else 'N/A'
        else:
            prerequisites = prerequisites_data if prerequisites_data else 'N/A'
        
        # Table header
        table_data = [
            [
                Paragraph("<b>Prerequisites</b>", normal_style),
                Paragraph("<b>Topics Details</b>", normal_style),
                Paragraph("<b>Time (range)</b>", normal_style),
                Paragraph("<b>Comments</b>", normal_style)
            ]
        ]
        
        # Add each topic as a row
        topics = tutorial.get('topics_details', [])
        time_seconds = tutorial.get('time_seconds', 180)
        
        # Format time display as range if available
        time_range = tutorial.get('time_range')
        if time_range:
            min_minutes = time_range.get('min_seconds', 0) // 60
            max_minutes = time_range.get('max_seconds', 0) // 60
            if min_minutes == max_minutes:
                time_display = f"{min_minutes} min"
            else:
                time_display = f"{min_minutes}-{max_minutes} min"
        else:
            # Fallback to time_seconds
            time_display = f"{time_seconds // 60} min" if time_seconds > 0 else "0 min"
        
        comments = tutorial.get('comments', '')
        
        for i, topic in enumerate(topics):
            table_data.append([
                Paragraph(prerequisites if i == 0 else "", normal_style),
                Paragraph(f"{i+1}. {topic}", normal_style),
                Paragraph(time_display if i == 0 else "", normal_style),
                Paragraph(comments if i == 0 else "", normal_style)
            ])
        
        # Add empty rows if needed (template shows 4 rows minimum)
        while len(table_data) < 5:
            table_data.append([
                Paragraph("", normal_style),
                Paragraph(f"{len(table_data)}. ", normal_style),
                Paragraph("", normal_style),
                Paragraph("", normal_style)
            ])
        
        tutorial_table = Table(table_data, colWidths=[4*cm, 8*cm, 3*cm, 3*cm])
        tutorial_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8e8e8')),
        ]))
        story.append(tutorial_table)
        story.append(Spacer(1, 15))
    
    # Build PDF
    doc.build(story)
    print(f"✅ Generated outline PDF: {output_path}")
    
    return str(output_path)


if __name__ == "__main__":
    # Test with sample data
    sample_data = {
        "tutorial_name": "Ethics, Responsibility and Future of AI",
        "target_audience": "Everyone",
        "entry_behaviour": "Basics of generative AI",
        "purpose": "Understand the societal impact of GenAI",
        "recommended_no_of_tutorials": 1,
        "prepared_by": "Test User",
        "date": "2024-12-18",
        "keywords": ["GenAI", "AI", "Ethics"],
        "about_course": "This course teaches about AI ethics and responsibility.",
        "course_objectives": ["Understand AI ethics", "Recognize misinformation"],
        "topics_included": ["Bias in AI", "Deepfakes"],
        "topics_not_included": ["Coding"],
        "core_example": "An AI trained on biased data...",
        "allied_examples": ["Deepfake videos", "Fake audio"],
        "tutorial_rows": [
            {
                "tutorial_number": 1,
                "title": "Introduction to AI Ethics",
                "topics_details": ["What is AI bias", "Examples of bias", "How to detect bias"],
                "time_seconds": 300,
                "comments": ""
            }
        ]
    }
    create_outline_pdf(sample_data)
