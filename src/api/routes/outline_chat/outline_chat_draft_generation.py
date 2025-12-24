"""Draft generation for outline chat."""
from typing import Dict


def generate_draft_outline(outline_data: Dict) -> str:
    """Generate a human-readable draft outline for review."""
    draft = f"""# Course Outline Draft

## Tutorial Information
- **Course Outline Name:** {outline_data.get('outline_name', 'N/A')}
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
- **Allied Examples:** {'; '.join(outline_data.get('allied_examples', [])) or 'None'}

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
- **Keywords:** {'; '.join(outline_data.get('keywords', []))}
"""
    return draft

