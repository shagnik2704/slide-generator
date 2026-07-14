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


async def run_pipeline(foss_name: str, language: str, export: bool, reciept_emails: list, reciept_role: str):
    """Run the redesign pipeline with optimized concurrent processing.
    
    Uses stage-specific semaphore limits from SEMAPHORE_CONFIG:
    - Extraction: 8 concurrent operations (I/O bound)
    - Update: 2 concurrent operations (LLM rate-limited)
    - Split: 4 concurrent operations (Moderate LLM usage)
    
    Args:
        foss_name: Name of the FOSS software
        language: Language code for tutorials
        export: Whether to export to Google Sheets
        reciept_emails: Email addresses for sharing
        reciept_role: Role for recipients
        
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

    # Extract tutorials concurrently (up to 8 at a time - I/O bound)
    state = await extract_tutorials_async(state, foss_name, language)
    
    # Check if any tutorials were found
    tutorials_found = len(state.get("structured_legacy", []))
    if tutorials_found == 0:
        raise ValueError(
            f"No tutorials found for '{foss_name}' in '{language}'. "
            f"This FOSS might not be available in the selected language."
        )
    
    # _log(state, "extraction_output.json")

    # Update tutorials concurrently (up to 2 at a time - rate-limited)
    state = await tech_intelligence_agent_async(state)
    # _log(state, "updation_output.json")

    # Split tutorials concurrently (up to 4 at a time - moderate LLM)
    state = await duration_split_async(state)
    # _log(state, "split_output.json")

    # Form final table (sequential operation)
    state = form_final_table(state)
    # _log(state, "final_output.json")

    export_url = "Export flag disabled."

    if export:
        export_url = export_to_sheets(state, foss_name, language, reciept_emails, reciept_role)

    return state, export_url