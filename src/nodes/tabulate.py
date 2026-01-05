import pandas as pd
from state import AgentState
from inputs import foss_name,language
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


def form_final_table(state: AgentState):
    table = []
    new_t_counter = 1

    for i, legacy in enumerate(state["structured_legacy"]):
        row=empty_row()
        table.append(row)        
        tech = state["tech_updates"][i]

        old_t_id = f"Old T{i + 1}"
        old_title = legacy["title"]
        old_subtopics = legacy["subtopics"][1:].replace('-','')
        old_duration = legacy["duation"]

        updated = tech.get("updated_subtopics", [])
        logs = tech.get("logs")
        if isinstance(logs,str):
            logs = logs.splitlines()
            # logs = re.split('(?<=\\D)(?=\\d)|(?<=\\d)(?=\\D)', logs)
            # split_pattern = r"(?=\s*\d+[a-zA-Z]?\.)"
            # result = re.split(split_pattern, logs)
            # logs =  [item.strip() for item in result if item.strip()]
            

        max_len = max(len(updated), len(logs))

        for j in range(max_len):
            row = empty_row()

            # Fill OLD columns only for first row of this tutorial
            if j == 0:
                row["Old T#"] = old_t_id
                row["Old Tutorial Title"] = old_title
                row["Old Subtopics"] = old_subtopics
                row["Old Duration"] = old_duration
                
            # Fill LOGS if available
            if j < len(logs):
                row["Logs"] = logs[j]

            # Fill NEW tutorial data if available
            if j < len(updated):
                row["New T#"] = f"New T{new_t_counter}"
                row["New Title"] = updated[j]["tutorial_title"]
                row["New Subtopics"] = updated[j]["subtopic"]
                row["New Tutorial Duration"] = updated[j]["estimated_duration"]
                new_t_counter += 1

            table.append(row)

    # Export for inspection
    # df = pd.DataFrame(table)
    # df.to_csv(f"results/temp_{foss_name}_{language}.csv", index=False)

    state['final_table'] = table
    return state
