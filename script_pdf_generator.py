from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER

import os

def create_script_pdf(json_data, output_filename="static/script_review.pdf"):
    """Generate a Spoken Tutorial script PDF matching the standard format."""
    # Ensure static directory exists
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    
    doc = SimpleDocTemplate(
        output_filename, 
        pagesize=letter,
        topMargin=40,
        bottomMargin=40,
        leftMargin=50,
        rightMargin=50
    )
    styles = getSampleStyleSheet()
    story = []

    # === HEADER SECTION ===
    
    # Main Title - Bold and larger
    title = json_data.get('presentation_title', 'Presentation Script')
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        fontName='Helvetica-Bold',
        alignment=TA_LEFT,
        spaceAfter=6
    )
    story.append(Paragraph(f"<b>Spoken Tutorial – {title}</b>", title_style))
    story.append(Spacer(1, 8))
    
    # Series and Title info (smaller text below main title)
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=4
    )
    
    # Add series info if available
    series = json_data.get('series', '')
    if series:
        story.append(Paragraph(f"Series: {series}", subtitle_style))
    
    # Add title line
    story.append(Paragraph(f"Title: {title}", subtitle_style))
    story.append(Spacer(1, 12))
    
    # === METADATA TABLE ===
    
    metadata_label_style = ParagraphStyle(
        'MetadataLabel',
        parent=styles['Normal'],
        textColor=colors.HexColor('#0066CC'),  # Blue color like in the image
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14
    )
    
    metadata_value_style = ParagraphStyle(
        'MetadataValue',
        parent=styles['Normal'],
        fontSize=10,
        leading=14
    )
    
    # Build metadata table data
    metadata_data = []
    
    # Module
    module = json_data.get('module', 'N/A')
    metadata_data.append([
        Paragraph("<b>Module</b>", metadata_label_style),
        Paragraph(module, metadata_value_style)
    ])
    
    # Episode
    episode = json_data.get('episode', 'N/A')
    metadata_data.append([
        Paragraph("<b>Episode</b>", metadata_label_style),
        Paragraph(episode, metadata_value_style)
    ])
    
    # Learning Objectives
    learning_objectives = json_data.get('learning_objectives', [])
    if learning_objectives:
        obj_html = "At the end of this tutorial learner will be able to<br/>"
        obj_html += "<br/>".join([f"{i+1}. {obj}" for i, obj in enumerate(learning_objectives)])
        metadata_data.append([
            Paragraph("<b>Learning Objective</b>", metadata_label_style),
            Paragraph(obj_html, metadata_value_style)
        ])
    
    # Duration
    duration = json_data.get('duration', 'N/A')
    metadata_data.append([
        Paragraph("<b>Approx. Duration</b>", metadata_label_style),
        Paragraph(duration, metadata_value_style)
    ])
    
    # Outline
    outline = json_data.get('outline', [])
    if outline:
        outline_html = "<br/>".join([f"• {item}" for item in outline])
        metadata_data.append([
            Paragraph("<b>Outline</b>", metadata_label_style),
            Paragraph(outline_html, metadata_value_style)
        ])
    
    # Meta Tags
    meta_tags = json_data.get('meta_tags', [])
    if meta_tags:
        tags_text = ", ".join(meta_tags)
        metadata_data.append([
            Paragraph("<b>Meta Tags</b>", metadata_label_style),
            Paragraph(tags_text, metadata_value_style)
        ])
    
    # Prerequisites
    prerequisites = json_data.get('prerequisites', 'None')
    metadata_data.append([
        Paragraph("<b>Pre-requisite Tutorial</b>", metadata_label_style),
        Paragraph(prerequisites, metadata_value_style)
    ])
    
    # Create and style metadata table
    metadata_table = Table(metadata_data, colWidths=[140, 380])
    metadata_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F0FE')),  # Light blue background
    ]))
    
    story.append(metadata_table)
    story.append(Spacer(1, 20))
    
    # === SCRIPT HEADER ===
    script_header_style = ParagraphStyle(
        'ScriptHeader',
        parent=styles['Heading2'],
        fontSize=14,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#0066CC'),
        spaceAfter=8
    )
    story.append(Paragraph("<b>Script</b>", script_header_style))
    story.append(Spacer(1, 8))
    
    # === SCRIPT TABLE ===
    
    script_cell_style = ParagraphStyle(
        'ScriptCell',
        parent=styles['Normal'],
        fontSize=10,
        leading=14
    )
    
    # Collect all slide rows
    script_rows = []
    
    # Header row
    script_rows.append([
        Paragraph("<b>Visual Cue</b>", script_cell_style),
        Paragraph("<b>Narration</b>", script_cell_style)
    ])
    
    # Add each slide as a row
    for i, slide in enumerate(json_data.get('slides', []), 1):
        slide_title = slide.get('title', 'Untitled Slide')
        narration = slide.get('narration', [])
        image_prompt = slide.get('image_prompt', 'No visual cue provided.')
        
        # Format narration
        if isinstance(narration, list):
            narration_text = "<br/><br/>".join(narration)
        else:
            narration_text = narration
        
        # Bold standard slide names in visual cues
        standard_slides = [
            "Title Slide",
            "Learning Objectives Slide",
            "System Requirements Slide",
            "Pre-requisite Slide",
            "Prerequisites Slide",
            "Assignment Slide",
            "Summary Slide",
            "Acknowledgement Slide",
            "Closing Slide"
        ]
        
        visual_cue_text = image_prompt
        for slide_name in standard_slides:
            if slide_name in visual_cue_text:
                visual_cue_text = visual_cue_text.replace(slide_name, f"<b>{slide_name}</b>")
        
        # Add slide row - Visual Cue uses image_prompt, not title
        script_rows.append([
            Paragraph(visual_cue_text, script_cell_style),  # Visual Cue column
            Paragraph(narration_text, script_cell_style)  # Narration column
        ])
    
    # Create script table
    script_table = Table(script_rows, colWidths=[240, 280])
    script_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E0E0E0')),  # Header background
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    
    story.append(script_table)
    
    # Build PDF
    doc.build(story)
    return output_filename
