from src.core.state import VCAgentState
from src.nodes.extraction import extract_tutorials_async
from src.nodes.updates import tech_intelligence_agent_async
from src.nodes.split import duration_split_async
from src.nodes.tabulate import form_final_table
from src.nodes.gsheet import export_to_sheets
import json
import asyncio
from typing import List


def _log(data, filename):
    with open(f"logs/{filename}", "w") as f:
        json.dump(data, f, indent=4)


async def run_pipeline(foss_name: str, language: str, export: bool, reciept_emails: list, reciept_role: str, semaphore_limit: int = 3):
    """Run the redesign pipeline with concurrent processing.
    
    Args:
        foss_name: Name of the FOSS software
        language: Language code for tutorials
        export: Whether to export to Google Sheets
        reciept_emails: Email addresses for sharing
        reciept_role: Role for recipients
        semaphore_limit: Concurrency limit for extraction, update, and split (default: 3)
        
    Returns:
        Tuple of (state, export_url)
    """
    URL = f"https://spoken-tutorial.org/tutorial-search/?serch_FOSS={foss_name}&search_language={language}"

    state: VCAgentState = {
        "legacy_raw_data": URL,
        "structured_legacy": [],
        "tech_updates": [],
        "final_table": []
    }

    # Extract tutorials concurrently (up to 3 at a time)
    state = await extract_tutorials_async(state, foss_name, language, semaphore_limit)
    
    # Check if any tutorials were found
    tutorials_found = len(state.get("structured_legacy", []))
    if tutorials_found == 0:
        raise ValueError(
            f"No tutorials found for '{foss_name}' in '{language}'. "
            f"This FOSS might not be available in the selected language."
        )
    
    # _log(state, "extraction_output.json")

    # Update tutorials concurrently (up to 3 at a time)
    state = await tech_intelligence_agent_async(state, semaphore_limit)
    # _log(state, "updation_output.json")

    # Split tutorials concurrently (up to 3 at a time)
    state = await duration_split_async(state, semaphore_limit)
    # _log(state, "split_output.json")

    # Form final table (sequential operation)
    state = form_final_table(state)
    # _log(state, "final_output.json")

    export_url = "Export flag disabled."

    if export:
        export_url = export_to_sheets(state, foss_name, language, reciept_emails, reciept_role)

    return state, export_url