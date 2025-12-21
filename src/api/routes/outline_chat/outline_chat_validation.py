"""Validation functions for outline chat."""
from typing import Dict, List, Tuple


def validate_outline(outline_data: Dict) -> Tuple[List[str], Dict]:
    """Validate the outline against pedagogy rules based on outline type."""
    outline_type = outline_data.get("outline_type", "FOSS").upper()
    
    if outline_type == "ICT":
        return validate_outline_ict(outline_data)
    else:
        return validate_outline_foss(outline_data)


def validate_outline_foss(outline_data: Dict) -> Tuple[List[str], Dict]:
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


def validate_outline_ict(outline_data: Dict) -> Tuple[List[str], Dict]:
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

