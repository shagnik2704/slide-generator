"""Question flow logic for outline chat."""
from typing import Dict, List, Optional, Tuple

from .outline_chat_models import ChatMessage


def get_system_prompt(outline_type: str = "FOSS") -> str:
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

Always transform SME answers into the exact template fields: Course Outline Name, Target Audience, Entry Behaviour, Purpose, Course Objectives, Topics Included (can be organized by categories), Topics Not Included, Teaching Scenarios/Examples (core use case), Allied Examples, Recommended number of tutorials, and a tutorial-by-tutorial table (Prerequisites, Topics Details, Time (secs), Comments). 

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

Always transform SME answers into the exact template fields: Course Outline Name, Target Audience, Entry Behaviour, Purpose, Course Objectives, Topics Included, Topics Not Included, Core Example, Allied Examples, Recommended number of tutorials, and a tutorial-by-tutorial table (Prerequisites, Topics Details, Time (secs), Comments). 

ENFORCE PEDAGOGY RULES FOR FOSS:
- Keep theory minimal (1-2 lines max per tutorial)
- Prioritize demo content (75-80% of each tutorial must be demonstration)
- Do NOT use menu-based descriptions (convert "File → Open" to "Click File, then Open. In the dialog, choose your file and click Open.")
- Avoid repetition across tutorials
- Flag topics that are too advanced or off-scope

If unsure about a reply, ask ONE clarifying question. After generating an outline, show it to the SME for review, accept edits, apply them, and produce a final approved outline. 

Always preserve SME wording for domain terms but rewrite for clarity and pedagogy where needed."""


def get_question_flow(outline_type: str = "FOSS") -> Dict[str, Dict]:
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
                        "field": "os_version",
                        "question": "What is the compatible Operating Software version for this ICT course? Please mention the OS name along with its version. If this is a non-IT course, please write 'Not applicable'.",
                        "why": "Captures the operating system context learners will use."
                    },
                    {
                        "field": "outline_name",
                        "question": "What would you like to call this ICT course or training? Please share the course/program name in your own words. The course outline name must be under 50 characters and use only letters, numbers, and spaces (no special characters).",
                        "why": "Title used in template for ICT outlines."
                    },
                    {
                        "field": "target_audience",
                        "question": "Who is the target audience? For example, you can mention the type of teachers, students, or professionals this is meant for.",
                        "why": "Helps choose depth, examples, and teaching methodologies."
                    },
                    {
                        "field": "course_objectives",
                        "question": "What are the main course objectives or learning outcomes? Please list 3–6 clear, action‑oriented objectives, separated by semicolons .",
                        "why": "Fills the Course Objectives section in the outline template."
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
                        "question": "Which topics, skill areas, categories, or methodologies must be included? You can list them as bullets or as a semicolon‑separated list, and group them into categories if that helps.",
                        "why": "Helps structure the course content and ensure all key areas are covered."
                    },
                    {
                        "field": "topics_not_included",
                        "question": "Are there any topics that should NOT be included or are clearly out-of-scope? Please list them (semicolon-separated is perfect).",
                        "why": "Helps avoid scope creep and keeps the course focused."
                    }
                ]
            },
            "examples": {
                "questions": [
                    {
                        "field": "core_example",
                        "question": "Please describe one core teaching scenario, use case, or practical application that can run throughout the course.\n\nThis should be a consistent example that helps you demonstrate the concepts across multiple tutorials. If you don't have a single running example, you can instead describe a common teaching context or use case.",
                        "examples": "Teaching scenarios, lesson plan examples, practical applications, or common use cases.",
                        "why": "ICT courses benefit from a consistent teaching scenario or use case that helps learners see practical applications."
                    },
                    {
                        "field": "allied_examples",
                        "question": "Would you like to add 0–2 allied examples (alternate scenarios, use cases, or contexts) to show variations? If yes, please separate each example with semicolons. If not needed, you can simply say 'none' or 'no'.",
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
                        "question": "We're excited to learn more! Which FOSS tool is this course based on? Please mention the FOSS name along with its version. If this is a non-IT course, please write 'Not applicable'.",
                        "why": "Captures the specific FOSS tool and version before naming the course."
                    },
                    {
                        "field": "os_version",
                        "question": "What is the compatible Operating Software version for this FOSS course, including the OS name and version? If this is a non-IT course, please write 'Not applicable'.",
                        "why": "Captures the operating system context learners will use."
                    },
                    {
                        "field": "outline_name",
                        "question": "What is the full name or title of this course outline (how it should appear to learners)? The course outline name must be under 50 characters and use only letters, numbers, and spaces (no special characters).",
                        "why": "Title used in template for FOSS outlines."
                    },
                    {
                        "field": "target_audience",
                        "question": "Who is the target audience for this course?",
                        "why": "Helps choose depth and examples."
                    },
                    {
                        "field": "course_objectives",
                        "question": "What are the main course objectives or learning outcomes? Please list 3–6 clear, action‑oriented objectives, separated by semicolons .",
                        "why": "Fills the Course Objectives section in the outline template."
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
                        "question": "Which topics must be included? You can give a short list, separated by semicolons or line breaks."
                    },
                    {
                        "field": "topics_not_included",
                        "question": "Which topics should NOT be included or are out-of-scope? Please list them, separated by semicolons.",
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
                        "question": "Do you want 0-2 allied examples (short alternate scenarios) to show variations? If yes, list them separated by semicolons.",
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


def determine_next_question(outline_data: Dict, phase: str, conversation: List[ChatMessage]) -> Tuple[str, Optional[str]]:
    """Determine the next question to ask based on current state and outline type."""
    outline_type = outline_data.get("outline_type", "FOSS").upper()
    question_flow = get_question_flow(outline_type)
    
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
                # Check if field exists and has a non-empty value
                field_value = outline_data.get(field)
                if not field_value or (isinstance(field_value, str) and not field_value.strip()):
                    return phase, q["question"]
        phase = "structure"
    
    if phase == "structure":
        # Collect keywords before tutorial numbering to avoid asking them at the very end
        if not outline_data.get("keywords"):
            return phase, "Any keywords or tags to help search (3-6 words, separated by semicolons)?"

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
                return phase, f"Tutorial #{next_tutorial_num} — please give a short title (under 50 characters, using only letters, numbers, and spaces; no special characters)."
        
        # Check if current tutorial needs more info
        if tutorial_rows:
            last_tutorial = tutorial_rows[-1]
            if not last_tutorial.get("title"):
                return phase, f"Tutorial #{len(tutorial_rows)} — please give a short title (under 50 characters, using only letters, numbers, and spaces; no special characters)."
            if not last_tutorial.get("prerequisites") or last_tutorial.get("prerequisites") == "":
                prev_tutorials = ""
                if len(tutorial_rows) > 1:
                    prev_tutorials = f" (you can refer to the previous tutorial number or specific skills required)"
                return phase, f"For Tutorial #{len(tutorial_rows)} ({last_tutorial.get('title', 'N/A')}): What are the prerequisites? What should learners already know or have completed before starting this tutorial?{prev_tutorials}"
            if not last_tutorial.get("topics_details") or len(last_tutorial.get("topics_details", [])) < 2:
                if outline_type == "ICT":
                    return phase, f"""For Tutorial #{len(tutorial_rows)} ({last_tutorial.get('title', 'N/A')}): please list 3–6 practical steps, activities, or methodologies the learner will follow.

For ICT courses, these steps should describe what learners will actually DO or TEACH, in simple, action-oriented language.
You can provide them as a short semicolon-separated list or bullets.
"""
                else:
                    return phase, f"For Tutorial #{len(tutorial_rows)} ({last_tutorial.get('title', 'N/A')}): list 3–6 demonstrable steps the learner will follow. You can write them as short bullets or as a semicolon‑separated list. Please avoid menu-only instructions like 'File → Open' and instead describe full actions in simple language."
            if not last_tutorial.get("time_seconds") or last_tutorial.get("time_seconds") == 0:
                return phase, f"Could you please share your estimated time for Tutorial #{len(tutorial_rows)} ({last_tutorial.get('title', 'N/A')}) in minutes? Typically, it ranges from 2 to 10 minutes, but feel free to suggest any reasonable duration. You can provide a single number (e.g., '5 minutes') or a range (e.g., '3-4 minutes' or '3 to 4 minutes').\n\nExample answer: 7 minutes or 3-4 minutes"
        
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
            from datetime import datetime
            today = datetime.now().strftime("%Y-%m-%d")
            return phase, f"Preferred date for the outline? (default: {today})"
        # All metadata collected, move to review
        phase = "review"
    
    if phase == "review":
        return phase, None  # No more questions, show draft
    
    return phase, None

