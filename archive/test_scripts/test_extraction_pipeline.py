"""
Test script for the new content extractor + script generator pipeline.
Tests that analogies and examples from the outline are properly extracted
and included in the generated script.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nodes.outline_distiller_node import extract_content
from nodes.script_node import generate_script

# Sample outline from user (Submodule 1.1)
TEST_OUTLINE = """
1.1: The Big Picture: AI, Machine Learning & Deep Learning

Think of AI, Machine Learning (ML), and Deep Learning (DL) as nested Russian dolls. AI is the biggest doll, ML is the next one inside, and DL is the smallest, most powerful one within ML.

What is Artificial Intelligence (AI)? 
At its core, Artificial Intelligence is a broad field of computer science focused on a simple goal: building smart machines capable of performing tasks that typically require human intelligence. This could be anything from understanding language and recognizing images to solving complex problems.
The idea isn't new; it has been a dream of scientists since the 1950s, starting with pioneers who asked, "Can machines think?" AI is the entire universe of making computers intelligent.

What is Machine Learning (ML)? 
Machine Learning is a type of AI. Instead of giving a computer a detailed list of rules to follow (traditional programming), we give it a lot of data and let it learn the rules for itself. It's all about recognizing patterns from examples.

Let's use an analogy:
Traditional Programming (Rules First): Imagine you want to program a computer to identify a cat. You'd have to write specific rules like: "IF it has pointy ears, AND it has whiskers, AND it has fur, AND it has four legs, THEN it is a cat." This is fragile—what if the cat's ears are folded?
Machine Learning (Data First): Instead, you show the computer thousands of pictures labeled "cat." The ML model analyzes all these images and learns the common patterns and features that define a cat on its own. It builds its own internal "rules" that are much more flexible and accurate.

What is Deep Learning? 
Deep Learning is a super-powered, more advanced version of Machine Learning. It uses a structure called a neural network, which is inspired by the human brain. These networks have many layers of "neurons" stacked on top of each other—and because there are many layers, we call it "deep."
This deep structure allows it to learn much more complex patterns from data than traditional ML. Deep learning is the magic behind self-driving cars recognizing pedestrians, voice assistants understanding your commands, and the generative AI we'll discuss next.
"""

def test_extraction():
    """Test that the extractor properly identifies analogies and examples."""
    print("\n" + "="*60)
    print("STEP 1: Testing Content Extraction")
    print("="*60)
    
    state = {"outline": TEST_OUTLINE}
    result = extract_content(state)
    
    extracted = result.get("extracted_content", {})
    
    print(f"\nExtracted Content Summary:")
    print(f"  Analogies: {len(extracted.get('analogies', []))}")
    print(f"  Examples: {len(extracted.get('examples', []))}")
    print(f"  Key Terms: {len(extracted.get('key_terms', []))}")
    print(f"  Learning Objectives: {len(extracted.get('learning_objectives', []))}")
    print(f"  Hook Ideas: {len(extracted.get('hook_ideas', []))}")
    
    # Check for expected analogies
    analogies = extracted.get('analogies', [])
    analogy_names = [a.get('name', '').lower() for a in analogies]
    
    if any('russian' in name or 'doll' in name for name in analogy_names):
        print("  ✅ Found 'Russian Dolls' analogy")
    else:
        print("  ❌ MISSING 'Russian Dolls' analogy!")
    
    if any('cat' in name for name in analogy_names):
        print("  ✅ Found 'Cat recognition' analogy")
    else:
        print("  ❌ MISSING 'Cat recognition' analogy!")
    
    return extracted

def test_script_generation(extracted_content):
    """Test that the script generator includes the mandatory content."""
    print("\n" + "="*60)
    print("STEP 2: Testing Script Generation with Mandatory Content")
    print("="*60)
    
    state = {
        "outline": TEST_OUTLINE,
        "extracted_content": extracted_content
    }
    
    result = generate_script(state)
    script = result.get("json_script", {})
    
    print(f"\nGenerated Script Summary:")
    print(f"  Title: {script.get('presentation_title', 'N/A')}")
    print(f"  Slides: {len(script.get('slides', []))}")
    
    # Check if analogies appear in the narration
    all_narration = " ".join([s.get('narration', '') for s in script.get('slides', [])])
    all_narration_lower = all_narration.lower()
    
    print("\n  Checking for mandatory content in narration:")
    
    if 'russian' in all_narration_lower or 'doll' in all_narration_lower:
        print("  ✅ 'Russian Dolls' analogy appears in script!")
    else:
        print("  ❌ 'Russian Dolls' analogy NOT found in script!")
    
    if 'cat' in all_narration_lower:
        print("  ✅ 'Cat' example appears in script!")
    else:
        print("  ❌ 'Cat' example NOT found in script!")
    
    return script

if __name__ == "__main__":
    print("Testing Content Extraction + Script Generation Pipeline")
    print("="*60)
    
    # Step 1: Extract content
    extracted = test_extraction()
    
    # Step 2: Generate script with extracted content
    script = test_script_generation(extracted)
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
