from src.core.state import VCAgentState
from src.nodes.extract_links import fetch_links
from src.utils.VC_utils import SEMAPHORE_CONFIG
import aiohttp
from bs4 import BeautifulSoup
import asyncio
from typing import List, Dict


async def extract(url: str) -> dict:
    """Asynchronously extract tutorial information from URL."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()
            html = await response.text()
    
    soup = BeautifulSoup(html, "html.parser")

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


async def _extract_single(semaphore: asyncio.Semaphore, index: int, total: int, link: str) -> Dict:
    """Extract a single tutorial with semaphore control."""
    async with semaphore:
        print(f"Extracting tutorial outline and information: {index+1}/{total}")
        extracted_info = await extract(link)
        return {
            "title": extracted_info["outline_title"],
            "duation": extracted_info["duration"],
            "subtopics": extracted_info["outline_points"]
        }


async def extract_tutorials_async(state: VCAgentState, foss: str, language: str, semaphore_limit: int = None) -> VCAgentState:
    """Extract tutorials concurrently with semaphore limit."""
    if semaphore_limit is None:
        semaphore_limit = SEMAPHORE_CONFIG["extraction"]
    
    url = state["legacy_raw_data"]
    links = fetch_links(foss, language)
    print(f"Tutorials found: {len(links)}")
    print(f"Using extraction semaphore limit: {semaphore_limit}")
    
    semaphore = asyncio.Semaphore(semaphore_limit)
    tasks = [
        _extract_single(semaphore, i, len(links), link)
        for i, link in enumerate(links)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if isinstance(result, Exception):
            print(f"Error during extraction: {result}")
        else:
            state["structured_legacy"].append(result)
    
    return state


def extract_tutorials(state: VCAgentState, foss: str, language: str) -> VCAgentState:
    """Synchronous wrapper for extract_tutorials_async."""
    return asyncio.run(extract_tutorials_async(state, foss, language))



