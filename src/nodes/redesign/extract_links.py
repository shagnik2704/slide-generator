import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pandas as pd
from src.nodes.redesign.utils.schema import TutorialData, Link

def fetch_links(request: TutorialData) -> TutorialData:
    BASE_URL = "https://spoken-tutorial.org"
    SEARCH_URL = "https://spoken-tutorial.org/tutorial-search/"

    params = {
        "search_foss": request.foss_name,     
        "search_language": request.language  
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(SEARCH_URL, params=params, headers=headers, timeout=20)
    response.raise_for_status()
    links = []
    names = []

    soup = BeautifulSoup(response.text, "html.parser")

    for record in soup.select("div.result-record"):
        a_tag = record.select_one("div.title a[href]")
        if a_tag:
            href = a_tag["href"]
            if href.startswith("/watch/"):
                names.append(a_tag.get_text(strip=True))
                links.append(urljoin(BASE_URL, href))

    request.links = [Link(name=name, url=url) for name, url in zip(names, links)]

    return request


# links = fetch_links(foss_name, language)
# print ((links))



