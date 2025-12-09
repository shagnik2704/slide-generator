"""
Full workflow test: Evaluator → Optimizer
Tests if a sentence over 80 chars is caught and fixed.
"""
import json
from nodes.evaluator_node import evaluate_quality
from nodes.optimiser_node import optimise_script
from models.state import AgentState

# Create a test script with a sentence over 80 characters
test_script = {
    "presentation_title": "Test Tutorial",
    "module": "Test Module",
    "episode": "Test Episode 1",
    "learning_objectives": ["Understand the concept", "Apply the technique"],
    "duration": "3-4 min",
    "outline": ["Introduction", "Main Content", "Conclusion"],
    "meta_tags": ["test", "demo"],
    "prerequisites": "Basic knowledge",
    "slides": [
        {
            "title": "Welcome",
            "content": ["Welcome to tutorial"],
            "narration": "Welcome to this tutorial.",
            "image_prompt": "Welcome screen",
            "video_prompt": "",
            "is_video_slide": False
        },
        {
            "title": "Main Concept",
            "content": ["Point 1", "Point 2"],
            "narration": "This is a deliberately very long sentence that contains more than eighty characters and should definitely be caught by the evaluator as being too long for proper narration. It just keeps going and going.",
            "image_prompt": "Concept diagram",
            "video_prompt": "",
            "is_video_slide": False
        },
        {
            "title": "Summary",
            "content": ["Key point 1", "Key point 2"],
            "narration": "Remember these key points. **Practice makes perfect**. Thank you.",
            "image_prompt": "Summary slide",
            "video_prompt": "",
            "is_video_slide": False
        }
    ]
}

print("=" * 70)
print("FULL WORKFLOW TEST: EVALUATOR → OPTIMIZER")
print("=" * 70)

print("\n" + "=" * 70)
print("STEP 1: ORIGINAL SCRIPT")
print("=" * 70)
print(f"\nSlide 2 Narration (should fail - over 80 chars):")
print(f"  Length: {len(test_script['slides'][1]['narration'])} characters")
print(f"  Text: {test_script['slides'][1]['narration'][:100]}...")

print(f"\nSlide 3 Narration (has **bold**):")
print(f"  Text: {test_script['slides'][2]['narration']}")

# STEP 2: Run Evaluator
print("\n" + "=" * 70)
print("STEP 2: RUNNING EVALUATOR")
print("=" * 70)

state = {
    "json_script": test_script,
    "evaluation_iteration": 0
}

eval_result = evaluate_quality(state)

print(f"\nEvaluation Result:")
print(f"  Passed: {eval_result['evaluation_passed']}")
print(f"  Feedback: {eval_result['evaluation_feedback'][:200]}...")

# STEP 3: Run Optimizer if failed
if not eval_result['evaluation_passed']:
    print("\n" + "=" * 70)
    print("STEP 3: RUNNING OPTIMIZER TO FIX ISSUES")
    print("=" * 70)
    
    state['evaluation_feedback'] = eval_result['evaluation_feedback']
    optimizer_result = optimise_script(state)
    
    optimized_script = optimizer_result['json_script']
    
    print(f"\nOptimized Slide 2 Narration:")
    slide2_narration = optimized_script['slides'][1]['narration']
    print(f"  Text: {slide2_narration}")
    
    # Check if it has newlines
    sentences = slide2_narration.split('\n')
    print(f"  Number of lines: {len(sentences)}")
    print(f"  Max line length: {max(len(s) for s in sentences)} characters")
    
    print(f"\nOptimized Slide 3 Narration:")
    slide3_narration = optimized_script['slides'][2]['narration']
    print(f"  Text: {slide3_narration}")
    print(f"  Has ** **: {'**' in slide3_narration}")
    
    # STEP 4: Re-evaluate
    print("\n" + "=" * 70)
    print("STEP 4: RE-EVALUATING OPTIMIZED SCRIPT")
    print("=" * 70)
    
    state['json_script'] = optimized_script
    state['evaluation_iteration'] = 1
    
    final_eval = evaluate_quality(state)
    
    print(f"\nFinal Evaluation Result:")
    print(f"  Passed: {final_eval['evaluation_passed']}")
    print(f"  Feedback: {final_eval['evaluation_feedback'][:200]}")
    
    if final_eval['evaluation_passed']:
        print("\n✅ SUCCESS! Script passed after optimization!")
    else:
        print("\n⚠️  Script still has issues. May need another iteration.")
        print(f"  Full feedback: {final_eval['evaluation_feedback']}")
else:
    print("\n✅ Script passed evaluation on first try!")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
