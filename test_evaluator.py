"""
Test script to debug the evaluator JSON parsing issue.
"""
import os
from dotenv import load_dotenv
from nodes.evaluator_node import evaluate_quality

load_dotenv()

# Minimal test script
test_script = {
    "presentation_title": "Test Presentation",
    "module": "Test Module",
    "episode": "Episode 1",
    "learning_objectives": ["Understand testing", "Learn debugging"],
    "duration": "3-4 min",
    "outline": ["Introduction", "Main Content", "Conclusion"],
    "meta_tags": ["testing", "debugging"],
    "prerequisites": "Basic knowledge",
    "slides": [
        {
            "title": "Title Slide",
            "content": ["Welcome to the presentation"],
            "narration": ["Hello and welcome.", "This is a test."],
            "image_prompt": "A welcoming scene",
            "video_prompt": "",
            "is_video_slide": False
        },
        {
            "title": "Learning Objectives",
            "content": ["Objective 1", "Objective 2"],
            "narration": ["By the end of this tutorial, you will be able to...", "Understand testing.", "Learn debugging."],
            "image_prompt": "Learning objectives displayed",
            "video_prompt": "",
            "is_video_slide": False
        }
    ]
}

# Test state
test_state = {
    "json_script": test_script,
    "evaluation_iteration": 0
}

print("=" * 60)
print("TESTING EVALUATOR WITH SAMPLE SCRIPT")
print("=" * 60)

result = evaluate_quality(test_state)

print("\n" + "=" * 60)
print("EVALUATION RESULT:")
print("=" * 60)
print(f"Passed: {result.get('evaluation_passed')}")
print(f"Feedback: {result.get('evaluation_feedback')}")
print(f"Iteration: {result.get('evaluation_iteration')}")
print("=" * 60)
