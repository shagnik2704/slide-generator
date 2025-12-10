from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import re
import os

def convert_bold_markdown(text):
    """Convert **text** to <b>text</b> for PDF rendering."""
    if not text:
        return text
    return re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', str(text))

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
    
    # Avoid duplication: only add prefix if title doesn't already start with "Spoken Tutorial"
    if title.startswith("Spoken Tutorial"):
        display_title = title
    else:
        display_title = f"Spoken Tutorial – {title}"
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        fontName='Helvetica-Bold',
        alignment=TA_LEFT,
        spaceAfter=6
    )
    story.append(Paragraph(f"<b>{display_title}</b>", title_style))
    story.append(Spacer(1, 12))
    
    # Removed redundant "Title:" line - already shown in header
    
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
        Paragraph(convert_bold_markdown(module), metadata_value_style)
    ])
    
    # Tutorial (was Episode)
    tutorial = json_data.get('episode', 'N/A')
    metadata_data.append([
        Paragraph("<b>Tutorial</b>", metadata_label_style),
        Paragraph(convert_bold_markdown(tutorial), metadata_value_style)
    ])
    
    # Learning Objectives
    learning_objectives = json_data.get('learning_objectives', [])
    if learning_objectives:
        obj_html = "At the end of this tutorial learner will be able to<br/>"
        obj_html += "<br/>".join([f"{i+1}. {convert_bold_markdown(obj)}" for i, obj in enumerate(learning_objectives)])
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
        outline_html = "<br/>".join([f"• {convert_bold_markdown(item)}" for item in outline])
        metadata_data.append([
            Paragraph("<b>Outline</b>", metadata_label_style),
            Paragraph(outline_html, metadata_value_style)
        ])
    
    # Meta Tags
    meta_tags = json_data.get('meta_tags', [])
    if meta_tags:
        tags_text = ", ".join([convert_bold_markdown(tag) for tag in meta_tags])
        metadata_data.append([
            Paragraph("<b>Meta Tags</b>", metadata_label_style),
            Paragraph(tags_text, metadata_value_style)
        ])
    
    # Prerequisites
    prerequisites = json_data.get('prerequisites', 'None')
    metadata_data.append([
        Paragraph("<b>Pre-requisite Tutorial</b>", metadata_label_style),
        Paragraph(convert_bold_markdown(prerequisites), metadata_value_style)
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
            # Convert \n to <br/> for PDF rendering
            narration_text = narration.replace('\n', '<br/>')
        
        # Convert bullet character to ensure it renders in PDF
        # Replace unicode bullet (•) with a dash or HTML entity that ReportLab supports
        narration_text = narration_text.replace('•', '&#8226;')
        
        # Convert **word** to <b>word</b> for non-translatable terms
        # These words will appear bold in the PDF to indicate "do not translate"
        narration_text = convert_bold_markdown(narration_text)
        
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
        
        visual_cue_text = image_prompt if image_prompt else "No visual cue provided."
        
        # Ensure it's a string (just in case)
        if not isinstance(visual_cue_text, str):
            visual_cue_text = str(visual_cue_text)

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
