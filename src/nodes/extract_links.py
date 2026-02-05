import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
# from inputs import *

def fetch_links(tutorial: str, language: str) -> BeautifulSoup:
    BASE_URL = "https://spoken-tutorial.org"
    SEARCH_URL = "https://spoken-tutorial.org/tutorial-search/"

    params = {
        "search_foss": tutorial,     
        "search_language": language  
    }

    response = requests.get(SEARCH_URL, params=params, timeout=20)
    response.raise_for_status()
    links = []

    soup = BeautifulSoup(response.text, "html.parser")

    for record in soup.select("div.result-record"):
        a_tag = record.select_one("div.title a[href]")
        if a_tag:
            href = a_tag["href"]
            if href.startswith("/watch/"):
                links.append(urljoin(BASE_URL, href))

    return links


# links = fetch_links(foss_name, language)
# print ((links))



