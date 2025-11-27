from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
import os

def test_create_video():
    img_path = "generated_images/slide_0.png"
    aud_path = "audio/slide_0.mp3"
    
    if not os.path.exists(img_path) or not os.path.exists(aud_path):
        print("Missing test files.")
        return

    print(f"Testing with {img_path} and {aud_path}")
    
    audio_clip = AudioFileClip(aud_path)
    image_clip = ImageClip(img_path).with_duration(audio_clip.duration)
    image_clip = image_clip.with_audio(audio_clip)
    
    video_path = "test_video.mp4"
    image_clip.write_videofile(video_path, fps=24, audio_codec='aac')
    print(f"Video created at {video_path}")

if __name__ == "__main__":
    test_create_video()
