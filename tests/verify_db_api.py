import httpx
import json

# Setup
API_URL = "http://localhost:8000"
LANGUAGES = ["hi"] # Testing with Hindi

# 1. Sample Script Data
sample_script = {
    "presentation_title": "Test Database Project",
    "slides": [
        {
            "slide_number": 1,
            "title": "Welcome Slide",
            "narration": "Hello and welcome to the database test.",
            "visual_cue": "Show a database icon"
        },
        {
            "slide_number": 2,
            "title": "CRUD Demo",
            "narration": "This is row two for testing.",
            "visual_cue": "Show code on screen"
        }
    ]
}

async def run_test():
    print("🚀 Starting CRUD Flow Test...\n")
    
    # --- STEP 1: TRANSLATE AND SAVE ---
    print("📝 Step 1: Sending translation request (Translate & Save)...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{API_URL}/translation/batch_translate",
            json={
                "json_script": sample_script,
                "languages": LANGUAGES,
                "translate_visual_cues": True
            }
        )
        
        if response.status_code != 200:
            print(f"❌ Error in translation: {response.text}")
            return
            
        data = response.json()
        project_id = data.get("project_id")
        print(f"✅ Success! Project saved with ID: {project_id}\n")
        
        # --- STEP 2: READ GRID DATA ---
        print(f"📊 Step 2: Fetching grid data for Project #{project_id}...")
        grid_response = await client.get(f"{API_URL}/translation/project_data/{project_id}")
        grid_data = grid_response.json()
        
        # Get the slide_id of the first slide for the update test
        first_row = grid_data['grid'][0]
        slide_id = first_row['slide_id']
        current_text = first_row['translations']['hi']['text']
        
        print(f"✅ Received grid with {len(grid_data['grid'])} rows.")
        print(f"   Current Hindi text for Slide 1: \"{current_text}\"\n")
        
        # --- STEP 3: UPDATE A CELL ---
        new_text = "यह एक डेटाबेस एडिट टेस्ट है।" # "This is a database edit test."
        print(f"✏️ Step 3: Updating Slide 1 Hindi text to: \"{new_text}\"")
        
        update_response = await client.post(
            f"{API_URL}/translation/update_cell",
            json={
                "slide_id": slide_id,
                "language_code": "hi",
                "text": new_text
            }
        )
        
        if update_response.status_code == 200:
            print("✅ Cell updated successfully in the DB!")
        else:
            print(f"❌ Update failed: {update_response.text}")
            return
            
        # --- STEP 4: VERIFY UPDATE ---
        print(f"\n🔍 Step 4: Verifying update from DB...")
        verify_response = await client.get(f"{API_URL}/translation/project_data/{project_id}")
        updated_grid = verify_response.json()
        updated_text = updated_grid['grid'][0]['translations']['hi']['text']
        is_edited = updated_grid['grid'][0]['translations']['hi']['is_edited']
        
        print(f"   Updated Hindi text: \"{updated_text}\"")
        print(f"   Is Edited Flag: {is_edited}")
        
        if updated_text == new_text and is_edited:
            print("\n🎉 PERSISTENCE TEST PASSED!")
        else:
            print("\n⚠️ Verification mismatch!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_test())
