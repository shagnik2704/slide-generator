from agent import graph

def run_trial():
    print("--- Phase 1: Generating Script ---")
    initial_state = {"topic": "Introduction to Neural Networks", "mode": "script_only"}
    result = graph.invoke(initial_state)
    
    if result.get("script_pdf_path"):
        print(f"Script PDF generated at: {result['script_pdf_path']}")
        
        # Phase 2: Generate Slides PDF
        print("\n--- Phase 2: Generating Slides PDF ---")
        phase2_state = {
            "json_script": result['json_script'], 
            "mode": "slides_only"
        }
        slides_result = graph.invoke(phase2_state)
        print(f"DEBUG: slides_result keys: {slides_result.keys()}")
        
        if slides_result.get("pdf_path"):
            print(f"Slides PDF generated at: {slides_result['pdf_path']}")
            
            # Phase 3: Generate Video
            print("\n--- Phase 3: Generating Video ---")
            phase3_state = {
                "json_script": result['json_script'],
                "pdf_path": slides_result['pdf_path'],
                "mode": "video_production"
            }
            final_result = graph.invoke(phase3_state)
            
            if final_result.get("video_path"):
                print(f"Final Video available at: {final_result['video_path']}")
        else:
            print("Slides generation failed.")
    else:
        print("Script generation failed.")

if __name__ == "__main__":
    run_trial()
