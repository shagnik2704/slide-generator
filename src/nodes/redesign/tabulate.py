from src.nodes.redesign.utils.schema import TutorialState
import pandas as pd
# from inputs import foss_name,language
import re


def empty_row():
    """Returns a blank row following the strict schema."""
    return {
        "Old T#": "",
        "Old Tutorial Title": "",
        "Old Subtopics": "",
        "Old Duration": "",
        "Logs": "",
        "New T#": "",
        "New Title": "",
        "New Subtopics": "",
        "New Tutorial Duration": ""
    }


def form_final_table(state: TutorialState, output_csv_path: str = None, tutorial_index: int = 1):
    table = []
    
    # 1. Old tutorial info
    old_title = state.tutorial_name
    
    # Clean up old subtopics/outline: strip, replace '-' with '', remove leading comma
    old_subtopics = state.old_tutorial.outline or ""
    if old_subtopics.startswith(','):
        old_subtopics = old_subtopics[1:]
    old_subtopics = old_subtopics.replace('-', '')
    
    # Format old duration if float (seconds) to HH:MM:SS
    old_duration = state.old_tutorial.duration
    import time
    if isinstance(old_duration, (int, float)):
        old_duration_str = time.strftime('%H:%M:%S', time.gmtime(old_duration))
    else:
        old_duration_str = str(old_duration) if old_duration is not None else ""

    # 2. Logs
    logs = []
    if state.updated_tutorial and state.updated_tutorial.logs:
        logs = state.updated_tutorial.logs
        if isinstance(logs, str):
            logs = logs.splitlines()

    # 3. New (split) tutorials
    updated_items = []
    if state.splited_tutorial:
        if isinstance(state.splited_tutorial, list):
            updated_items = state.splited_tutorial
        else:
            updated_items = [state.splited_tutorial]

    # Calculate max length to align logs and new/split tutorials
    max_len = max(len(updated_items), len(logs))

    new_t_counter = 1
    for j in range(max_len):
        row = empty_row()

        # Fill OLD columns only for the first row of this tutorial
        if j == 0:
            row["Old T#"] = f"Old T{tutorial_index}"
            row["Old Tutorial Title"] = old_title
            row["Old Subtopics"] = old_subtopics
            row["Old Duration"] = old_duration_str
            
        # Fill LOGS if available
        if j < len(logs):
            row["Logs"] = logs[j]

        # Fill NEW tutorial data if available
        if j < len(updated_items):
            item = updated_items[j]
            # Handle if Pydantic model or dict
            if isinstance(item, dict):
                title = item.get("tutorial_title", "")
                subtopic = item.get("subtopic", "")
                duration = item.get("estimated_duration", "")
            else:
                title = getattr(item, "tutorial_title", "")
                subtopic = getattr(item, "subtopic", "")
                duration = getattr(item, "estimated_duration", "")
                
            row["New T#"] = f"New T{new_t_counter}"
            row["New Title"] = title
            row["New Subtopics"] = subtopic
            row["New Tutorial Duration"] = str(duration)
            new_t_counter += 1

        table.append(row)

    # 4. Save locally in csv file
    import os
    df = pd.DataFrame(table)
    
    if output_csv_path:
        # Append to the combined CSV file
        os.makedirs(os.path.dirname(output_csv_path) or ".", exist_ok=True)
        header = not os.path.exists(output_csv_path)
        df.to_csv(output_csv_path, mode='a', index=False, header=header)
        print(f"Appended final table to {output_csv_path}")
    else:
        # Sanitize the tutorial name for use in filesystem path
        safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', old_title)
        os.makedirs("work_dir", exist_ok=True)
        csv_path = os.path.join("work_dir", f"temp_{safe_name}.csv")
        df.to_csv(csv_path, index=False)
        print(f"Saved final table to {csv_path}")

    # Return state
    return state

