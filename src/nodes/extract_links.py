import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
# from inputs import *

def fetch_links(tutorial: str, language: str) -> list:
    BASE_URL = "https://spoken-tutorial.org"
    SEARCH_URL = "https://spoken-tutorial.org/tutorial-search/"

    params = {
        "search_foss": tutorial,     
        "search_language": language  
    }

    all_links = []
    current_page = 1

    while True:
        # Add page parameter for pages after the first
        if current_page > 1:
            params["page"] = current_page

        print(f"Fetching page {current_page}...")
        response = requests.get(SEARCH_URL, params=params, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract links from current page
        page_links = []
        for record in soup.select("div.result-record"):
            a_tag = record.select_one("div.title a[href]")
            if a_tag:
                href = a_tag["href"]
                if href.startswith("/watch/"):
                    page_links.append(urljoin(BASE_URL, href))

        print(f"Found {len(page_links)} links on page {current_page}")
        
        # If no links found on this page, we've reached the end
        if not page_links:
            print("No more links found, stopping.")
            break

        all_links.extend(page_links)

        # Check for pagination - look for "Next" link or button
        has_next = False
        
        # Check if there's an active/enabled "Next" button
        # Look for the li containing the Next button and check if it's not disabled
        pagination = soup.select("ul.pagination li")
        for li in pagination:
            link = li.select_one("a")
            if link:
                link_text = link.get_text().strip()
                # Check if this is a Next button and the parent li is not disabled
                if "Next" in link_text or "»" in link_text or "next" in link_text:
                    # Check if the parent li has class 'disabled' or 'active'
                    if 'disabled' not in li.get('class', []):
                        has_next = True
                    break

        if not has_next:
            print("No 'Next' button found or Next button is disabled, reached last page.")
            break

        current_page += 1

    print(f"Total links extracted: {len(all_links)}")
    return all_links


# links = fetch_links(foss_name, language)
# print ((links))



