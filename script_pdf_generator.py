from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def create_script_pdf(json_data, output_filename="script_review.pdf"):
    doc = SimpleDocTemplate(output_filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title = json_data.get('presentation_title', 'Presentation Script')
    story.append(Paragraph(title, styles['Title']))
    story.append(Spacer(1, 12))

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
            [Paragraph("<b>Narration</b>", styles['Normal']), Paragraph("<b>Visual Cue</b>", styles['Normal'])],
            [Paragraph(narration, styles['Normal']), Paragraph(image_prompt, styles['Normal'])]
        ]
        
        t = Table(data, colWidths=[300, 150])
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
