import os
import shutil

def cleanup():
    files_to_remove = [
        "output.aux", "output.log", "output.out", "output.pdf", "output.tex", "output.snm", "output.toc", "output.nav",
        "presentation.mp4", "script_review.pdf", "test_video.mp4",
        "test_nested.json", "test_output.tex"
    ]
    
    dirs_to_remove = [
        "audio", "images", "generated_images", "__pycache__"
    ]
    
    print("Cleaning up project directory...")
    
    for file in files_to_remove:
        if os.path.exists(file):
            try:
                os.remove(file)
                print(f"Removed file: {file}")
            except Exception as e:
                print(f"Error removing {file}: {e}")
                
    for directory in dirs_to_remove:
        if os.path.exists(directory):
            try:
                shutil.rmtree(directory)
                print(f"Removed directory: {directory}")
            except Exception as e:
                print(f"Error removing {directory}: {e}")
                
    print("Cleanup complete.")

if __name__ == "__main__":
    cleanup()
