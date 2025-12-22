"""
Compliance checking service for Spoken Tutorial scripts.
Runs checklist-style checks and returns pass/fail results with violations.
"""
import re
from typing import Dict, List, Any


def check_compliance(json_script: dict, tutorial_type: str = "conceptual") -> dict:
    """
    Run all compliance checks on a script and return checklist results.
    
    Args:
        json_script: The parsed script JSON
        tutorial_type: 'conceptual' or 'demo'
    
    Returns:
        Dictionary with checklist results (no scores, just pass/fail)
    """
    slides = json_script.get('slides', [])
    
    # Run all checks
    formatting_results = _check_formatting(slides)
    narration_results = _check_narration(slides, tutorial_type)
    structure_results = _check_structure(slides, json_script)
    
    # Count total violations
    total_violations = sum(
        len(check.get('violations', [])) 
        for category in [formatting_results, narration_results, structure_results]
        for check in category.values()
        if not check.get('passed', True)
    )
    
    return {
        "formatting": formatting_results,
        "narration": narration_results,
        "structure": structure_results,
        "total_violations": total_violations
    }


def _check_formatting(slides: List[dict]) -> dict:
    """Check formatting rules."""
    results = {}
    
    # 1. Sentence length check (≤80 characters)
    sentence_violations = []
    for i, slide in enumerate(slides):
        title = slide.get('title', '').lower()
        # Skip LO and Thank You slides
        if 'learning' in title or 'thank you' in title:
            continue
        
        narration = slide.get('narration', '')
        sentences = _split_sentences(narration)
        for sentence in sentences:
            if len(sentence.strip()) > 80:
                sentence_violations.append({
                    "slide": i + 1,
                    "issue": f"Sentence too long ({len(sentence.strip())} chars)",
                    "text": sentence.strip()[:50] + "..." if len(sentence.strip()) > 50 else sentence.strip()
                })
    
    results["sentence_length"] = {
        "rule": "Sentence length ≤80 characters",
        "passed": len(sentence_violations) == 0,
        "violations": sentence_violations
    }
    
    # 2. New lines check (sentences on new lines)
    newline_violations = []
    for i, slide in enumerate(slides):
        title = slide.get('title', '').lower()
        if 'learning' in title or 'thank you' in title:
            continue
            
        narration = slide.get('narration', '')
        # Check if there are multiple sentences without newlines
        sentences = _split_sentences(narration)
        if len(sentences) > 1:
            # Check if narration has proper newlines
            newline_count = narration.count('\\n') + narration.count('\n')
            if newline_count < len(sentences) - 1:
                newline_violations.append({
                    "slide": i + 1,
                    "issue": f"Multiple sentences without newlines ({len(sentences)} sentences, {newline_count} newlines)"
                })
    
    results["new_lines"] = {
        "rule": "Each sentence on new line",
        "passed": len(newline_violations) == 0,
        "violations": newline_violations
    }
    
    # 3. Forbidden symbols check
    symbol_violations = []
    forbidden_patterns = [r'->', r'-->', r'^\*\s', r'^-\s']
    for i, slide in enumerate(slides):
        narration = slide.get('narration', '')
        for pattern in forbidden_patterns:
            if pattern.startswith('^'):
                # Check at line start
                lines = narration.split('\n')
                for line in lines:
                    if re.match(pattern, line.strip()):
                        symbol_violations.append({
                            "slide": i + 1,
                            "issue": f"Forbidden symbol at line start",
                            "text": line.strip()[:30]
                        })
            else:
                if re.search(pattern, narration):
                    symbol_violations.append({
                        "slide": i + 1,
                        "issue": f"Contains forbidden symbol: {pattern.replace(chr(92), '')}"
                    })
    
    results["no_forbidden_symbols"] = {
        "rule": "No forbidden symbols (→, -->, * or - at line start)",
        "passed": len(symbol_violations) == 0,
        "violations": symbol_violations
    }
    
    # 4. Bold markers for technical terms (advisory)
    bold_count = 0
    for slide in slides:
        narration = slide.get('narration', '')
        bold_count += len(re.findall(r'\*\*[^*]+\*\*', narration))
    
    results["bold_markers"] = {
        "rule": "Technical terms use **bold** markers",
        "passed": bold_count > 0,
        "violations": [] if bold_count > 0 else [{
            "slide": 0,
            "issue": "No bold markers found in script"
        }]
    }
    
    return results


def _check_narration(slides: List[dict], tutorial_type: str) -> dict:
    """Check narration quality rules."""
    results = {}
    
    if tutorial_type == "demo":
        # Demo-specific checks
        
        # 1. Action verbs check
        action_verbs = ['click', 'open', 'type', 'select', 'navigate', 'copy', 'paste', 
                       'drag', 'enter', 'press', 'scroll', 'hover', 'choose', 'tap']
        action_violations = []
        
        for i, slide in enumerate(slides):
            title = slide.get('title', '').lower()
            # Skip boilerplate slides
            if any(x in title for x in ['title', 'learning', 'thank', 'summary', 'assignment', 'prerequisite', 'system']):
                continue
            
            narration = slide.get('narration', '').lower()
            has_action = any(verb in narration for verb in action_verbs)
            if not has_action:
                action_violations.append({
                    "slide": i + 1,
                    "issue": "No action verbs found (Click, Open, Type, etc.)"
                })
        
        results["action_verbs"] = {
            "rule": "Uses action verbs (Click, Open, Type...)",
            "passed": len(action_violations) == 0,
            "violations": action_violations
        }
        
        # 2. Screen location check
        location_words = ['top', 'bottom', 'left', 'right', 'corner', 'menu', 'toolbar', 
                         'panel', 'sidebar', 'dialog', 'window', 'tab', 'bar']
        location_violations = []
        
        for i, slide in enumerate(slides):
            title = slide.get('title', '').lower()
            if any(x in title for x in ['title', 'learning', 'thank', 'summary', 'assignment', 'prerequisite', 'system']):
                continue
            
            narration = slide.get('narration', '').lower()
            # Check if click/select actions have location context
            if 'click' in narration or 'select' in narration:
                has_location = any(loc in narration for loc in location_words)
                if not has_location:
                    location_violations.append({
                        "slide": i + 1,
                        "issue": "Click/Select without screen location (top, left, menu, etc.)"
                    })
        
        results["screen_location"] = {
            "rule": "Screen location specified for actions",
            "passed": len(location_violations) == 0,
            "violations": location_violations
        }
        
        # 3. Verification cues check
        verification_words = ['you will see', 'appears', 'shows', 'displayed', 'notice', 
                             'observe', 'visible', 'confirmation', 'result']
        verification_violations = []
        
        for i, slide in enumerate(slides):
            title = slide.get('title', '').lower()
            if any(x in title for x in ['title', 'learning', 'thank', 'summary', 'assignment', 'prerequisite', 'system']):
                continue
            
            narration = slide.get('narration', '').lower()
            has_verification = any(v in narration for v in verification_words)
            if not has_verification:
                verification_violations.append({
                    "slide": i + 1,
                    "issue": "No verification cue (You will see, appears, etc.)"
                })
        
        results["verification_cues"] = {
            "rule": "Verification cues present",
            "passed": len(verification_violations) <= len(slides) // 3,  # Allow some slides without
            "violations": verification_violations[:5]  # Limit to first 5
        }
        
    else:
        # Conceptual tutorial checks
        
        # 1. Smooth transitions check
        transition_words = ['now', 'next', 'let us', "let's", 'so', 'therefore', 'this means',
                          'in other words', 'for example', 'similarly', 'however', 'but']
        transition_count = 0
        
        for slide in slides:
            narration = slide.get('narration', '').lower()
            if any(t in narration for t in transition_words):
                transition_count += 1
        
        results["smooth_transitions"] = {
            "rule": "Uses transition words between ideas",
            "passed": transition_count >= len(slides) // 3,
            "violations": [] if transition_count >= len(slides) // 3 else [{
                "slide": 0,
                "issue": f"Only {transition_count} slides use transitions"
            }]
        }
        
        # 2. Analogies/examples check
        analogy_words = ['like', 'imagine', 'think of', 'similar to', 'just as', 'for example',
                        'consider', 'suppose', 'everyday', 'real-world', 'real world']
        analogy_count = 0
        
        for slide in slides:
            narration = slide.get('narration', '').lower()
            if any(a in narration for a in analogy_words):
                analogy_count += 1
        
        results["uses_analogies"] = {
            "rule": "Uses analogies and examples",
            "passed": analogy_count > 0,
            "violations": [] if analogy_count > 0 else [{
                "slide": 0,
                "issue": "No analogies or real-world examples found"
            }]
        }
        
        # 3. Engagement check (questions, prompts)
        engagement_words = ['?', 'notice', 'observe', 'think about', 'consider', 'why', 'how']
        engagement_count = 0
        
        for slide in slides:
            narration = slide.get('narration', '')
            if any(e in narration.lower() for e in engagement_words) or '?' in narration:
                engagement_count += 1
        
        results["learner_engagement"] = {
            "rule": "Engages learner (questions, prompts)",
            "passed": engagement_count > 0,
            "violations": [] if engagement_count > 0 else [{
                "slide": 0,
                "issue": "No questions or engagement prompts found"
            }]
        }
    
    return results


def _check_structure(slides: List[dict], json_script: dict) -> dict:
    """Check script structure rules."""
    results = {}
    
    if not slides:
        return {
            "title_slide": {"rule": "Title slide present", "passed": False, "violations": [{"slide": 0, "issue": "No slides found"}]},
            "lo_slide": {"rule": "Learning objectives slide", "passed": False, "violations": []},
            "thank_you_slide": {"rule": "Thank you slide", "passed": False, "violations": []}
        }
    
    slide_titles = [s.get('title', '').lower() for s in slides]
    
    # 1. Title slide
    has_title = any('title' in t or 'spoken tutorial' in t for t in slide_titles[:2])
    results["title_slide"] = {
        "rule": "Title slide present",
        "passed": has_title,
        "violations": [] if has_title else [{"slide": 1, "issue": "First slide should be title slide"}]
    }
    
    # 2. Learning objectives slide
    has_lo = any('learning' in t or 'objective' in t for t in slide_titles[:4])
    results["lo_slide"] = {
        "rule": "Learning objectives slide",
        "passed": has_lo,
        "violations": [] if has_lo else [{"slide": 2, "issue": "Missing learning objectives slide"}]
    }
    
    # 3. Thank you slide
    has_thank = any('thank' in t for t in slide_titles[-3:])
    results["thank_you_slide"] = {
        "rule": "Thank you slide",
        "passed": has_thank,
        "violations": [] if has_thank else [{"slide": len(slides), "issue": "Missing thank you slide at end"}]
    }
    
    # 4. Summary slide
    has_summary = any('summary' in t or 'summarize' in t or 'summarise' in t for t in slide_titles[-5:])
    results["summary_slide"] = {
        "rule": "Summary slide",
        "passed": has_summary,
        "violations": [] if has_summary else [{"slide": len(slides) - 1, "issue": "Missing summary slide"}]
    }
    
    return results


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences, handling common edge cases."""
    # Replace escaped newlines
    text = text.replace('\\n', '\n')
    
    # Split by newlines first (each line is likely a sentence)
    lines = text.split('\n')
    
    sentences = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # For lines without periods, treat as single sentence
        if '.' not in line:
            sentences.append(line)
        else:
            # Split by sentence-ending punctuation
            parts = re.split(r'(?<=[.!?])\s+', line)
            sentences.extend([p.strip() for p in parts if p.strip()])
    
    return sentences
