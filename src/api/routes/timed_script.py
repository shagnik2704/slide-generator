"""Timed Script route - Generate sentence-level timestamps from audio."""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Body
from pathlib import Path
import tempfile
import shutil

from src.api.auth import get_current_user, TokenData
from src.services.timed_script_service import generate_timed_script

router = APIRouter(prefix="/timed-script", tags=["timed-script"])


@router.post("/generate")
async def generate_timed_script_endpoint(
    audio: UploadFile = File(...),
    language: str = None,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Generate a timed script from an uploaded audio file.
    
    Returns sentence-level timestamps with time ranges.
    Language is auto-detected by default.
    
    Args:
        audio: Audio file (WAV, MP3, etc.)
        language: Language code (optional, auto-detect if not provided)
        
    Returns:
        {
            "success": true,
            "audio_file": "intro.wav",
            "total_duration": "04:05",
            "total_sentences": 59,
            "sentences": [
                {
                    "sentence_number": 1,
                    "text": "...",
                    "time_range": "00:00 - 00:07",
                    "start_seconds": 0.0,
                    "end_seconds": 7.0
                },
                ...
            ]
        }
    """
    # Validate file type
    allowed_extensions = {'.wav', '.mp3', '.m4a', '.ogg', '.flac', '.webm'}
    file_ext = Path(audio.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Save uploaded file temporarily
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            shutil.copyfileobj(audio.file, tmp_file)
            tmp_path = tmp_file.name
        
        # Generate timed script (language=None for auto-detect)
        result = generate_timed_script(tmp_path, language=language)
        
        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to generate timed script"))
        
        # Update audio_file to show original filename
        result["audio_file"] = audio.filename
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean up on error
        if 'tmp_path' in locals():
            Path(tmp_path).unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download-docx")
async def download_timed_script_docx(
    data: dict = Body(...),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Generate a DOCX file from timed script results.
    
    Args:
        data: The result from /generate endpoint containing sentences
        
    Returns:
        DOCX file download
    """
    from fastapi.responses import StreamingResponse
    from docx import Document
    from docx.shared import Inches, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    import io
    
    sentences = data.get("sentences", [])
    audio_file = data.get("audio_file", "audio")
    total_duration = data.get("total_duration", "00:00")
    
    if not sentences:
        raise HTTPException(status_code=400, detail="No sentences provided")
    
    # Create document
    doc = Document()
    
    # Title
    title = doc.add_heading("Timed Script", level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Metadata
    doc.add_paragraph(f"Audio File: {audio_file}")
    doc.add_paragraph(f"Total Duration: {total_duration}")
    doc.add_paragraph(f"Total Sentences: {len(sentences)}")
    doc.add_paragraph()
    
    # Create table
    table = doc.add_table(rows=1, cols=2)
    table.style = 'Table Grid'
    
    # Header row
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Time Range"
    hdr_cells[1].text = "Text"
    
    # Make header bold
    for cell in hdr_cells:
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True
    
    # Add data rows
    for sentence in sentences:
        row_cells = table.add_row().cells
        row_cells[0].text = sentence.get("time_range", "")
        row_cells[1].text = sentence.get("text", "")
    
    # Set column widths and add cell padding
    from docx.oxml.ns import nsdecls
    from docx.oxml import parse_xml
    
    for row in table.rows:
        row.cells[0].width = Inches(1.5)
        row.cells[1].width = Inches(5.0)
        
        # Add padding to each cell
        for cell in row.cells:
            # Set cell margins (padding) - values in twips (1/20 of a point)
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            tcMar = parse_xml(
                f'<w:tcMar {nsdecls("w")}>'
                '<w:top w:w="200" w:type="dxa"/>'
                '<w:left w:w="200" w:type="dxa"/>'
                '<w:bottom w:w="200" w:type="dxa"/>'
                '<w:right w:w="200" w:type="dxa"/>'
                '</w:tcMar>'
            )
            tcPr.append(tcMar)
    
    # Save to bytes
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    # Generate filename
    base_name = Path(audio_file).stem if audio_file else "timed_script"
    filename = f"{base_name}_timed_script.docx"
    
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

