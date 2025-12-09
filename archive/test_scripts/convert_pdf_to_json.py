"""
Script to convert sample PDF scripts to JSON format using Gemini API.
This extracts the script structure from PDFs and converts to the JSON format expected by the system.
"""
import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

def convert_pdf_to_json(pdf_path, output_json_path):
    """Convert a PDF script to JSON using Gemini's file API."""
    
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    
    print(f"📄 Uploading PDF: {pdf_path}")
    
    # Upload the PDF file
    with open(pdf_path, 'rb') as f:
        uploaded_file = client.files.upload(file=f, config={'mime_type': 'application/pdf'})
    print(f"✓ Uploaded file: {uploaded_file.name}")
    
    # Wait for file to be processed
    import time
    while uploaded_file.state == "PROCESSING":
        time.sleep(2)
        uploaded_file = client.files.get(name=uploaded_file.name)
    
    if uploaded_file.state == "FAILED":
        print(f"✗ File processing failed")
        return None
    
    print(f"✓ File ready: {uploaded_file.state}")
    
    # Create conversion prompt
    conversion_prompt = """
You are converting a Spoken Tutorial script from PDF format to JSON format.

Extract ALL the content from this PDF and convert it to this exact JSON structure:

{
  "presentation_title": "Title of the tutorial",
  "module": "Module name",
  "episode": "Episode number and title",
  "learning_objectives": ["List of learning objectives using Bloom's taxonomy verbs"],
  "duration": "Duration (e.g., 3-4 min)",
  "outline": ["List of main topics covered"],
  "meta_tags": ["Keywords for searchability"],
  "prerequisites": "Prior knowledge needed",
  "slides": [
    {
      "title": "Slide title",
      "content": ["Bullet point 1", "Bullet point 2"],
      "narration": "The exact narration text with newlines between sentences",
      "image_prompt": "Description of visual cue",
      "video_prompt": "",
      "is_video_slide": false
    }
  ]
}

CRITICAL INSTRUCTIONS:
1. Extract the EXACT narration text from the script
2. Preserve the conversational tone exactly as written
3. Keep all sentence breaks (use \\n between sentences in the narration field)
4. Extract all slides in order
5. For the "Visual Cue" column, put it in "image_prompt"
6. For the "Narration" column, put it in "narration"
7. Preserve the EXACT wording - this is a reference example

Return ONLY valid JSON, no additional text.
"""
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',  # Use latest model with file API
            contents=[uploaded_file, conversion_prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1  # Low temperature for accurate extraction
            )
        )
        
        script_json = json.loads(response.text)
        
        # Save to file
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(script_json, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved JSON to: {output_json_path}")
        print(f"✓ Extracted {len(script_json.get('slides', []))} slides")
        
        # Clean up uploaded file
        client.files.delete(name=uploaded_file.name)
        
        return script_json
        
    except Exception as e:
        print(f"✗ Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Convert the "3Cs of Prompting" PDF
    pdf_file = "sample_scripts/Spoken Tutorial – 3Cs of Prompting.pdf"
    json_file = "sample_scripts/json/3cs_prompting.json"
    
    print("=" * 60)
    print("Converting Sample PDF to JSON")
    print("=" * 60)
    
    result = convert_pdf_to_json(pdf_file, json_file)
    
    if result:
        print("\n" + "=" * 60)
        print("✓ CONVERSION SUCCESSFUL")
        print("=" * 60)
        print(f"\nPreview of first slide:")
        print(json.dumps(result['slides'][0], indent=2))
    else:
        print("\n✗ Conversion failed")
