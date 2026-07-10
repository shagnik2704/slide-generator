import os
import re
from src.nodes.redesign.utils.schema import SharedAgentState, TutorialData, TutorialState, OldTutorial, UpdatedTutorial, GenerateTutorialRequest, GenerateTutorialResponse
from src.nodes.redesign.extract_links import fetch_links
from src.nodes.redesign.extraction import extract_tutorials
from src.nodes.redesign.updates import tech_intelligence_agent
from src.nodes.redesign.split import duration_split
from src.nodes.redesign.tabulate import form_final_table
from src.nodes.redesign.gsheet import export_to_sheets


def run_pipeline(request: GenerateTutorialRequest) -> GenerateTutorialResponse:
    try:
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
        state.data = fetch_links(state.data)
        
        # Check if any tutorials were found
        if not state.data.links:
            raise ValueError(
                f"No tutorials found for '{foss_name}' in '{language}'. "
                f"This FOSS might not be available in the selected language."
            )
        
        # 2. Iterate over links
        for idx, link in enumerate(state.data.links, start=1):
            # Initialize TutorialState for this loop iteration
            state.tutorial = TutorialState(
                tutorial_name=link.name,
                tutorial_link=link.url,
                old_tutorial=OldTutorial(),
                updated_tutorial=UpdatedTutorial(),
                splited_tutorial=[]
            )
            
            # Run stages
            state.tutorial = extract_tutorials(state.tutorial)
            state.tutorial = tech_intelligence_agent(state.tutorial)
            state.tutorial = duration_split(state.tutorial)
            state.tutorial = form_final_table(state.tutorial, output_csv_path=state.output_csv_path, tutorial_index=idx)

        # 3. Export worksheet
        export_url = "Export flag disabled."
        if request.export:
            export_url = export_to_sheets(state=state, receipt_emails=request.reciept_emails, receipt_role=request.reciept_role)
            return GenerateTutorialResponse(status="success", url=export_url)
        
        return GenerateTutorialResponse(status="success", url="Export flag disabled. No Google Sheet created.")
    
    except Exception as e:
        return GenerateTutorialResponse(status="error", url=str(e))

