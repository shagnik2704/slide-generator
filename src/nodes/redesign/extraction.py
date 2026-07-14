from src.nodes.redesign.utils.schema import TutorialState, OldTutorial
from src.nodes.redesign.extract_links import fetch_links
import requests
from bs4 import BeautifulSoup
from datetime import datetime


def extract(url: str) -> OldTutorial:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    extracted_data = OldTutorial()

    # ---------- Extract Outline ----------
    outline_block = soup.find("pre", class_="custom-jumbotron")
    if outline_block:
        text = outline_block.get_text(separator="\n", strip=True)

        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # extracted_data["outline_title"] = lines[1]

        # Remaining lines → outline points
        points = ""
        for line in lines[2:]:
            # if not line.startswith("-"):
            points = points + ',' + line
        extracted_data.outline = points

    # ---------- Extract Video Metadata ----------
    metadata_table = soup.find("table", class_="table table-bordered table-hover")
    if metadata_table:
        # table_rows = metadata_table.find_all("tr")
        for row in metadata_table.find_all("tr")[1:]:
            cells = row.find_all(["th", "td"])
            if len(cells) == 4:
                # key = cells[0].get_text(strip=True).replace(":", "").lower()
                value = cells[1].get_text(strip=True)
                delta = datetime.strptime(value, "%H:%M:%S") - datetime.strptime("00:00:00", "%H:%M:%S")
                total_seconds = float(delta.total_seconds())
                extracted_data.duration = total_seconds

    return extracted_data


def extract_tutorials(state: TutorialState) -> TutorialState:
    link = state.tutorial_link
    extracted_info = extract(link)
    state.old_tutorial = extracted_info
    return state


def extract_tutorials(state: VCAgentState, foss: str, language: str) -> VCAgentState:
    """Synchronous wrapper for extract_tutorials_async."""
    return asyncio.run(extract_tutorials_async(state, foss, language))



