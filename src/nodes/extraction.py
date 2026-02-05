from src.core.state import VCAgentState
from src.nodes.extract_links import fetch_links
import requests
from bs4 import BeautifulSoup


def extract(url: str) -> dict:
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    extracted_data = {
        "outline_title": "",
        "outline_points": "",
        "duration": ""
    }

    # ---------- Extract Outline ----------
    outline_block = soup.find("pre", class_="custom-jumbotron")
    if outline_block:
        text = outline_block.get_text(separator="\n", strip=True)

        lines = [line.strip() for line in text.split("\n") if line.strip()]

        extracted_data["outline_title"] = lines[1]

        # Remaining lines → outline points
        points = ""
        for line in lines[2:]:
            # if not line.startswith("-"):
            points = points + ',' + line
        extracted_data["outline_points"] = points

    # ---------- Extract Video Metadata ----------
    metadata_table = soup.find("table", class_="table table-bordered table-hover")
    if metadata_table:
        # table_rows = metadata_table.find_all("tr")
        for row in metadata_table.find_all("tr")[1:]:
            cells = row.find_all(["th", "td"])
            if len(cells) == 4:
                # key = cells[0].get_text(strip=True).replace(":", "").lower()
                value = cells[1].get_text(strip=True)
                extracted_data["duration"] = value

    return extracted_data


def extract_tutorials(state: VCAgentState,foss: str, language: str) -> VCAgentState:
    url = state["legacy_raw_data"]
    links = fetch_links(foss,language)
    print (f"Tutorials found: {len(links)}")
    for i,link in enumerate(links):
        print (f"Extracting tutorial outline and information: {i+1}/{len(links)}")
        extracted_info = extract(link)

        tutorial_row = {
            "title": extracted_info["outline_title"],
            "duation": extracted_info["duration"],
            "subtopics": extracted_info["outline_points"]
        }

        state["structured_legacy"].append(tutorial_row)
    return state



