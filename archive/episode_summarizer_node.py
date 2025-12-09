"""
Episode Summarizer Node - Extracts key information from completed episodes for series continuity.

After a script passes evaluation, this node extracts:
- Episode title and number
- Key terms introduced
- Main concepts covered
- Brief summary for cross-referencing in future episodes

This information is stored in the checkpointer via the state.
"""

from models.state import AgentState


def summarize_episode(state: AgentState):
    """Extracts a summary of the current episode for series memory."""
    print("📝 Summarizing episode for series memory...")
    
    json_script = state.get('json_script', {})
    extracted_content = state.get('extracted_content', {})
    episode_number = state.get('episode_number', 'unknown')
    
    if not json_script:
        print("⚠️ No script to summarize")
        return {"episode_summary": None}
    
    # Extract key information from the completed script
    episode_summary = {
        "episode_number": episode_number,
        "title": json_script.get('presentation_title', 'Untitled'),
        "learning_objectives": json_script.get('learning_objectives', []),
        "key_terms": extracted_content.get('key_terms', []),
        "core_concepts": extracted_content.get('core_concepts', []),
        # Extract first few words of each slide's narration for quick reference
        "topics_covered": [
            slide.get('title', '') 
            for slide in json_script.get('slides', [])
            if slide.get('title') and slide.get('title') not in ['Welcome', 'Thank You', 'Summary', 'Assignment']
        ][:5],  # Top 5 content topics
        "prerequisites": json_script.get('prerequisites', ''),
        "duration": json_script.get('duration', ''),
    }
    
    print(f"✓ Episode summary created: {episode_summary['title']}")
    print(f"  Key terms: {episode_summary['key_terms']}")
    print(f"  Topics: {episode_summary['topics_covered']}")
    
    # Build the previous_episodes list
    previous_episodes = state.get('previous_episodes', []) or []
    
    # Add current episode to the history
    updated_previous_episodes = previous_episodes + [episode_summary]
    
    return {
        "episode_summary": episode_summary,
        "previous_episodes": updated_previous_episodes
    }
