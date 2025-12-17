"""Interactive Course Outline chat route for Spoken Tutorials.

This module implements a comprehensive chatbot flow to capture SME input
and convert it into a Spoken Tutorial Course Outline following pedagogy rules.
"""
import json
import os
import re
import time
import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from google import genai
from google.api_core.exceptions import InternalServerError, ResourceExhausted, ServiceUnavailable
from pydantic import BaseModel, Field

load_dotenv()

router = APIRouter(tags=["outline_chat"])


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str  # "user" or "assistant"
    content: str


class TutorialRow(BaseModel):
    """Single tutorial row in the course outline table."""
    tutorial_number: int
    title: str
    prerequisites: str = Field(default="", description="Prerequisites for this tutorial")
    topics_details: List[str] = Field(description="List of demonstrable steps")
    time_seconds: int
    comments: str = ""


class CourseOutlineData(BaseModel):
    """Complete Course Outline data structure matching the template."""
    outline_type: str = "FOSS"  # "FOSS", "ICT", or "OTHER"
    platform_name: str = ""     # Name of FOSS software / ICT platform / Other
    tutorial_name: str = ""
    foss_version: str = "Not Applicable"
    target_audience: str = ""
    entry_behaviour: str = ""
    purpose: str = ""
    recommended_no_of_tutorials: int = 0
    prepared_by: str = ""
    domain: str = ""
    reviewer: str = "IITB ST Team"
    date: str = ""
    keywords: List[str] = []
    about_course: str = ""
    course_objectives: List[str] = []
    topics_included: List[str] = []
    topics_not_included: List[str] = []
    core_example: str = ""
    allied_examples: List[str] = []
    tutorial_rows: List[TutorialRow] = []


class ConversationPhase(str, Enum):
    """Tracks which phase of the interview we're in."""
    WARMUP = "warmup"  # Phase A
    OUTCOMES = "outcomes"  # Phase B
    EXAMPLES = "examples"  # Phase C
    STRUCTURE = "structure"  # Phase D
    METADATA = "metadata"  # Phase E
    REVIEW = "review"
    APPROVED = "approved"


class OutlineChatRequest(BaseModel):
    """Request model for outline chat."""
    conversation: List[ChatMessage]
    outline_data: Optional[Dict] = None
    project_id: Optional[int] = None
    phase: Optional[str] = None


class OutlineChatResponse(BaseModel):
    """Response model for outline chat."""
    project_id: int
    assistant_message: str
    follow_up_question: Optional[str] = None
    phase: str
    outline_data: Dict
    validation_errors: List[str] = []
    pedagogy_compliance: Dict = {}
    is_draft_ready: bool = False
    is_approved: bool = False


def _extract_json_block(text: str) -> str:
    """Extract JSON payload from a response that may contain code fences."""
    cleaned = text.strip()
    if "```" in cleaned:
        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[-1]
        elif "```" in cleaned:
            cleaned = cleaned.split("```", 1)[-1]
        cleaned = cleaned.split("```")[0]
    return cleaned.strip()


def _get_system_prompt(outline_type: str = "FOSS") -> str:
    """Get the system prompt for the chatbot based on outline type."""
    if outline_type.upper() == "ICT":
        return """You are a friendly assistant whose job is to interview a subject-matter expert (SME) and convert their answers into a Spoken Tutorial ICT course outline that fits the "Course Outline - Format" template. 

The SME may not know Spoken Tutorial pedagogy. Ask short, concrete, plain-language questions that guide the SME to provide practical examples, teaching methodologies, and skill-building activities. 

ICT courses focus on:
- Teaching digital skills, concepts, and methodologies (e.g., "Teachers will learn to guide students in...")
- Integration of tools and technologies in educational contexts (e.g., "GeoGebra + AI for Data Modeling")
- Skill-building activities and practical applications (e.g., "Design AI-integrated lesson plans")
- Teaching methodologies and frameworks (e.g., "The AI+X Method", "Concept → Practice → Reflect")
- Practical use cases and scenarios (e.g., "Teaching symmetry with AI drawing tools")
- Categories and skill areas (e.g., "Problem Identification", "Data Collection", "AI Integration")

ICT course structure typically includes:
- Categories or skill areas (e.g., "Core Student Skills", "AI Integration in Lesson Plans")
- Teaching methodologies and frameworks
- Tool integration strategies
- Practical applications and use cases
- Quick capsule tutorials for specific skills

Always transform SME answers into the exact template fields: Tutorial Name, Target Audience, Entry Behaviour, Purpose, Course Objectives, Topics Included (can be organized by categories), Topics Not Included, Teaching Scenarios/Examples (core use case), Allied Examples, Recommended number of tutorials, and a tutorial-by-tutorial table (Prerequisites, Topics Details, Time (secs), Comments). 

ENFORCE PEDAGOGY RULES FOR ICT:
- Focus on skill-building and practical application (what learners will DO or TEACH)
- Include teaching methodologies and integration strategies
- Use relatable teaching scenarios and real-world educational applications
- Keep content practical and actionable (avoid pure theory)
- Organize topics by categories or skill areas when helpful
- Each tutorial should focus on a specific skill, methodology, or integration strategy
- Avoid repetition across tutorials
- Flag topics that are too advanced or off-scope

If unsure about a reply, ask ONE clarifying question. After generating an outline, show it to the SME for review, accept edits, apply them, and produce a final approved outline. 

Always preserve SME wording for domain terms but rewrite for clarity and pedagogy where needed."""
    else:  # FOSS
        return """You are a friendly assistant whose job is to interview a subject-matter expert (SME) and convert their answers into a Spoken Tutorial FOSS course outline that fits the "Course Outline - Format" template. 

The SME may not know Spoken Tutorial pedagogy. Ask short, concrete, plain-language questions that guide the SME to provide practical examples and demonstration steps. 

Always transform SME answers into the exact template fields: Tutorial Name, Target Audience, Entry Behaviour, Purpose, Course Objectives, Topics Included, Topics Not Included, Core Example, Allied Examples, Recommended number of tutorials, and a tutorial-by-tutorial table (Prerequisites, Topics Details, Time (secs), Comments). 

ENFORCE PEDAGOGY RULES FOR FOSS:
- Keep theory minimal (1-2 lines max per tutorial)
- Prioritize demo content (75-80% of each tutorial must be demonstration)
- Do NOT use menu-based descriptions (convert "File → Open" to "Click File, then Open. In the dialog, choose your file and click Open.")
- Avoid repetition across tutorials
- Flag topics that are too advanced or off-scope

If unsure about a reply, ask ONE clarifying question. After generating an outline, show it to the SME for review, accept edits, apply them, and produce a final approved outline. 

Always preserve SME wording for domain terms but rewrite for clarity and pedagogy where needed."""


def _get_question_flow(outline_type: str = "FOSS") -> Dict[str, Dict]:
    """Get the question flow for each phase based on outline type."""
    if outline_type.upper() == "ICT":
        return {
            "warmup": {
                "questions": [
                    {
                        "field": "outline_type",
                        "question": "Before we start, could you tell me whether this is a **FOSS** course (based on free/open-source software), an **ICT** training (general ICT / digital skills), or something else? You can reply with `FOSS`, `ICT`, or `Other` (and add a short note if you pick Other).",
                        "why": "Helps us tag the outline correctly for FOSSEE / ICT pipelines."
                    },
                    {
                        "field": "platform_name",
                        "question": "What is the name of the ICT platform, program, or initiative this course is about?",
                        "why": "Captures the specific ICT focus before naming the course."
                    },
                    {
                        "field": "tutorial_name",
                        "question": "What would you like to call this ICT course or training? Please share the course/program name in your own words.",
                        "why": "Title used in template for ICT outlines."
                    },
                    {
                        "field": "target_audience",
                        "question": "Who is the target audience? For example, you can mention the type of teachers, students, or professionals this is meant for.",
                        "why": "Helps choose depth, examples, and teaching methodologies."
                    },
                    {
                        "field": "entry_behaviour",
                        "question": "What should learners already know before starting? You can give a short list of prerequisites or entry behaviour (for example, basic computer skills or prior teaching experience).",
                        "why": "Entry Behaviour field - helps determine starting point."
                    },
                    {
                        "field": "purpose",
                        "question": "In one simple sentence, what is the main purpose of this course? (What will learners be able to do, teach, or apply after completing it?)",
                        "why": "Template Purpose - defines the learning outcome."
                    }
                ]
            },
            "outcomes": {
                "questions": [
                    {
                        "field": "topics_included",
                        "question": "Which topics, skill areas, categories, or methodologies must be included? You can list them as bullets or as a comma‑separated list, and group them into categories if that helps.",
                        "why": "Helps structure the course content and ensure all key areas are covered."
                    },
                    {
                        "field": "topics_not_included",
                        "question": "Are there any topics that should NOT be included or are clearly out-of-scope? You can briefly list them, if any.",
                        "why": "Helps avoid scope creep and keeps the course focused."
                    }
                ]
            },
            "examples": {
                "questions": [
                    {
                        "field": "core_example",
                        "question": "Please describe one core teaching scenario, use case, or practical application that can run throughout the course.\n\nThis should be a consistent example that helps you demonstrate the concepts across multiple tutorials. If you don’t have a single running example, you can instead describe a common teaching context or use case.",
                        "examples": "Teaching scenarios, lesson plan examples, practical applications, or common use cases.",
                        "why": "ICT courses benefit from a consistent teaching scenario or use case that helps learners see practical applications."
                    },
                    {
                        "field": "allied_examples",
                        "question": "Would you like to add 0–2 allied examples (alternate scenarios, use cases, or contexts) to show variations? These are optional and only if you feel they are helpful. If not needed, you can simply say 'none' or 'no'.",
                        "why": "Allies cover different contexts or applications without bloating the core scenario."
                    }
                ]
            },
            "structure": {
                "questions": [
                    {
                        "field": "recommended_no_of_tutorials",
                        "question": "How many tutorials (modules) should this course contain? There is no fixed limit; choose any number that fits your course design."
                    }
                ]
            }
        }
    else:  # FOSS
        return {
            "warmup": {
                "questions": [
                    {
                        "field": "outline_type",
                        "question": "Before we start, could you tell me whether this is a **FOSS** course (based on free/open-source software), an **ICT** training (general ICT / digital skills), or something else? You can reply with `FOSS`, `ICT`, or `Other` (and add a short note if you pick Other).",
                        "why": "Helps us tag the outline correctly for FOSSEE / ICT pipelines."
                    },
                    {
                        "field": "platform_name",
                        "question": "What is the name of the FOSS software or tool this course is based on?",
                        "why": "Captures the specific FOSS tool before naming the course."
                    },
                    {
                        "field": "tutorial_name",
                        "question": "What is the full name or title of this course (how it should appear to learners)?",
                        "why": "Title used in template for FOSS outlines."
                    },
                    {
                        "field": "target_audience",
                        "question": "Who is the target audience for this course?",
                        "why": "Helps choose depth and examples."
                    },
                    {
                        "field": "entry_behaviour",
                        "question": "What should learners already know before starting? You can give a short list of prerequisites or entry behaviour.",
                        "why": "Entry Behaviour field."
                    },
                    {
                        "field": "purpose",
                        "question": "In one simple sentence, what is the main purpose of this course? (What will learners be able to do after completing it?)",
                        "why": "Template Purpose."
                    }
                ]
            },
            "outcomes": {
                "questions": [
                    {
                        "field": "topics_included",
                        "question": "Which topics must be included? You can give a short list, separated by commas or line breaks."
                    },
                    {
                        "field": "topics_not_included",
                        "question": "Which topics should NOT be included or are out-of-scope?",
                        "why": "Helps avoid scope creep."
                    }
                ]
            },
            "examples": {
                "questions": [
                    {
                        "field": "core_example",
                        "question": "Please describe one core example (a real file, dataset, scenario, or project) we can use for demonstrations.",
                        "examples": "'student marksheet' for Excel; 'bookstore DB' for SQL; 'small image set' for image processing.",
                        "why": "Spoken Tutorials teach via a running example — this is mandatory."
                    },
                    {
                        "field": "allied_examples",
                        "question": "Do you want 0-2 allied examples (short alternate scenarios) to show variations? If yes, list them.",
                        "why": "Allies cover edge-cases without bloating the core demo."
                    }
                ]
            },
            "structure": {
                "questions": [
                    {
                        "field": "recommended_no_of_tutorials",
                        "question": "How many tutorials (modules) should this course contain? There is no fixed limit; choose any number that fits your course design."
                    }
                ]
            }
        }


def _validate_outline(outline_data: Dict) -> Tuple[List[str], Dict]:
    """Validate the outline against pedagogy rules based on outline type."""
    outline_type = outline_data.get("outline_type", "FOSS").upper()
    
    if outline_type == "ICT":
        return _validate_outline_ict(outline_data)
    else:
        return _validate_outline_foss(outline_data)


def _validate_outline_foss(outline_data: Dict) -> Tuple[List[str], Dict]:
    """Validate FOSS outline against pedagogy rules."""
    errors = []
    compliance = {
        "core_example": False,
        "demo_percentage": 0,
        "menu_free": True,
        "time_checks": True,
        "no_repetition": True
    }
    
    # Check core example (mandatory for FOSS)
    if not outline_data.get("core_example"):
        errors.append("Core example is required for FOSS courses. We need a core example to demonstrate steps.")
        compliance["core_example"] = False
    else:
        compliance["core_example"] = True
    
    # Check tutorial rows
    tutorial_rows = outline_data.get("tutorial_rows", [])
    if not tutorial_rows:
        errors.append("At least one tutorial must be defined.")
    
    total_demo_steps = 0
    total_steps = 0
    
    for i, tutorial in enumerate(tutorial_rows, 1):
        topics = tutorial.get("topics_details", [])
        
        # Check minimum demonstrable steps
        if len(topics) < 2:
            errors.append(f"Tutorial #{i} needs at least 2 demonstrable steps.")
        
        # Check for menu-only instructions
        for topic in topics:
            total_steps += 1
            if "→" in topic or ("File" in topic and "Open" in topic and len(topic.split()) < 5):
                compliance["menu_free"] = False
                errors.append(f"Tutorial #{i} has menu-only instruction: '{topic}'. Please rewrite as action steps.")
            else:
                total_demo_steps += 1
        
        # Check time sanity
        time_secs = tutorial.get("time_seconds", 0)
        if time_secs > 600:
            errors.append(f"Tutorial #{i} is too long ({time_secs}s > 10min). Suggest breaking into smaller tutorials.")
            compliance["time_checks"] = False
        elif time_secs < 60:
            errors.append(f"Tutorial #{i} is too short ({time_secs}s < 1min). Suggest expanding content.")
            compliance["time_checks"] = False
    
    # Calculate demo percentage (FOSS requires 75%+ demo content)
    if total_steps > 0:
        demo_pct = (total_demo_steps / total_steps) * 100
        compliance["demo_percentage"] = demo_pct
        if demo_pct < 75:
            errors.append(f"Demo content is only {demo_pct:.1f}%. FOSS courses need ≥75% demo content per tutorial.")
    
    # Check for repetition
    all_topics = []
    for tutorial in tutorial_rows:
        all_topics.extend([t.lower() for t in tutorial.get("topics_details", [])])
    
    seen = set()
    for topic in all_topics:
        if topic in seen:
            compliance["no_repetition"] = False
            errors.append(f"Repetition detected: '{topic}' appears in multiple tutorials. Consider merging or reassigning.")
        seen.add(topic)
    
    return errors, compliance


def _validate_outline_ict(outline_data: Dict) -> Tuple[List[str], Dict]:
    """Validate ICT outline against pedagogy rules."""
    errors = []
    compliance = {
        "core_example": False,
        "practical_content": 0,
        "time_checks": True,
        "no_repetition": True,
        "skill_focused": True
    }
    
    # Check core example/teaching scenario (recommended but not as strict for ICT)
    if not outline_data.get("core_example"):
        errors.append("A core teaching scenario or use case is recommended for ICT courses to maintain consistency.")
        compliance["core_example"] = False
    else:
        compliance["core_example"] = True
    
    # Check tutorial rows
    tutorial_rows = outline_data.get("tutorial_rows", [])
    if not tutorial_rows:
        errors.append("At least one tutorial must be defined.")
    
    total_practical_steps = 0
    total_steps = 0
    
    for i, tutorial in enumerate(tutorial_rows, 1):
        topics = tutorial.get("topics_details", [])
        
        # Check minimum practical steps (ICT focuses on skills/activities)
        if len(topics) < 2:
            errors.append(f"Tutorial #{i} needs at least 2 practical steps or activities.")
        
        # Check for practical, actionable content
        for topic in topics:
            total_steps += 1
            # ICT should focus on skills, methodologies, or practical applications
            if any(keyword in topic.lower() for keyword in ["learn to", "understand", "apply", "design", "create", "integrate", "teach"]):
                total_practical_steps += 1
        
        # Check time sanity
        time_secs = tutorial.get("time_seconds", 0)
        if time_secs > 600:
            errors.append(f"Tutorial #{i} is too long ({time_secs}s > 10min). Suggest breaking into smaller tutorials.")
            compliance["time_checks"] = False
        elif time_secs < 60:
            errors.append(f"Tutorial #{i} is too short ({time_secs}s < 1min). Suggest expanding content.")
            compliance["time_checks"] = False
    
    # Calculate practical content percentage (ICT should be practical/skill-focused)
    if total_steps > 0:
        practical_pct = (total_practical_steps / total_steps) * 100
        compliance["practical_content"] = practical_pct
        if practical_pct < 60:
            errors.append(f"Practical content is only {practical_pct:.1f}%. ICT courses should focus on practical skills and applications (≥60%).")
    
    # Check for repetition
    all_topics = []
    for tutorial in tutorial_rows:
        all_topics.extend([t.lower() for t in tutorial.get("topics_details", [])])
    
    seen = set()
    for topic in all_topics:
        if topic in seen:
            compliance["no_repetition"] = False
            errors.append(f"Repetition detected: '{topic}' appears in multiple tutorials. Consider merging or reassigning.")
        seen.add(topic)
    
    return errors, compliance


def _transform_menu_instructions(text: str) -> str:
    """Transform menu-based instructions into action steps."""
    # Pattern: "File → Open" or "Go to File → Export"
    pattern = r"(\w+)\s*→\s*(\w+)"
    
    def replace_menu(match):
        menu1, menu2 = match.groups()
        return f"Click {menu1}, then {menu2}. In the dialog that appears, choose your option and confirm."
    
    transformed = re.sub(pattern, replace_menu, text)
    return transformed


def _build_conversation_context(conversation: List[ChatMessage], outline_data: Dict, phase: str) -> str:
    """Build the conversation context for the LLM."""
    context = f"""Current Phase: {phase}

Current Outline Data:
{json.dumps(outline_data, indent=2)}

Conversation History:
"""
    for msg in conversation[-10:]:  # Last 10 messages for context
        context += f"{msg.role.upper()}: {msg.content}\n"
    
    return context


def _determine_next_question(outline_data: Dict, phase: str, conversation: List[ChatMessage]) -> Tuple[str, Optional[str]]:
    """Determine the next question to ask based on current state and outline type."""
    outline_type = outline_data.get("outline_type", "FOSS").upper()
    question_flow = _get_question_flow(outline_type)
    
    # Check if we're in a specific phase
    if phase == "warmup":
        for q in question_flow["warmup"]["questions"]:
            field = q["field"]
            if not outline_data.get(field):
                return phase, q["question"]
        phase = "outcomes"
    
    if phase == "outcomes":
        for q in question_flow["outcomes"]["questions"]:
            field = q["field"]
            if not outline_data.get(field):
                return phase, q["question"]
        phase = "examples"
    
    if phase == "examples":
        for q in question_flow["examples"]["questions"]:
            field = q["field"]
            # For optional allied_examples, only ask if the field has never been set.
            if field == "allied_examples":
                if "allied_examples" not in outline_data:
                    return phase, q["question"]
            else:
                if not outline_data.get(field):
                    return phase, q["question"]
        phase = "structure"
    
    if phase == "structure":
        if not outline_data.get("recommended_no_of_tutorials"):
            q = question_flow["structure"]["questions"][0]
            return phase, q["question"]
        
        # Check if we need to collect tutorial details
        num_tutorials = outline_data.get("recommended_no_of_tutorials", 0)
        tutorial_rows = outline_data.get("tutorial_rows", [])
        
        # Initialize tutorial rows if needed
        if not tutorial_rows and num_tutorials > 0:
            outline_data["tutorial_rows"] = []
        
        # Check if we need to start a new tutorial
        if len(tutorial_rows) < num_tutorials:
            # Check if we need to create a new tutorial row
            if len(tutorial_rows) == 0 or (tutorial_rows and tutorial_rows[-1].get("title") and 
                                          tutorial_rows[-1].get("prerequisites") and
                                          tutorial_rows[-1].get("topics_details") and 
                                          len(tutorial_rows[-1].get("topics_details", [])) >= 2 and
                                          tutorial_rows[-1].get("time_seconds")):
                # All info collected for last tutorial, start new one
                next_tutorial_num = len(tutorial_rows) + 1
                return phase, f"Tutorial #{next_tutorial_num} — please give a short title."
        
        # Check if current tutorial needs more info
        if tutorial_rows:
            last_tutorial = tutorial_rows[-1]
            if not last_tutorial.get("title"):
                return phase, f"Tutorial #{len(tutorial_rows)} — please give a short title."
            if not last_tutorial.get("prerequisites") or last_tutorial.get("prerequisites") == "":
                prev_tutorials = ""
                if len(tutorial_rows) > 1:
                    prev_tutorials = f" (you can refer to the previous tutorial number or specific skills required)"
                return phase, f"For Tutorial #{len(tutorial_rows)} ({last_tutorial.get('title', 'N/A')}): What are the prerequisites? What should learners already know or have completed before starting this tutorial?{prev_tutorials}"
            if not last_tutorial.get("topics_details") or len(last_tutorial.get("topics_details", [])) < 2:
                if outline_type == "ICT":
                    return phase, f"""For Tutorial #{len(tutorial_rows)} ({last_tutorial.get('title', 'N/A')}): please list 3–6 practical steps, activities, or methodologies the learner will follow.

For ICT courses, these steps should describe what learners will actually DO or TEACH, in simple, action-oriented language.
"""
                else:
                    return phase, f"For Tutorial #{len(tutorial_rows)} ({last_tutorial.get('title', 'N/A')}): list 3–6 demonstrable steps the learner will follow. You can write them as short bullets or as a comma‑separated list. Please avoid menu-only instructions like 'File → Open' and instead describe full actions in simple language."
            if not last_tutorial.get("time_seconds") or last_tutorial.get("time_seconds") == 0:
                return phase, f"Estimated time for Tutorial #{len(tutorial_rows)} ({last_tutorial.get('title', 'N/A')}) in seconds."
        
        # All tutorials collected, move to metadata
        if len(tutorial_rows) >= num_tutorials and all(
            t.get("title") and t.get("prerequisites") and t.get("topics_details") and len(t.get("topics_details", [])) >= 2 and t.get("time_seconds")
            for t in tutorial_rows
        ):
            phase = "metadata"
    
    if phase == "metadata":
        if not outline_data.get("prepared_by"):
            return phase, "Who prepared the outline? (Name)"
        if not outline_data.get("date"):
            today = datetime.now().strftime("%Y-%m-%d")
            return phase, f"Preferred date for the outline? (default: {today})"
        if not outline_data.get("keywords"):
            return phase, "Any keywords or tags to help search (3-6 words, comma-separated)?"
        # All metadata collected, move to review
        phase = "review"
    
    if phase == "review":
        return phase, None  # No more questions, show draft
    
    return phase, None


def _friendly_rewrite_question(base_question: str, outline_type: str, phase: str) -> str:
    """
    Use LLM to lightly rewrite a base question in a more friendly,
    conversational tone while keeping the meaning the same.
    Falls back to the original question on any error.
    """
    try:
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        prompt = f"""You are a warm, supportive assistant helping to interview a subject-matter expert for a Spoken Tutorial course outline.

Rewrite the following question in a more friendly, conversational way, but keep the meaning and structure the same.

Guidelines:
- Address the user as "you".
- Sound encouraging and collaborative (as if you are gently guiding them).
- Keep it within 1–2 sentences.
- Do NOT add extra instructions, tips, examples, or emojis beyond what is already present.
- Do NOT change any technical terms or placeholders.

Question:
{base_question}

Return ONLY the rewritten question text."""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        rewritten = response.text.strip()
        # Basic sanity check: avoid empty or extremely short output
        if len(rewritten) < 5:
            return base_question
        return rewritten
    except Exception:
        return base_question


def _extract_field_from_response(field: str, response: str, outline_data: Dict) -> Dict:
    """Extract and transform field value from SME response."""
    updated = outline_data.copy()
    
    if field == "course_objectives":
        # Extract bullet points or numbered list
        objectives = re.findall(r'[•\-\d+\.]\s*(.+?)(?:\n|$)', response, re.MULTILINE)
        if not objectives:
            # Try comma-separated or line-separated
            if ',' in response:
                objectives = [item.strip() for item in response.split(',') if item.strip()]
            else:
                objectives = [line.strip() for line in response.split('\n') if line.strip()]
        updated["course_objectives"] = objectives[:6]  # Max 6
    
    elif field == "topics_included" or field == "topics_not_included":
        topics = re.findall(r'[•\-\d+\.]\s*(.+?)(?:\n|$)', response, re.MULTILINE)
        if not topics:
            if ',' in response:
                topics = [item.strip() for item in response.split(',') if item.strip()]
            else:
                topics = [line.strip() for line in response.split('\n') if line.strip()]
        updated[field] = topics
    
    elif field == "allied_examples":
        examples = re.findall(r'[•\-\d+\.]\s*(.+?)(?:\n|$)', response, re.MULTILINE)
        if not examples:
            if ',' in response:
                examples = [
                    item.strip() for item in response.split(',')
                    if item.strip() and item.strip().lower() not in ['no', 'none', 'n/a']
                ]
            else:
                examples = [
                    line.strip() for line in response.split('\n')
                    if line.strip() and line.strip().lower() not in ['no', 'none', 'n/a']
                ]
        updated["allied_examples"] = examples[:2]  # Max 2
    
    elif field == "keywords":
        keywords = [k.strip() for k in response.split(',') if k.strip()]
        updated["keywords"] = keywords[:6]  # Max 6
    
    elif field == "recommended_no_of_tutorials":
        # Extract number
        numbers = re.findall(r'\d+', response)
        if numbers:
            updated["recommended_no_of_tutorials"] = int(numbers[0])
    
    elif field == "tutorial_rows":
        # This is handled separately in the tutorial collection logic
        pass
    
    else:
        # Simple string field
        updated[field] = response.strip()
    
    return updated


def _generate_draft_outline(outline_data: Dict) -> str:
    """Generate a human-readable draft outline for review."""
    draft = f"""# Course Outline Draft

## Tutorial Information
- **Tutorial Name:** {outline_data.get('tutorial_name', 'N/A')}
- **Target Audience:** {outline_data.get('target_audience', 'N/A')}
- **Entry Behaviour:** {outline_data.get('entry_behaviour', 'N/A')}
- **Purpose:** {outline_data.get('purpose', 'N/A')}
- **Recommended Tutorials:** {outline_data.get('recommended_no_of_tutorials', 0)}

## About the Course
{outline_data.get('about_course', 'To be filled')}

## Course Objectives
"""
    for obj in outline_data.get('course_objectives', []):
        draft += f"- {obj}\n"
    
    draft += f"""
## Topics Included
"""
    for topic in outline_data.get('topics_included', []):
        draft += f"- {topic}\n"
    
    draft += f"""
## Topics Not Included
"""
    for topic in outline_data.get('topics_not_included', []):
        draft += f"- {topic}\n"
    
    draft += f"""
## Examples
- **Core Example:** {outline_data.get('core_example', 'N/A')}
- **Allied Examples:** {', '.join(outline_data.get('allied_examples', [])) or 'None'}

## Course Outline Table

| Tutorial | Prerequisites | Topics Details | Time (secs) | Comments |
|----------|--------------|---------------|-------------|----------|
"""
    for tutorial in outline_data.get('tutorial_rows', []):
        topics = '; '.join(tutorial.get('topics_details', []))
        prerequisites = tutorial.get('prerequisites', 'N/A')
        draft += f"| {tutorial.get('title', 'N/A')} | {prerequisites} | {topics} | {tutorial.get('time_seconds', 0)} | {tutorial.get('comments', '')} |\n"
    
    draft += f"""
## Metadata
- **Prepared By:** {outline_data.get('prepared_by', 'N/A')}
- **Reviewer:** {outline_data.get('reviewer', 'IITB ST Team')}
- **Date:** {outline_data.get('date', 'N/A')}
- **Keywords:** {', '.join(outline_data.get('keywords', []))}
"""
    return draft


@router.post("/outline_chat")
async def outline_chat(request: OutlineChatRequest):
    """Chat endpoint that guides SME through Course Outline creation."""
    try:
        if not request.conversation:
            raise HTTPException(status_code=400, detail="Conversation history is required")
        
        project_root = Path(__file__).parent.parent.parent
        session_dir = project_root / "output" / "outline_sessions"
        session_dir.mkdir(parents=True, exist_ok=True)
        
        project_id = request.project_id or int(time.time())
        session_path = session_dir / f"outline_{project_id}.json"
        
        # Load or initialize outline data
        if session_path.exists():
            with open(session_path, "r") as f:
                session_data = json.load(f)
                outline_data = session_data.get("outline_data", {})
                phase = session_data.get("phase", "warmup")
        else:
            outline_data = {}
            phase = request.phase or "warmup"
        
        # Check for approval command
        last_message = request.conversation[-1] if request.conversation else None
        user_content = last_message.content.lower().strip() if last_message and last_message.role == "user" else ""
        
        if user_content == "approve" and phase == "review":
                # Mark as approved
                phase = "approved"
                outline_data["status"] = "approved"
                outline_data["approved_at"] = datetime.now().isoformat()
                
                # Save final outline
                with open(session_path, "w") as f:
                    json.dump({
                        "project_id": project_id,
                        "outline_data": outline_data,
                        "phase": phase,
                        "updated_at": time.time()
                    }, f, indent=2)
                
                return JSONResponse({
                    "project_id": project_id,
                    "assistant_message": "Outline approved! Generating final outputs...",
                    "phase": phase,
                    "outline_data": outline_data,
                    "is_approved": True,
                    "is_draft_ready": True
                })
        
        # Process the conversation - extract information from last user message
        if last_message and last_message.role == "user" and user_content and user_content != "approve":
            # Use LLM to extract and structure information
            client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
            
            # Determine which field we're collecting
            outline_type = outline_data.get("outline_type", "FOSS").upper()
            question_flow = _get_question_flow(outline_type)
            current_field = None
            extraction_prompt = ""
            
            if phase == "warmup":
                for q in question_flow["warmup"]["questions"]:
                    if not outline_data.get(q["field"]):
                        current_field = q["field"]
                        extraction_prompt = f"""Extract the {q['field']} from the user's response. Return only the extracted value as a simple string (no JSON, no explanation).

User response: {last_message.content}
Field to extract: {q['field']}
Expected format: {q.get('why', 'text string')}"""
                        break
            elif phase == "outcomes":
                for q in question_flow["outcomes"]["questions"]:
                    if not outline_data.get(q["field"]):
                        current_field = q["field"]
                        if q["field"] in ["course_objectives", "topics_included", "topics_not_included"]:
                            extraction_prompt = f"""Extract {q['field']} from the user's response. Return as a JSON array of strings.

User response: {last_message.content}
Field: {q['field']}
Return format: ["item1", "item2", "item3"]"""
                        else:
                            extraction_prompt = f"""Extract {q['field']} from the user's response. Return only the value."""
                        break
            elif phase == "examples":
                for q in question_flow["examples"]["questions"]:
                    if not outline_data.get(q["field"]):
                        current_field = q["field"]
                        if q["field"] == "allied_examples":
                            extraction_prompt = f"""Extract allied examples from the user's response. Return as JSON array. If user says 'no' or 'none', return empty array [].

User response: {last_message.content}
Return format: ["example1", "example2"] or []"""
                        else:
                            if outline_type == "ICT":
                                extraction_prompt = f"""Extract the core teaching scenario, use case, or practical application from the user's response for an ICT course.

This should be a consistent example that demonstrates concepts across multiple tutorials.
Examples: 'Teaching symmetry with AI drawing tools', 'Data collection for student projects', 'Creating lesson plans with AI assistance'

User response: {last_message.content}
Return only the scenario description as a string (teaching scenario, use case, or practical application)."""
                            else:
                                extraction_prompt = f"""Extract the core example from the user's response. Return only the example description as a string.

User response: {last_message.content}"""
                        break
            elif phase == "structure":
                # Check if we're still collecting the number of tutorials
                if not outline_data.get("recommended_no_of_tutorials"):
                    current_field = "recommended_no_of_tutorials"
                    extraction_prompt = f"""Extract the number of tutorials from the user's response. Return only the number as an integer.

User response: {last_message.content}
Example: "5" should return 5, "eight" should return 8"""
                else:
                    # Check if collecting tutorial info
                    num_tutorials = outline_data.get("recommended_no_of_tutorials", 0)
                    tutorial_rows = outline_data.get("tutorial_rows", [])
                    
                    # Initialize tutorial rows if needed
                    if not tutorial_rows:
                        outline_data["tutorial_rows"] = []
                    
                    # Check if we need to create a new tutorial row
                    if len(tutorial_rows) < num_tutorials:
                        if not tutorial_rows or (tutorial_rows and 
                                                tutorial_rows[-1].get("title") and 
                                                tutorial_rows[-1].get("prerequisites") and
                                                tutorial_rows[-1].get("topics_details") and 
                                                len(tutorial_rows[-1].get("topics_details", [])) >= 2 and
                                                tutorial_rows[-1].get("time_seconds")):
                            # Create new tutorial row
                            tutorial_rows.append({
                                "tutorial_number": len(tutorial_rows) + 1,
                                "title": "",
                                "prerequisites": "",
                                "topics_details": [],
                                "time_seconds": 0,
                                "comments": ""
                            })
                            outline_data["tutorial_rows"] = tutorial_rows
                    
                    # Determine what we're collecting for current tutorial
                    if tutorial_rows:
                        last_tutorial = tutorial_rows[-1]
                        if not last_tutorial.get("title"):
                            current_field = "tutorial_title"
                            extraction_prompt = f"""Extract the tutorial title from the user's response. Return only the title as a string.

User response: {last_message.content}"""
                        elif not last_tutorial.get("prerequisites") or last_tutorial.get("prerequisites") == "":
                            current_field = "tutorial_prerequisites"
                            extraction_prompt = f"""Extract the prerequisites from the user's response. Return as a string describing what learners need before this tutorial (e.g., "Completion of Tutorial #1" or specific skills).

User response: {last_message.content}"""
                        elif not last_tutorial.get("topics_details") or len(last_tutorial.get("topics_details", [])) < 2:
                            current_field = "tutorial_steps"
                            if outline_type == "ICT":
                                extraction_prompt = f"""Extract practical steps, activities, or methodologies from the user's response for an ICT course tutorial.

ICT tutorial steps should focus on:
- Teaching methodologies (what learners will teach/guide)
- Skill-building activities (what learners will practice)
- Integration strategies (how learners will combine tools/concepts)
- Practical applications (what learners will create/apply)

User response: {last_message.content}
Return format: ["step1", "step2", "step3"]
Each step should be actionable and focused on skills, teaching methods, or practical applications."""
                            else:
                                extraction_prompt = f"""Extract demonstrable steps from the user's response. Transform any menu instructions (like "File → Open") into action descriptions. Return as JSON array of strings.

User response: {last_message.content}
Return format: ["step1", "step2", "step3"]
Example transformation: "File → Open" becomes "Click File, then Open. In the dialog, choose your file and click Open." """
                        elif not last_tutorial.get("time_seconds") or last_tutorial.get("time_seconds") == 0:
                            current_field = "tutorial_time"
                            extraction_prompt = f"""Extract the time in seconds from the user's response. Return only the number as an integer.

User response: {last_message.content}
Example: "300" or "5 minutes" should return 300"""
                        else:
                            current_field = "tutorial_comments"
                            extraction_prompt = f"""Extract any comments or notes from the user's response. Return as a string.

User response: {last_message.content}"""
            
            elif phase == "metadata":
                if not outline_data.get("prepared_by"):
                    current_field = "prepared_by"
                    extraction_prompt = f"""Extract the name of the person who prepared the outline. Return only the name.

User response: {last_message.content}"""
                elif not outline_data.get("date"):
                    current_field = "date"
                    extraction_prompt = f"""Extract the date from the user's response. Return in YYYY-MM-DD format. If user says "today" or doesn't specify, use {datetime.now().strftime('%Y-%m-%d')}.

User response: {last_message.content}"""
                elif not outline_data.get("keywords"):
                    current_field = "keywords"
                    extraction_prompt = f"""Extract keywords from the user's response. Return as JSON array of strings (3-6 keywords).

User response: {last_message.content}
Return format: ["keyword1", "keyword2", "keyword3"]"""
            
            # Extract using LLM if we have a field to extract
            if current_field and extraction_prompt:
                try:
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=extraction_prompt,
                    )
                    extracted_text = response.text.strip()
                    
                    # Parse extracted value
                    if current_field == "outline_type":
                        # Normalize outline type
                        extracted_type = extracted_text.strip().upper()
                        if extracted_type in ["FOSS", "ICT", "OTHER"]:
                            outline_data["outline_type"] = extracted_type
                        elif "foss" in extracted_text.lower() or "free" in extracted_text.lower() or "open" in extracted_text.lower():
                            outline_data["outline_type"] = "FOSS"
                        elif "ict" in extracted_text.lower() or "digital" in extracted_text.lower() or "skill" in extracted_text.lower():
                            outline_data["outline_type"] = "ICT"
                        elif "other" in extracted_text.lower():
                            outline_data["outline_type"] = "OTHER"
                        else:
                            # Default to FOSS if unclear
                            outline_data["outline_type"] = "FOSS"
                    elif current_field == "recommended_no_of_tutorials":
                        # Extract number from response
                        numbers = re.findall(r'\d+', extracted_text)
                        if numbers:
                            outline_data["recommended_no_of_tutorials"] = int(numbers[0])
                        else:
                            # Try to parse the original message
                            numbers = re.findall(r'\d+', last_message.content)
                            if numbers:
                                outline_data["recommended_no_of_tutorials"] = int(numbers[0])
                    elif current_field == "tutorial_title":
                        tutorial_rows = outline_data.get("tutorial_rows", [])
                        if tutorial_rows:
                            tutorial_rows[-1]["title"] = extracted_text.strip('"\'')
                    elif current_field == "tutorial_prerequisites":
                        tutorial_rows = outline_data.get("tutorial_rows", [])
                        if tutorial_rows:
                            tutorial_rows[-1]["prerequisites"] = extracted_text.strip('"\'')
                    elif current_field == "tutorial_steps":
                        tutorial_rows = outline_data.get("tutorial_rows", [])
                        if tutorial_rows:
                            # Try to parse as JSON array
                            try:
                                steps = json.loads(_extract_json_block(extracted_text))
                            except:
                                # Fallback to regex or comma/line-based extraction
                                steps = re.findall(r'[•\-\d+\.]\s*(.+?)(?:\n|$)', last_message.content, re.MULTILINE)
                                if not steps:
                                    if ',' in last_message.content:
                                        steps = [item.strip() for item in last_message.content.split(',') if item.strip()]
                                    else:
                                        steps = [line.strip() for line in last_message.content.split('\n') if line.strip()]
                            # Transform menu instructions (only for FOSS)
                            if outline_type == "FOSS":
                                steps = [_transform_menu_instructions(s) for s in steps if s.strip()]
                            else:
                                steps = [s.strip() for s in steps if s.strip()]
                            tutorial_rows[-1]["topics_details"] = steps
                    elif current_field == "tutorial_time":
                        tutorial_rows = outline_data.get("tutorial_rows", [])
                        if tutorial_rows:
                            numbers = re.findall(r'\d+', extracted_text)
                            if numbers:
                                tutorial_rows[-1]["time_seconds"] = int(numbers[0])
                            # Handle "X minutes" format
                            elif "minute" in extracted_text.lower():
                                minutes = re.findall(r'\d+', extracted_text)
                                if minutes:
                                    tutorial_rows[-1]["time_seconds"] = int(minutes[0]) * 60
                    elif current_field == "tutorial_comments":
                        tutorial_rows = outline_data.get("tutorial_rows", [])
                        if tutorial_rows:
                            tutorial_rows[-1]["comments"] = extracted_text.strip('"\'')
                    elif current_field in ["course_objectives", "topics_included", "topics_not_included", "allied_examples", "keywords"]:
                        try:
                            value = json.loads(_extract_json_block(extracted_text))
                            outline_data[current_field] = value
                        except:
                            # Fallback to regex extraction
                            outline_data = _extract_field_from_response(current_field, last_message.content, outline_data)
                    else:
                        outline_data[current_field] = extracted_text.strip('"\'')
                except Exception as e:
                    # Fallback to regex-based extraction
                    if current_field == "outline_type":
                        # Try to extract from user message directly
                        user_lower = last_message.content.lower()
                        if "foss" in user_lower or "free" in user_lower or "open" in user_lower:
                            outline_data["outline_type"] = "FOSS"
                        elif "ict" in user_lower or "digital" in user_lower or "skill" in user_lower:
                            outline_data["outline_type"] = "ICT"
                        elif "other" in user_lower:
                            outline_data["outline_type"] = "OTHER"
                        else:
                            # Default to FOSS if unclear
                            outline_data["outline_type"] = "FOSS"
                    elif current_field == "recommended_no_of_tutorials":
                        numbers = re.findall(r'\d+', last_message.content)
                        if numbers:
                            outline_data["recommended_no_of_tutorials"] = int(numbers[0])
                    elif current_field in ["tutorial_title", "tutorial_prerequisites", "tutorial_steps", "tutorial_time", "tutorial_comments"]:
                        # Handle tutorial fields manually
                        tutorial_rows = outline_data.get("tutorial_rows", [])
                        if tutorial_rows:
                            if current_field == "tutorial_title":
                                tutorial_rows[-1]["title"] = last_message.content.strip()
                            elif current_field == "tutorial_prerequisites":
                                tutorial_rows[-1]["prerequisites"] = last_message.content.strip()
                            elif current_field == "tutorial_steps":
                                steps = re.findall(r'[•\-\d+\.]\s*(.+?)(?:\n|$)', last_message.content, re.MULTILINE)
                                if not steps:
                                    if ',' in last_message.content:
                                        steps = [item.strip() for item in last_message.content.split(',') if item.strip()]
                                    else:
                                        steps = [line.strip() for line in last_message.content.split('\n') if line.strip()]
                                # Transform menu instructions (only for FOSS)
                                if outline_type == "FOSS":
                                    steps = [_transform_menu_instructions(s) for s in steps if s.strip()]
                                else:
                                    steps = [s.strip() for s in steps if s.strip()]
                                tutorial_rows[-1]["topics_details"] = steps
                            elif current_field == "tutorial_time":
                                numbers = re.findall(r'\d+', last_message.content)
                                if numbers:
                                    tutorial_rows[-1]["time_seconds"] = int(numbers[0])
                            elif current_field == "tutorial_comments":
                                tutorial_rows[-1]["comments"] = last_message.content.strip()
                    else:
                        outline_data = _extract_field_from_response(current_field, last_message.content, outline_data)
        
        # Determine next question
        phase, next_question = _determine_next_question(outline_data, phase, request.conversation)
        
        assistant_message = ""
        
        # Handle edits in review phase
        if phase == "review" and outline_data.get("draft_shown") and last_message and last_message.role == "user" and user_content and user_content != "approve":
            # User is providing edits - use LLM to parse and apply
            try:
                client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
                edit_prompt = f"""The user wants to edit the course outline. Parse their edit request and return a JSON object with the changes to apply.

Current outline data:
{json.dumps(outline_data, indent=2)}

User's edit request: {last_message.content}

Return JSON with structure:
{{
  "updates": {{
    "field_name": "new_value",
    "tutorial_rows": [
      {{"tutorial_number": 1, "title": "...", "prerequisites": "...", "topics_details": [...], "time_seconds": 300, "comments": "..."}},
      ...
    ]
  }},
  "summary": "Brief description of changes made"
}}

Only include fields that need to be changed. For tutorial_rows, include ALL tutorials (not just changed ones)."""
                
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=edit_prompt,
                )
                edit_json = json.loads(_extract_json_block(response.text))
                
                # Apply updates
                if "updates" in edit_json:
                    updates = edit_json["updates"]
                    for key, value in updates.items():
                        if key == "tutorial_rows":
                            outline_data["tutorial_rows"] = value
                        else:
                            outline_data[key] = value
                    
                    assistant_message = f"✓ Applied your edits: {edit_json.get('summary', 'Changes applied')}\n\n"
                    outline_data["draft_shown"] = False  # Regenerate draft
                else:
                    assistant_message = "I understood your request. Let me apply those changes...\n\n"
            except Exception as e:
                assistant_message = f"I had trouble parsing your edits. Could you rephrase? (Error: {str(e)})\n\n"
        
        # If we've collected enough info, generate draft
        if phase == "review" and not outline_data.get("draft_shown"):
            # Auto-generate "About the Course" if missing
            if not outline_data.get("about_course"):
                try:
                    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
                    about_prompt = f"""Generate a brief 1-2 paragraph "About the Course" section for a Spoken Tutorial course outline.

Tutorial Name: {outline_data.get('tutorial_name', 'N/A')}
Purpose: {outline_data.get('purpose', 'N/A')}
Target Audience: {outline_data.get('target_audience', 'N/A')}
Course Objectives: {', '.join(outline_data.get('course_objectives', []))}

Write 1-2 paragraphs (2-4 sentences total) describing what this course teaches and who it's for. Keep it concise and clear."""
                    
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=about_prompt,
                    )
                    outline_data["about_course"] = response.text.strip()
                except:
                    outline_data["about_course"] = f"This course teaches {outline_data.get('tutorial_name', 'the subject')} to {outline_data.get('target_audience', 'learners')}."
            
            # Generate draft
            draft = _generate_draft_outline(outline_data)
            outline_data["draft"] = draft
            outline_data["draft_shown"] = True
            
            # Run validation
            errors, compliance = _validate_outline(outline_data)
            
            outline_type = outline_data.get("outline_type", "FOSS").upper()
            
            if outline_type == "ICT":
                assistant_message = f"""Here's your draft Course Outline:

{draft}

**Pedagogy Compliance:**
- Core Teaching Scenario: {'✓' if compliance.get('core_example', False) else '⚠️ Recommended'}
- Practical Content: {compliance.get('practical_content', 0):.1f}% {'✓' if compliance.get('practical_content', 0) >= 60 else '⚠️ Need ≥60%'}
- Time checks: {'✓' if compliance.get('time_checks', True) else '⚠️'}
- No repetition: {'✓' if compliance.get('no_repetition', True) else '⚠️'}
- Skill-focused: {'✓' if compliance.get('skill_focused', True) else '⚠️'}

"""
            else:
                assistant_message = f"""Here's your draft Course Outline:

{draft}

**Pedagogy Compliance:**
- Core Example: {'✓' if compliance.get('core_example', False) else '✗'}
- Demo Content: {compliance.get('demo_percentage', 0):.1f}% {'✓' if compliance.get('demo_percentage', 0) >= 75 else '⚠️ Need ≥75%'}
- Menu-free: {'✓' if compliance.get('menu_free', True) else '⚠️ Rewritten'}
- Time checks: {'✓' if compliance.get('time_checks', True) else '⚠️'}
- No repetition: {'✓' if compliance.get('no_repetition', True) else '⚠️'}

"""
            if errors:
                assistant_message += f"\n**Issues to address:**\n" + "\n".join(f"- {e}" for e in errors)
            
            assistant_message += "\n\nPlease review and suggest any edits. Type 'approve' when ready to finalize."
        elif phase == "review" and outline_data.get("draft_shown") and not assistant_message:
            # Already showed draft, waiting for edits or approval
            assistant_message = "Please review the draft above and suggest any edits, or type 'approve' to finalize."
        elif next_question:
            # Rewrite the base question in a slightly friendlier tone using LLM,
            # but fall back to the original text if anything fails.
            outline_type = outline_data.get("outline_type", "FOSS").upper()
            assistant_message = _friendly_rewrite_question(next_question, outline_type, phase)
        else:
            assistant_message = "Thank you! All information collected."
        
        # Save session
        with open(session_path, "w") as f:
            json.dump({
                "project_id": project_id,
                "outline_data": outline_data,
                "phase": phase,
                "updated_at": time.time()
            }, f, indent=2)
        
        # Run validation if we have enough data
        validation_errors = []
        pedagogy_compliance = {}
        if phase in ["review", "approved"]:
            validation_errors, pedagogy_compliance = _validate_outline(outline_data)
        
        return JSONResponse({
            "project_id": project_id,
            "assistant_message": assistant_message,
            "follow_up_question": next_question if phase != "review" else None,
            "phase": phase,
            "outline_data": outline_data,
            "validation_errors": validation_errors,
            "pedagogy_compliance": pedagogy_compliance,
            "is_draft_ready": phase == "review",
            "is_approved": phase == "approved"
        })
    
    except (ResourceExhausted, ServiceUnavailable, InternalServerError) as e:
        traceback.print_exc()
        raise HTTPException(status_code=503, detail=f"AI backend unavailable: {e}")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.options("/outline_chat")
async def outline_chat_options():
    """Handle CORS preflight for the outline chat endpoint.

    Some deployments were returning 405 for OPTIONS when middleware
    configuration was bypassed. This explicit handler ensures a 200
    with permissive CORS headers so browsers can proceed.
    """
    return JSONResponse(
        status_code=200,
        content={"status": "ok"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


@router.get("/outline_chat/{project_id}/export")
async def export_outline(project_id: int, format: str = "json"):
    """Export the finalized outline in JSON or PDF-ready format."""
    project_root = Path(__file__).parent.parent.parent
    session_dir = project_root / "output" / "outline_sessions"
    session_path = session_dir / f"outline_{project_id}.json"
    
    if not session_path.exists():
        raise HTTPException(status_code=404, detail="Outline not found")
    
    with open(session_path, "r") as f:
        session_data = json.load(f)
        outline_data = session_data.get("outline_data", {})
    
    if format == "json":
        # Return machine-readable JSON
        return JSONResponse({
            "tutorial_name": outline_data.get("tutorial_name"),
            "foss_version": outline_data.get("foss_version", "Not Applicable"),
            "target_audience": outline_data.get("target_audience"),
            "entry_behaviour": outline_data.get("entry_behaviour"),
            "purpose": outline_data.get("purpose"),
            "recommended_no_of_tutorials": outline_data.get("recommended_no_of_tutorials", 0),
            "prepared_by": outline_data.get("prepared_by"),
            "domain": outline_data.get("domain", ""),
            "reviewer": outline_data.get("reviewer", "IITB ST Team"),
            "date": outline_data.get("date"),
            "keywords": outline_data.get("keywords", []),
            "about_course": outline_data.get("about_course", ""),
            "course_objectives": outline_data.get("course_objectives", []),
            "topics_included": outline_data.get("topics_included", []),
            "topics_not_included": outline_data.get("topics_not_included", []),
            "core_example": outline_data.get("core_example"),
            "allied_examples": outline_data.get("allied_examples", []),
            "tutorial_rows": outline_data.get("tutorial_rows", [])
        })
    else:
        raise HTTPException(status_code=400, detail="Format must be 'json'")
