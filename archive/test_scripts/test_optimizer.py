"""
Test script to verify optimizer is working correctly.
"""
import json
from nodes.optimiser_node import optimise_script
from models.state import AgentState

# Sample script with known issues
test_script = {
    "presentation_title": "Test Tutorial",
    "module": "Test Module",
    "episode": "Test Episode",
    "learning_objectives": ["Test objective"],
    "duration": "3-4 min",
    "outline": ["Topic 1", "Topic 2"],
    "meta_tags": ["test"],
    "prerequisites": "None",
    "slides": [
        {
            "title": "Test Slide 1",
            "content": ["Point 1", "Point 2"],
            "narration": "This is a very long sentence that definitely exceeds eighty characters and should be flagged by the evaluator. Another sentence here.",
            "image_prompt": "Test image",
            "video_prompt": "",
            "is_video_slide": False
        },
        {
            "title": "Test Slide 2",
            "content": ["Point 1"],
            "narration": "This sentence uses **bold text** that should be converted properly. And has incomplete",
            "image_prompt": "Test image 2",
            "video_prompt": "",
            "is_video_slide": False
        }
    ]
}

# Test feedback - similar to what evaluator gives
test_feedback = """Slide 1 narration has sentences > 80 characters.
Slide 1 narration does not start each new sentence on a new line.
Slide 2 narration has incomplete sentences: 'And has incomplete'.
Slide 2 contains markdown bold formatting (**bold text**) which needs to be removed."""

print("=" * 60)
print("ORIGINAL SCRIPT (with issues):")
print("=" * 60)
print(json.dumps(test_script, indent=2))

print("\n" + "=" * 60)
print("FEEDBACK TO BE APPLIED:")
print("=" * 60)
print(test_feedback)

# Create test state
test_state = {
    "json_script": test_script,
    "evaluation_feedback": test_feedback
}

print("\n" + "=" * 60)
print("CALLING OPTIMIZER...")
print("=" * 60)

# Run optimizer
result = optimise_script(test_state)

print("\n" + "=" * 60)
print("OPTIMIZED SCRIPT:")
print("=" * 60)
print(json.dumps(result.get('json_script'), indent=2))

# Check if issues were fixed
optimized = result.get('json_script', {})
if optimized.get('slides'):
    print("\n" + "=" * 60)
    print("ANALYSIS OF FIXES:")
    print("=" * 60)
    
    slide1_narration = optimized['slides'][0]['narration']
    slide2_narration = optimized['slides'][1]['narration']
    
    has_newlines = '\n' in slide1_narration
    has_bold_markers = '**' in slide2_narration
    
    print(f"\nSlide 1 Narration:")
    print(f"  Original: {test_script['slides'][0]['narration']}")
    print(f"  Optimized: {slide1_narration}")
    print(f"  Has newlines: {has_newlines}")
    
    print(f"\nSlide 2 Narration:")
    print(f"  Original: {test_script['slides'][1]['narration']}")
    print(f"  Optimized: {slide2_narration}")
    print(f"  Has ** **: {has_bold_markers}")
    print(f"  Fixed incomplete: {'incomplete' not in slide2_narration or 'complete sentence' in slide2_narration.lower()}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
