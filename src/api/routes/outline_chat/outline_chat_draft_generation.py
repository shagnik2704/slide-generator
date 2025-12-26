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

| Tutorial | Prerequisites | Topics Details | Time (range) | Comments |
|----------|--------------|---------------|-------------|----------|
"""
    for tutorial in outline_data.get('tutorial_rows', []):
        topics = '; '.join(tutorial.get('topics_details', []))
        # Handle prerequisites as list or string (for backward compatibility)
        prerequisites_data = tutorial.get('prerequisites', [])
        if isinstance(prerequisites_data, list):
            prerequisites = '; '.join(prerequisites_data) if prerequisites_data else 'N/A'
        else:
            prerequisites = prerequisites_data if prerequisites_data else 'N/A'
        
        # Display time as range if available, otherwise use time_seconds
        time_range = tutorial.get('time_range')
        if time_range:
            min_minutes = time_range.get('min_seconds', 0) // 60
            max_minutes = time_range.get('max_seconds', 0) // 60
            if min_minutes == max_minutes:
                time_display = f"{min_minutes} min"
            else:
                time_display = f"{min_minutes}-{max_minutes} min"
        else:
            # Fallback to time_seconds for backward compatibility
            time_seconds = tutorial.get('time_seconds', 0)
            time_display = f"{time_seconds // 60} min" if time_seconds > 0 else "0 min"
        
        draft += f"| {tutorial.get('title', 'N/A')} | {prerequisites} | {topics} | {time_display} | {tutorial.get('comments', '')} |\n"
    
    draft += f"""
## Metadata
- **Prepared By:** {outline_data.get('prepared_by', 'N/A')}
- **Reviewer:** {outline_data.get('reviewer', 'IITB ST Team')}
- **Date:** {outline_data.get('date', 'N/A')}
- **Keywords:** {'; '.join(outline_data.get('keywords', []))}
"""
    return draft

