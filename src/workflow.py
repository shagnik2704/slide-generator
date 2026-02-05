from src.core.state import VCAgentState
from src.nodes.extraction import extract_tutorials
from src.nodes.updates import tech_intelligence_agent
from src.nodes.split import duration_split
from src.nodes.tabulate import form_final_table
from src.nodes.gsheet import export_to_sheets
import json
from typing import List


def _log(data, filename):
    with open(f"logs/{filename}", "w") as f:
        json.dump(data, f, indent=4)


def run_pipeline(foss_name: str, language: str, export: bool, reciept_emails: list, reciept_role: str):
    URL = f"https://spoken-tutorial.org/tutorial-search/?serch_FOSS={foss_name}&search_language={language}"

    state: VCAgentState = {
        "legacy_raw_data": URL,
        "structured_legacy": [],
        "tech_updates": [],
        "final_table": []
    }

    state = extract_tutorials(state, foss_name, language)
    
    # Check if any tutorials were found
    tutorials_found = len(state.get("structured_legacy", []))
    if tutorials_found == 0:
        raise ValueError(
            f"No tutorials found for '{foss_name}' in '{language}'. "
            f"This FOSS might not be available in the selected language."
        )
    
    # _log(state, "extraction_output.json")

    state = tech_intelligence_agent(state)
    # _log(state, "updation_output.json")

    state = duration_split(state)
    # _log(state, "split_output.json")

    state = form_final_table(state)
    # _log(state, "final_output.json")

    export_url = "Export flag disabled."

    if export:
        export_url = export_to_sheets(state, foss_name, language, reciept_emails, reciept_role)

    return state, export_url