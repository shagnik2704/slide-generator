"""
Test few-shot script generation to validate improvements.
"""
import sys
import json
from nodes.script_node import generate_script
from models.state import AgentState

def test_fewshot_script_generation():
    """Test script generation with few-shot prompting"""
    
    print("=" * 70)
    print("TESTING FEW-SHOT SCRIPT GENERATION")
    print("=" * 70)
    
    # Test outline
    test_outline = "Introduction to Neural Networks"
    
    print(f"\n📝 Generating script for: {test_outline}")
    print("-" * 70)
    
    # Generate script
    state = AgentState(outline=test_outline)
    result = generate_script(state)
    
    script = result.get('json_script', {})
    
    if not script or not script.get('slides'):
        print("\n✗ FAILED: No script generated")
        return False
    
    print(f"\n✓ Generated {len(script['slides'])} slides")
    print(f"✓ Title: {script.get('presentation_title', 'N/A')}")
    
    # Analyze narration for tone improvements
    print("\n" + "=" * 70)
    print("ANALYZING NARRATION QUALITY")
    print("=" * 70)
    
    # Collect all narrations
    narrations = []
    for slide in script['slides']:
        narration = slide.get('narration', '')
        if narration:
            narrations.append(narration)
    
    all_narration = " ".join(narrations).lower()
    
    # Check for conversational markers (good signs)
    contractions_found = []
    if "you'll" in all_narration:
        contractions_found.append("you'll")
    if "it's" in all_narration:
        contractions_found.append("it's")
    if "you're" in all_narration:
        contractions_found.append("you're")
    if "let's" in all_narration:
        contractions_found.append("let's")
    
    # Check for formal phrases (bad signs)
    formal_phrases_found = []
    if "ensure you have" in all_narration:
        formal_phrases_found.append("ensure you have")
    if "for this tutorial, you will need" in all_narration:
        formal_phrases_found.append("for this tutorial, you will need")
    if "you will achieve" in all_narration:
        formal_phrases_found.append("you will achieve")
    if "at the end of this tutorial, you will achieve" in all_narration:
        formal_phrases_found.append("at the end of this tutorial, you will achieve")
    
    print(f"\n✅ Conversational Markers Found: {len(contractions_found)}")
    if contractions_found:
        print(f"   - {', '.join(contractions_found)}")
    else:
        print("   ⚠️ No contractions found!")
    
    print(f"\n❌ Formal Phrases Found: {len(formal_phrases_found)}")
    if formal_phrases_found:
        print(f"   - {', '.join(formal_phrases_found)}")
    else:
        print("   ✅ No formal phrases - great!")
    
    # Show sample narrations
    print("\n" + "=" * 70)
    print("SAMPLE NARRATIONS (First 3 content slides)")
    print("=" * 70)
    
    for i, slide in enumerate(script['slides'][4:7], start=5):  # Skip title slides
        print(f"\nSlide {i}: {slide.get('title', 'Untitled')}")
        print(f"Narration: {slide.get('narration', 'N/A')[:150]}...")
    
    # Calculate scores
    conversational_score = len(contractions_found) * 2.5
    formal_penalty = len(formal_phrases_found) * 2
    
    tone_score = max(0, conversational_score - formal_penalty)
    
    print("\n" + "=" * 70)
    print("TONE ASSESSMENT")
    print("=" * 70)
    print(f"Conversational Score: +{conversational_score} ({len(contractions_found)} contractions)")
    print(f"Formal Penalty: -{formal_penalty} ({len(formal_phrases_found)} formal phrases)")
    print(f"\nOverall Tone Score: {tone_score}/10")
    
    if tone_score >= 7:
        print("✅ EXCELLENT - Natural conversational tone!")
    elif tone_score >= 5:
        print("⚠️ GOOD - Some improvement, but could be more conversational")
    else:
        print("❌ NEEDS WORK - Still too formal")
    
    # Save output for review
    output_file = "test_fewshot_output.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(script, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Full script saved to: {output_file}")
    
    return tone_score >= 5  # Pass if score is 5 or higher

if __name__ == "__main__":
    try:
        success = test_fewshot_script_generation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
