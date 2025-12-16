"""
Outline generation node for the slide generator agent.

This module generates structured, educational presentation outlines following
Spoken Tutorial pedagogy principles. It creates outlines optimized for hands-on,
demonstration-based learning.
"""
import os
from typing import Tuple
from dotenv import load_dotenv
from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, InternalServerError
from src.core.state import AgentState

load_dotenv()


def _create_outline_prompt(topic: str) -> str:
    """
    Creates a comprehensive prompt for generating a Spoken Tutorial outline.
    
    Args:
        topic: The topic/subject for the tutorial
        
    Returns:
        A formatted prompt string with clear instructions
    """
    return f"""You are creating a presentation outline for a Spoken Tutorial on "{topic}".

=== SPOKEN TUTORIAL PEDAGOGY RULES ===
1. DEMONSTRATION-FIRST: 75-80% of content must be hands-on demonstration, not theory
2. ACTION-ORIENTED: Use action verbs (Create, Build, Demonstrate, Show, etc.)
3. CONCRETE STEPS: Each topic should have 3-6 demonstrable, actionable steps
4. REAL EXAMPLES: Include a core example that runs throughout the tutorial
5. PROGRESSIVE: Build from simple to complex concepts
6. PRACTICAL: Focus on what learners will DO, not just what they'll learn

=== OUTLINE STRUCTURE ===
Create a markdown outline with the following sections:

# {topic} - Presentation Outline

## Overview
- Brief 2-3 sentence description of what this tutorial covers
- Target audience (who is this for?)

## Learning Objectives
List 3-6 specific, measurable objectives using action verbs:
- Use Bloom's Taxonomy verbs: Define, Explain, Identify, Apply, Create, Analyze
- Keep each objective under 80 characters
- Make them concrete and achievable

## Core Example
- Describe ONE main example/project that will be used throughout
- Should be relatable and practical (e.g., "student marksheet" for Excel, "bookstore DB" for SQL)
- This example must be used consistently across all topics

## Topics Covered
List 4-8 main topics in logical order. For each topic:
1. Topic name (clear and specific)
2. 3-6 demonstrable steps (what will the learner DO?)
3. Brief description of what will be demonstrated

Format each topic like this:
### Topic Name
**Prerequisites:**
- What should learners know before this topic? (e.g., previous topics, specific skills)
- Any required software/tools for this topic?
- Reference to previous tutorials if applicable

**Steps:**
1. Step 1 (action-oriented)
2. Step 2 (action-oriented)
3. Step 3 (action-oriented)

**What we'll demonstrate:** Brief description

## Key Takeaways
- 3-5 main points learners will remember
- Practical applications

=== REQUIREMENTS ===
- Total topics: 4-8 (not too many, not too few)
- Each topic must have demonstrable steps (not just theory)
- Each topic MUST include prerequisites (what learners need before starting this topic)
- Prerequisites should build progressively (later topics require earlier ones)
- Use clear, simple language
- Avoid jargon unless necessary (and explain it)
- Make it practical and hands-on
- Ensure logical flow from one topic to the next

=== OUTPUT FORMAT ===
Return ONLY the markdown outline. Do not include explanations or meta-commentary.
Start directly with the "# {topic} - Presentation Outline" heading.

Now generate the outline for: {topic}
"""


def _validate_outline(outline: str, topic: str) -> Tuple[bool, list[str]]:
    """
    Validates the generated outline for basic quality checks.
    
    Args:
        outline: The generated outline text
        topic: The original topic
        
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    # Check if outline is too short
    if len(outline.strip()) < 200:
        issues.append("Outline is too short (less than 200 characters)")
    
    # Check if topic is mentioned
    if topic.lower() not in outline.lower():
        issues.append(f"Topic '{topic}' not clearly mentioned in outline")
    
    # Check for required sections
    required_sections = ["Learning Objectives", "Topics"]
    outline_lower = outline.lower()
    for section in required_sections:
        if section.lower() not in outline_lower:
            issues.append(f"Missing required section: {section}")
    
    # Check if prerequisites are mentioned (should be per topic, not general)
    if "prerequisite" in outline_lower:
        # Good - prerequisites are mentioned
        pass
    else:
        issues.append("Prerequisites should be included for each topic")
    
    # Check if outline has structure (headings)
    if outline.count("#") < 3:
        issues.append("Outline lacks proper structure (not enough headings)")
    
    is_valid = len(issues) == 0
    return is_valid, issues


def _format_outline(outline: str, topic: str) -> str:
    """
    Formats and enhances the generated outline with proper structure.
    
    Args:
        outline: The raw outline from LLM
        topic: The original topic
        
    Returns:
        Formatted outline string
    """
    # Clean up the outline
    outline = outline.strip()
    
    # Remove any code fences if present
    if outline.startswith("```"):
        # Extract content between code fences
        lines = outline.split("\n")
        start_idx = 0
        end_idx = len(lines)
        
        for i, line in enumerate(lines):
            if line.strip().startswith("```"):
                if start_idx == 0:
                    start_idx = i + 1
                else:
                    end_idx = i
                    break
        
        outline = "\n".join(lines[start_idx:end_idx]).strip()
    
    # Ensure it starts with a proper heading
    if not outline.startswith("#"):
        outline = f"# {topic} - Presentation Outline\n\n{outline}"
    
    return outline


@retry(
    retry=retry_if_exception_type((ResourceExhausted, ServiceUnavailable, InternalServerError)),
    wait=wait_exponential(multiplier=4, min=4, max=60),
    stop=stop_after_attempt(5)
)
def generate_outline(state: AgentState):
    """
    Generates a structured, educational presentation outline following Spoken Tutorial pedagogy.
    
    This function:
    1. Creates a comprehensive prompt based on the topic
    2. Calls the LLM to generate the outline
    3. Validates the output
    4. Formats and returns the final outline
    
    Args:
        state: AgentState containing 'topic' or 'outline' field
        
    Returns:
        Dictionary with 'outline' key containing the generated outline
    """
    print("🔧 Generating presentation outline...")
    
    # Extract topic from state
    topic = state.get('topic') or state.get('outline', '')
    
    if not topic:
        print("⚠️ No topic provided, returning empty outline")
        return {"outline": "# Presentation Outline\n\nNo topic provided."}
    
    print(f"📝 Topic: {topic}")
    
    # Initialize client
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    
    # Create comprehensive prompt
    prompt = _create_outline_prompt(topic)
    
    try:
        print("🤖 Calling LLM to generate outline...")
        
        # Generate outline using Gemini 2.5 Flash
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.9,
                "max_output_tokens": 2048,
            }
        )
        
        # Extract and format outline
        raw_outline = response.text
        formatted_outline = _format_outline(raw_outline, topic)
        
        # Validate outline
        is_valid, issues = _validate_outline(formatted_outline, topic)
        
        if not is_valid:
            print(f"⚠️ Outline validation found issues: {issues}")
            print("   Proceeding anyway, but consider reviewing the output")
        else:
            print("✓ Outline validation passed")
        
        print("✓ Outline generated successfully")
        return {"outline": formatted_outline}
        
    except (ResourceExhausted, ServiceUnavailable, InternalServerError) as e:
        # These exceptions are retried by the decorator
        print(f"❌ API error (will retry): {e}")
        raise
        
    except Exception as e:
        print(f"❌ Outline generation failed: {e}")
        print("🔄 Attempting fallback generation...")
        
        # Fallback: Simpler prompt
        fallback_prompt = f"""Create a presentation outline for "{topic}".

Include:
1. Learning objectives (3-6 items)
2. Main topics (4-8 topics) - each topic MUST include:
   - Prerequisites (what learners need before this topic)
   - Demonstrable steps (3-6 action-oriented steps)
3. Core example to use throughout

IMPORTANT: Include prerequisites for EACH topic, not as a general section.
Prerequisites should build progressively (later topics require earlier ones).

Format as markdown with clear headings."""
        
        try:
            fallback_response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=fallback_prompt,
            )
            
            fallback_outline = _format_outline(fallback_response.text, topic)
            print("✓ Fallback outline generated")
            return {"outline": fallback_outline}
            
        except Exception as fallback_error:
            print(f"❌ Fallback generation also failed: {fallback_error}")
            # Return a minimal outline structure
            minimal_outline = f"""# {topic} - Presentation Outline

## Overview
This tutorial covers {topic}.

## Learning Objectives
- Understand the basics of {topic}
- Apply {topic} concepts in practice
- Create practical examples using {topic}

## Topics Covered

### Introduction to {topic}
**Prerequisites:**
- Basic computer skills
- Familiarity with related concepts

**Steps:**
1. Introduction step 1
2. Introduction step 2
3. Introduction step 3

### Core concepts
**Prerequisites:**
- Completion of "Introduction to {topic}" topic above

**Steps:**
1. Core concept step 1
2. Core concept step 2

### Practical applications
**Prerequisites:**
- Completion of "Core concepts" topic above

**Steps:**
1. Application step 1
2. Application step 2

### Advanced features
**Prerequisites:**
- Completion of "Practical applications" topic above

**Steps:**
1. Advanced step 1
2. Advanced step 2

## Core Example
A practical example demonstrating {topic} concepts.
"""
            return {"outline": minimal_outline}
    