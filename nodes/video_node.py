"""
Video creation node.
"""
import os
import fitz
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, VideoFileClip, CompositeVideoClip, vfx
from models.state import AgentState

def create_video(state: AgentState):
    print("Creating video...")
    pdf_path = state['pdf_path']
    audio_map = state['audio_map']
    
    if not pdf_path or not audio_map: return {"video_path": None}
        
    doc = fitz.open(pdf_path)
    clips = []
    current_page_index = 0
    slides = state['json_script']['slides']
    
    for i, slide in enumerate(slides):
        audio_path = audio_map.get(i)  # Now returns a single path string, not a list
        if not audio_path:
            print(f"No audio for slide {i}, skipping...")
            continue
        
        # Validate that the audio file actually exists
        if not os.path.exists(audio_path):
            print(f"Audio file not found for slide {i}: {audio_path}, skipping...")
            continue
        
        # Count how many pages this slide has (title + bullets)
        content_items = slide.get('content', [])
        num_pages_for_slide = len(content_items) + 1  # +1 for title-only page
        
        # Load the audio clip to get total duration
        try:
            audio_clip = AudioFileClip(audio_path)
            if audio_clip is None or audio_clip.reader is None:
                print(f"Failed to load audio for slide {i}: Invalid audio file")
                continue
            total_audio_duration = audio_clip.duration
        except Exception as e:
            print(f"Error loading audio for slide {i}: {e}")
            continue
        
        # Calculate duration per page to distribute audio evenly
        duration_per_page = total_audio_duration / num_pages_for_slide
        
        print(f"Slide {i}: {num_pages_for_slide} pages, {total_audio_duration:.2f}s audio, {duration_per_page:.2f}s per page")
        
        # Create video clips for each page of this slide
        # Prepare master video background if applicable
        master_video_bg = None
        if slide.get('is_video_slide') and slide.get('image_path') and slide['image_path'].endswith('.mp4'):
            try:
                # Load the video file
                raw_video = VideoFileClip(slide['image_path'])
                # Loop it to cover the total audio duration of the slide
                # We use a large number of loops or duration to ensure coverage
                master_video_bg = raw_video.with_effects([vfx.Loop(duration=total_audio_duration)])
                print(f"Loaded video background for slide {i}")
            except Exception as e:
                print(f"Failed to load video background for slide {i}: {e}")

        for page_offset in range(num_pages_for_slide):
            page_index = current_page_index + page_offset
            if page_index >= len(doc):
                print(f"Warning: Page index {page_index} out of bounds")
                break
            
            page = doc.load_page(page_index)
            pix = page.get_pixmap(dpi=300)
            img_path = f"temp_slide_{i}_page_{page_offset}.png"
            pix.save(img_path)
            
            # Extract the segment of audio for this page
            start_time = page_offset * duration_per_page
            end_time = (page_offset + 1) * duration_per_page
            
            try:
                audio_segment = audio_clip.subclipped(start_time, end_time)
                
                # Base clip from PDF page
                base_clip = ImageClip(img_path).with_duration(duration_per_page)
                
                # Composite video background if available
                if master_video_bg:
                    try:
                        # Extract segment from the looped master video
                        video_segment = master_video_bg.subclipped(start_time, end_time)
                        
                        # Resize and position
                        # We assume the layout puts the image on the right half (50% width)
                        # We'll resize the video to fit half the width of the PDF page
                        # pix.width is the full width
                        target_width = pix.width / 2
                        
                        # Resize video (keeping aspect ratio? or fill?)
                        # Let's resize to target width
                        video_segment = video_segment.resized(width=target_width)
                        
                        # Position on the right
                        video_segment = video_segment.with_position(("right", "center"))
                        
                        # Composite: Base PDF (bottom) + Video (top, right)
                        # Note: PDF page has white background on right, so video covers it.
                        video_clip = CompositeVideoClip([base_clip, video_segment])
                        video_clip = video_clip.with_duration(duration_per_page)
                        
                    except Exception as e:
                        print(f"Failed to composite video for slide {i} page {page_offset}: {e}")
                        video_clip = base_clip # Fallback
                else:
                    video_clip = base_clip

                video_clip = video_clip.with_audio(audio_segment)
                clips.append(video_clip)
            except Exception as e:
                print(f"Error creating video clip for slide {i}, page {page_offset}: {e}")
                # Create clip without audio as fallback
                video_clip = ImageClip(img_path).with_duration(duration_per_page)
                clips.append(video_clip)
        
        current_page_index += num_pages_for_slide
        # Don't close audio_clip here - the subclipped segments still need it!
        # The clips will be cleaned up automatically after video writing
            
    final_video = concatenate_videoclips(clips)
    video_path = "presentation.mp4"
    final_video.write_videofile(video_path, fps=24, codec='libx264', audio_codec='aac')
    
    # Cleanup
    for f in glob.glob("temp_slide_*.png"): os.remove(f)
    
    return {"video_path": os.path.abspath(video_path)}
