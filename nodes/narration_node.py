"""
Narration expansion node for the 4-node pipeline.
Stage 2: Expands slide skeleton into full narration.
"""
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from models.state import AgentState, NarrationScript
import json

load_dotenv()


def expand_narration(state: AgentState):
    """
    Stage 2: Expand skeleton into full narration per slide.
    
    Input: StructuredOutline (from Stage 1)
    Output: NarrationScript with full narration for each slide
    """
    print("📝 Stage 2: Expanding narration...")
    structured_outline = state.get('structured_outline', {})
    
    if not structured_outline or not structured_outline.get('slides'):
        print("⚠️ No structured outline provided")
        return {"narration_script": {}}
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    structured_llm = llm.with_structured_output(NarrationScript)
    
    prompt = f"""You are expanding a slide skeleton into FULL NARRATION for a Spoken Tutorial.

=== INPUT: STRUCTURED OUTLINE ===
{json.dumps(structured_outline, indent=2)}

=== WRITING STYLE ===
- Write like you're SPEAKING to a learner, not reading bullet points
- Natural, conversational flow - sentences should connect smoothly
- Simple Indian English (easy to translate)
- Each sentence on a NEW LINE (use \\n) for TTS
- Sentences should be ≤ 80 characters

=== CONCISENESS RULES (IMPORTANT) ===

1. CUT FILLER PHRASES
   Remove these unnecessary starters:
   - "So," / "Now," / "Well,"
   - "So, what exactly is..." → "What is..."
   - "Now, let's look at..." → Just start the content
   - "This is really important because..." → State it directly

2. REMOVE REDUNDANCY
   Don't repeat or over-explain:
   - "An API, or Application Programming Interface, is..." → "An API is..."
   - "They act like a digital key for authentication. This controls access." → "API keys control access."
   - Don't define acronyms if you've already used them

3. ONE IDEA PER SLIDE
   - Don't cram definition + example + analogy into one slide
   - If content feels long, the structure stage should have split it

4. USE ACTIVE VOICE
   - "The request is sent to the API" → "You send a request to the API"
   - "The data is processed" → "The API processes the data"

5. AVOID META-EXPLANATIONS
   - Don't say "Let me explain..." or "I will now show you..."
   - Just explain or show directly


=== BOLD TERMS (for transliteration) ===
If you are bolding a term,make sure you bold every occurrence of that term in the narration.    
Use **bold** for technical terms:
- AI tools: **AI**, **ChatGPT**, **Gemini**, **Claude**
- Technical: **prompt**, **LLM**, **API**, **deepfake**
- UI elements: **Enter**, **Submit**, **click**
- Organizations: **EduPyramids**, **IIT Bombay**

=== BOILERPLATE NARRATION ===

Title Slide:
"Welcome to this Spoken Tutorial on [presentation_title]."

Learning Objectives Slide (BULLETED FORMAT - EACH BULLET ≤80 CHARS):
"In this tutorial, you will learn to,\\n• [short objective 1].\\n• [short objective 2].\\n• [short objective 3]."
Each bullet must be SHORT and achievable. Example: "• Define what an API is."

System Requirements Slide:
"Here I am using a browser on a computer or mobile."

Pre-requisite Slide:
"To follow this tutorial, you should [prerequisites].
Summary Slide:
"Let us summarize what we learned.\\n[brief conversational recap]"

Assignment Slide:
"Now as an assignment,\\n[simple practice task].\\nCompare the results."

Thank You Slide:
"This Spoken Tutorial is brought to you by\\n**EduPyramids Educational Services Private Limited**, **SINE**, **IIT Bombay**.\\nThank you for joining."

=== NARRATIVE FLOW FOR CONTENT SLIDES ===

Apply these 6 narrative patterns:

1. BRIDGE SCENE ANTICIPATION
   Build curiosity before explaining:
   - "What if I told you AI can create a video of someone saying something they never said?"
   - "Imagine watching a news clip that looks completely real, but isn't."
   
2. LINK ACTION TO REFLECTION
   After showing something, prompt the learner to think:
   - "Watch closely. Can you spot what's fake here?"
   - "Pause for a moment. What did you notice?"
   - "Think about it. How would you feel if this happened to you?"

3. CONNECT OBSERVATION TO TIMING
   Point out WHEN and WHAT to notice:
   - "Notice how the lips sync perfectly with the audio."
   - "At this point, look at the edges of the face."
   - "See what happens when I click Submit."

4. TIE MOTIVATION TO ACTION
   Explain WHY the learner should care:
   - "This could happen to you or someone you know."
   - "That's why learning to spot deepfakes matters."
   - "Understanding this protects you from being fooled."

5. SMOOTH TRANSITION TO NEW ACTION
   Connect slides naturally:
   - "Now that we've seen the problem, let's look at solutions."
   - "But here's where it gets interesting..."
   - "With that in mind, let's move to..."

6. IMPROVE ACCURACY AND CLARITY
   Be specific, not vague:
   - Instead of "It looks real" → "The skin texture and lighting match perfectly."
   - Instead of "This is dangerous" → "This can ruin someone's career in hours."

=== EXAMPLE OF GOOD NARRATION ===

"What if I told you that someone could create a video of you saying something you never said?
That's exactly what **deepfakes** can do.
Watch this example closely.
Notice how the lips move perfectly with the audio.
It looks completely real, but it's entirely fake.
This could happen to anyone, including you.
That's why understanding **deepfakes** is so important."

=== EXAMPLE OF BAD NARRATION (too choppy, no flow) ===

"What is a deepfake?
It is a fake video.
AI creates it.
It looks real.
It is dangerous."

=== TRANSITIONS ===
Connect slides naturally,these are some examples:
- "Now, let's move to..."
- "But here's the problem..."
- "With that understanding, let's see..."
- "See the difference?"

Expand EVERY slide's 'notes' into full conversational 'narration' using these patterns."""

    try:
        result = structured_llm.invoke(prompt)
        narration_script = result.model_dump()
        
        slide_count = len(narration_script.get('slides', []))
        print(f"✓ Stage 2 complete: {slide_count} slides with narration")
        
        return {"narration_script": narration_script}
        
    except Exception as e:
        print(f"❌ Stage 2 failed: {e}")
        import traceback
        traceback.print_exc()
        return {"narration_script": {}}
