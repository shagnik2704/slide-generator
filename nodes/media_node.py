"""
Media generation nodes (images and audio).
"""
import os
import time
import random
import wave
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from models.state import AgentState

load_dotenv()

@retry(
    retry=retry_if_exception_type((ResourceExhausted, ServiceUnavailable)),
    wait=wait_exponential(multiplier=4, min=4, max=60),
    stop=stop_after_attempt(5)
)
def generate_images(state: AgentState):
    """Generates images."""
    print("Generating images...")
    json_script = state.get('json_script')
    slides = json_script['slides']
    target_audience = state.get('target_audience', 'general')
    
    if os.path.exists("generated_images"):
        shutil.rmtree("generated_images")
    os.makedirs("generated_images")
    
    # Audience-specific image style prefixes
    audience_style_prefix = {
        'kids': "Hand-drawn crayon sketch, colorful, playful, child-friendly illustration,",
        'students': "Hand-drawn pencil sketch, educational diagram, clear and informative,",
        'professionals': "Minimalist architectural sketch, clean lines, professional, blueprint style,",
        'general': "Artistic ink sketch, hand-drawn illustration, high quality,"
    }
    
    style_prefix = audience_style_prefix.get(target_audience, audience_style_prefix['general'])
    
    api_key = os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
        
    for i, slide in enumerate(slides):
        prompt = slide.get('image_prompt')
        if prompt:
            # Check if this is a video slide
            if slide.get('is_video_slide'):
                try:
                    # Use dedicated video prompt if available, otherwise fallback to image prompt
                    raw_video_prompt = slide.get('video_prompt') or prompt
                    print(f"Generating VIDEO for slide {i+1} (Audience: {target_audience}) using Veo...")
                    video_prompt = f"{style_prefix} {raw_video_prompt}. Cinematic, smooth motion, high quality."
                    
                    # Use generate_videos instead of generate_content
                    operation = client.models.generate_videos(
                        model='veo-3.1-generate-preview',
                        prompt=video_prompt,
                    )
                    print(f"Operation started: {operation.name}")
                    
                    # Poll for completion
                    while True:
                        time.sleep(5)
                        print(".", end="", flush=True)
                        op_status = client.operations.get(operation)
                        if op_status.done:
                            print("\nOperation done!")
                            if op_status.result:
                                video_uri = op_status.result.generated_videos[0].video.uri
                                print(f"Downloading video from {video_uri}...")
                                
                                # Download video
                                import requests
                                headers = {"x-goog-api-key": api_key}
                                vid_response = requests.get(video_uri, headers=headers)
                                
                                if vid_response.status_code == 200:
                                    video_path = f"generated_images/slide_{i}.mp4"
                                    with open(video_path, "wb") as f:
                                        f.write(vid_response.content)
                                    slide['image_path'] = os.path.abspath(video_path)
                                    print(f"✓ Video generated for slide {i+1}")
                                else:
                                    raise Exception(f"Failed to download video: {vid_response.status_code}")
                            else:
                                raise Exception("Operation completed but no result returned")
                            break
                    
                except Exception as e:
                    print(f"Failed to generate video for slide {i+1}: {e}")
                    # Fallback to image generation if video fails
                    print("Falling back to image generation...")
                    try:
                        prompt = f"{style_prefix} {prompt}"
                        response = client.models.generate_content(
                            model='gemini-2.5-flash-image',
                            contents=prompt,
                        config=types.GenerateContentConfig(
                            response_modality=["IMAGE"],
                            image_config=types.ImageConfig(aspect_ratio="1:1"),
                        ),
                        )
                        if response.parts:
                            for part in response.parts:
                                if part.inline_data:
                                    try:
                                        generated_image = part.as_image()
                                        image_path = f"generated_images/slide_{i}.png"
                                        generated_image.save(image_path)
                                        slide['image_path'] = os.path.abspath(image_path)
                                        print(f"✓ Fallback image generated for slide {i+1}")
                                        break
                                    except Exception as e_img:
                                        print(f"Error saving fallback image for slide {i+1}: {e_img}")
                        else:
                            print(f"No image parts returned for fallback slide {i+1}")
                    except Exception as e2:
                        print(f"Failed to generate fallback image for slide {i+1}: {e2}")

            else:
                # Standard Image Generation
                prompt = f"{style_prefix} {prompt}"
                try:
                    print(f"Generating image for slide {i+1} (Audience: {target_audience})...")
                    response = client.models.generate_content(
                        model='gemini-2.5-flash-image',
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_modalities=["IMAGE"],
                            image_config=types.ImageConfig(aspect_ratio="1:1"),
                        ),
                    )
                    if response.parts:
                        for part in response.parts:
                            if part.inline_data:
                                try:
                                    generated_image = part.as_image()
                                    image_path = f"generated_images/slide_{i}.png"
                                    generated_image.save(image_path)
                                    slide['image_path'] = os.path.abspath(image_path)
                                    print(f"✓ Image generated for slide {i+1}")
                                    break
                                except Exception as e_img:
                                    print(f"Error saving image for slide {i+1}: {e_img}")
                    else:
                         print(f"No image parts returned for slide {i+1}")
                except Exception as e:
                    print(f"Failed to generate image for slide {i+1}: {e}")
                
    return {"json_script": json_script}
@retry(
    retry=retry_if_exception_type((ResourceExhausted, ServiceUnavailable)),
    wait=wait_exponential(multiplier=4, min=4, max=60),
    stop=stop_after_attempt(5)
)
async def generate_audio(state: AgentState):
    """Generates audio narration for each slide using Gemini 2.5 Flash."""
    print("Generating audio narration with Gemini 2.5 Flash...")
    json_script = state['json_script']
    slides = json_script['slides']
    audio_map = {}
    
    if not os.path.exists("audio"):
        os.makedirs("audio")
        
    api_key = os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    
    target_audience = state.get('target_audience', 'general')
    
    # Audience-specific voice prompts
    tts_prompts = {
        'kids': "Read aloud in a fun, energetic, and playful tone, like a storyteller for children.",
        'students': "Read aloud in a clear, educational, and engaging tone, like a friendly teacher.",
        'professionals': "Read aloud in a professional, confident, and concise tone, suitable for a business presentation.",
        'general': "Read aloud in a warm, welcoming, and conversational tone."
    }
    
    voice_instruction = tts_prompts.get(target_audience, tts_prompts['general'])
    
    # Audience-specific voices
    voice_mapping = {
        'kids': "Tevel",
        'students': "Kore",
        'professionals': "Ophir",
        'general': "Kore"
    }
    
    selected_voice = voice_mapping.get(target_audience, "Kore")
    
    for i, slide in enumerate(slides):
        narrations = slide.get('narration', [])
        if isinstance(narrations, str): narrations = [narrations]
        if not narrations: narrations = [slide.get('title', 'Slide')]
        
        # Merge all narration parts for this slide into one text
        full_narration = " ".join(narrations)
        
        # Clean markdown formatting
        full_narration = full_narration.replace('**', '').replace('__', '').replace('*', '').replace('_', '').replace('#', '')
        
        audio_path = f"audio/slide_{i}.wav"
        
        # Use Gemini 2.5 Flash TTS
        try:
            # Rate limit handling: 10 RPM = 1 request every 6 seconds.
            # We wait 7 seconds to be safe.
            await asyncio.sleep(7)
            
            print(f"Generating audio for slide {i} (Audience: {target_audience}, Voice: {selected_voice})...")
            response = client.models.generate_content(
                model='gemini-2.5-flash-preview-tts',
                contents=f"{voice_instruction} {full_narration}",
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=selected_voice
                            )
                        )
                    )
                )
            )
            
            # Save audio
            for part in response.parts:
                if part.inline_data:
                    wave_file(audio_path, part.inline_data.data)
                    audio_map[i] = audio_path  # Store single audio path per slide
                    print(f"✓ Generated audio for slide {i}")
                    break
                    
        except Exception as e:
            print(f"Failed audio for slide {i}: {e}")
    
    return {"audio_map": audio_map}
