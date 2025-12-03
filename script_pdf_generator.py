from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

import os

def create_script_pdf(json_data, output_filename="static/script_review.pdf"):
    # Ensure static directory exists
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    
    doc = SimpleDocTemplate(output_filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title = json_data.get('presentation_title', 'Presentation Script')
    story.append(Paragraph(title, styles['Title']))
    story.append(Spacer(1, 12))
    
    # Metadata Table
    metadata_style = ParagraphStyle(
        'MetadataLabel',
        parent=styles['Normal'],
        textColor=colors.HexColor('#0000FF'),
        fontName='Helvetica-Bold',
        fontSize=11
    )
    
    metadata_value_style = ParagraphStyle(
        'MetadataValue',
        parent=styles['Normal'],
        fontSize=10
    )
    
    # Build metadata table data
    metadata_data = []
    
    # Module
    module = json_data.get('module', 'N/A')
    metadata_data.append([
        Paragraph("<b>Module:</b>", metadata_style),
        Paragraph(module, metadata_value_style)
    ])
    
    # Episode
    episode = json_data.get('episode', 'N/A')
    metadata_data.append([
        Paragraph("<b>Episode:</b>", metadata_style),
        Paragraph(episode, metadata_value_style)
    ])
    
    # Learning Objectives
    learning_objectives = json_data.get('learning_objectives', [])
    if learning_objectives:
        obj_text = "<br/>".join([f"{i+1}. {obj}" for i, obj in enumerate(learning_objectives)])
        metadata_data.append([
            Paragraph("<b>Learning Objective:</b>", metadata_style),
            Paragraph(f"At the end of this tutorial learner will be able to<br/>{obj_text}", metadata_value_style)
        ])
    
    # Duration
    duration = json_data.get('duration', 'N/A')
    metadata_data.append([
        Paragraph("<b>Approx. Duration:</b>", metadata_style),
        Paragraph(duration, metadata_value_style)
    ])
    
    # Outline
    outline = json_data.get('outline', [])
    if outline:
        outline_text = "<br/>".join([f"• {item}" for item in outline])
        metadata_data.append([
            Paragraph("<b>Outline</b>", metadata_style),
            Paragraph(outline_text, metadata_value_style)
        ])
    
    # Meta Tags
    meta_tags = json_data.get('meta_tags', [])
    if meta_tags:
        tags_text = ", ".join(meta_tags)
        metadata_data.append([
            Paragraph("<b>Meta Tags</b>", metadata_style),
            Paragraph(tags_text, metadata_value_style)
        ])
    
    # Prerequisites
    prerequisites = json_data.get('prerequisites', 'None')
    metadata_data.append([
        Paragraph("<b>Pre-requisite Tutorial</b>", metadata_style),
        Paragraph(prerequisites, metadata_value_style)
    ])
    
    # Create and style metadata table
    metadata_table = Table(metadata_data, colWidths=[150, 350])
    metadata_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F0F0F0')),
    ]))
    
    story.append(metadata_table)
    story.append(Spacer(1, 20))

    # Slides
    for slide in json_data.get('slides', []):
        slide_id = slide.get('id', '')
        slide_title = slide.get('title', 'Untitled Slide')
        narration = slide.get('narration', 'No narration provided.')
        image_prompt = slide.get('image_prompt', 'No visual cue provided.')
        
        # Slide Header
        story.append(Paragraph(f"Slide {slide_id}: {slide_title}", styles['Heading2']))
        story.append(Spacer(1, 6))
        
        # Handle narration list
        if isinstance(narration, list):
            narration = "<br/>".join(narration)
            
        # Content Table
        data = [
            [Paragraph("<b>Visual Cue</b>", styles['Normal']), Paragraph("<b>Narration</b>", styles['Normal'])],
            [Paragraph(image_prompt, styles['Normal']), Paragraph(narration, styles['Normal'])]
        ]
        
        t = Table(data, colWidths=[150, 300])
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(t)
        story.append(Spacer(1, 12))
        
    doc.build(story)
    return output_filename
