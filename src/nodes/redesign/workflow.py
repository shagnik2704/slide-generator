import os
import re
import logging
from src.nodes.redesign.utils.schema import SharedAgentState, TutorialData, TutorialState, OldTutorial, UpdatedTutorial, GenerateTutorialRequest, GenerateTutorialResponse
from src.nodes.redesign.extract_links import fetch_links
from src.nodes.redesign.extraction import extract_tutorials
from src.nodes.redesign.updates import tech_intelligence_agent
from src.nodes.redesign.split import duration_split
from src.nodes.redesign.tabulate import form_final_table
from src.nodes.redesign.gsheet import export_to_sheets

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

import requests

def update_progress(task_id: str | None, webhook_url: str | None, status: str, progress: int, message: str, stage: str, url: str | None = None):
    if not task_id:
        return
    payload = {
        "task_id": task_id,
        "status": status,
        "progress": progress,
        "message": message,
        "stage": stage,
        "url": url
    }
    logger.info(f"Task {task_id} [{stage}] - Progress: {progress}% - {message}")
    if webhook_url:
        try:
            res = requests.post(webhook_url, json=payload, timeout=5)
            res.raise_for_status()
        except Exception as e:
            logger.warning(f"Failed to post to webhook {webhook_url}: {e}")

def run_pipeline(request: GenerateTutorialRequest, task_id: str | None = None, webhook_url: str | None = None) -> GenerateTutorialResponse:
    try:
        # Initial status
        update_progress(task_id, webhook_url, "processing", 5, "Initializing workspace...", "init")
        
        # Initialize TutorialData
        foss_name = request.foss_name
        language = request.language
        data = TutorialData(foss_name=foss_name, language=language, links=[])
        
        # Define output CSV path
        safe_foss = re.sub(r'[^a-zA-Z0-9_\-]', '_', foss_name)
        os.makedirs("results", exist_ok=True)
        output_csv_path = os.path.join("results", f"{safe_foss}_{language}_final.csv")
        
        # Clean output CSV if it already exists
        if os.path.exists(output_csv_path):
            try:
                os.remove(output_csv_path)
            except OSError:
                pass
                
        # Initialize SharedAgentState
        state = SharedAgentState(
            data=data,
            output_csv_path=output_csv_path,
            tutorial=None
        )
        
        # 1. Fetch links
        update_progress(task_id, webhook_url, "processing", 10, "Fetching tutorial links from Spoken Tutorial website...", "fetch_links")
        state.data = fetch_links(state.data)
        
        # Check if any tutorials were found
        if not state.data.links:
            raise ValueError(
                f"No tutorials found for '{foss_name}' in '{language}'. "
                f"This FOSS might not be available in the selected language."
            )
        
        num_links = len(state.data.links)
        update_progress(task_id, webhook_url, "processing", 20, f"Found {num_links} tutorials. Starting content redesign...", "analysis_start")
        
        # 2. Iterate over links
        new_t_counter = 1
        for idx, link in enumerate(state.data.links, start=1):
            # Calculate progress bounds for this iteration
            tut_start_progress = 20 + int((idx - 1) * 70 / num_links)
            tut_end_progress = 20 + int(idx * 70 / num_links)
            step_delta = max(1, (tut_end_progress - tut_start_progress) // 4)
            
            # Initialize TutorialState for this loop iteration
            state.tutorial = TutorialState(
                tutorial_name=link.name,
                tutorial_link=link.url,
                old_tutorial=OldTutorial(),
                updated_tutorial=UpdatedTutorial(),
                splited_tutorial=[]
            )
            
            # Run stages
            logger.info(f"Running extraction stage for {state.tutorial.tutorial_name}")
            update_progress(
                task_id, webhook_url, "processing", 
                tut_start_progress, 
                f"[{idx}/{num_links}] Extracting contents from: {state.tutorial.tutorial_name}", 
                "extraction"
            )
            state.tutorial = extract_tutorials(state.tutorial)
            
            logger.info(f"Running tech intelligence stage for {state.tutorial.tutorial_name}")
            update_progress(
                task_id, webhook_url, "processing", 
                tut_start_progress + step_delta, 
                f"[{idx}/{num_links}] Running tech intelligence agent for: {state.tutorial.tutorial_name}", 
                "tech_intelligence"
            )
            state.tutorial = tech_intelligence_agent(state.tutorial)
            
            logger.info(f"Running duration split stage for {state.tutorial.tutorial_name}")
            update_progress(
                task_id, webhook_url, "processing", 
                tut_start_progress + 2 * step_delta, 
                f"[{idx}/{num_links}] Splitting tutorial: {state.tutorial.tutorial_name}", 
                "duration_split"
            )
            state.tutorial = duration_split(state.tutorial)
            
            logger.info(f"Running tabulate stage for {state.tutorial.tutorial_name}")
            update_progress(
                task_id, webhook_url, "processing", 
                tut_start_progress + 3 * step_delta, 
                f"[{idx}/{num_links}] Saving table results for: {state.tutorial.tutorial_name}", 
                "tabulation"
            )
            state.tutorial, new_t_counter = form_final_table(
                state.tutorial, 
                output_csv_path=state.output_csv_path, 
                tutorial_index=idx,
                start_new_t_index=new_t_counter
            )

        # 3. Export worksheet
        update_progress(task_id, webhook_url, "processing", 90, "Exporting results to Google Sheets...", "export")
        export_url = "Export flag disabled."
        if request.export:
            export_url = export_to_sheets(state=state, user_emails=request.reciept_emails, user_role=request.reciept_role)
            update_progress(task_id, webhook_url, "completed", 100, "Tutorial redesign completed successfully!", "completed", url=export_url)
            return GenerateTutorialResponse(status="success", url=export_url)
        
        update_progress(task_id, webhook_url, "completed", 100, "Tutorial redesign completed (Export disabled).", "completed", url="Export flag disabled. No Google Sheet created.")
        return GenerateTutorialResponse(status="success", url="Export flag disabled. No Google Sheet created.")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in redesign pipeline: {error_msg}", exc_info=True)
        update_progress(task_id, webhook_url, "failed", 100, f"Error: {error_msg}", "failed")
        return GenerateTutorialResponse(status="error", url=error_msg)

