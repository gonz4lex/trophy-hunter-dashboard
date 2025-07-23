"""
This module contains all the logic for fetching and parsing data
from the PSNProfiles website.
"""

import logging
from logging.handlers import RotatingFileHandler

from typing import Callable, List, Dict, Any
import time

import json
import random
import requests
from bs4 import BeautifulSoup

SCRAPE_DELAY_SECONDS = random.uniform(1.0, 2.5)
REQUEST_TIMEOUT_SECONDS = random.uniform(10, 15)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    stream_handler = logging.StreamHandler()
    file_handler = RotatingFileHandler(
        "./logs/scraper.log", maxBytes=1024 * 1024, backupCount=3
    )

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

# Parsing

def parse_profile_summary(html_content: str) -> Dict[str, Any]:
    """Parses the main profile page's HTML to extract summary stats."""
    soup = BeautifulSoup(html_content, "html.parser")
    profile_summary = {}

    # Use try/except in case the page structure changes
    try:
        user_bar = soup.find("div", id="user-bar")
        if user_bar:
            username_span = user_bar.find("span", class_="username")
            profile_summary["username"] = (
                username_span.text.strip() if username_span else "N/A"
            )

            avatar_div = user_bar.find("div", class_="avatar")
            if avatar_div:
                avatar_img = avatar_div.find("img")
                if avatar_img and avatar_img.has_attr('src'):
                    profile_summary["avatar_url"] = avatar_img['src']

            profile_summary["total_trophies"] = {}
            for t_type in ["total", "platinum", "gold", "silver", "bronze"]:
                el = user_bar.find("li", class_=t_type)
                if el:
                    profile_summary["total_trophies"][t_type] = int(
                        el.text.strip().replace(",", "")
                    )
        stats_div = soup.find("div", class_="stats")
        if stats_div:
            profile_summary["stats"] = {}
            for stat in stats_div.find_all("span", class_="stat"):
                value = stat.contents[0].strip().replace(",", "")
                label = stat.find("span").text.strip()
                profile_summary["stats"][label] = value
    except (AttributeError, TypeError, ValueError) as e:
        print(f"Error parsing summary: {e}")
        return {}  # Return an empty dict on failure

    return profile_summary


def parse_trophy_log_page(html_content: str) -> List[Dict[str, str]]:
    """Parses an HTML page from the trophy log to extract trophy data."""
    soup = BeautifulSoup(html_content, "html.parser")
    trophy_data = []
    trophy_table = soup.find("table", class_="zebra")
    if not trophy_table:
        return []

    for row in trophy_table.find_all("tr"):
        try:
            cells = row.find_all("td")
            if len(cells) < 10:
                continue

            game_img = cells[0].find("img")
            trophy_img = cells[1].find("img")
            title_anchor = cells[2].find("a", class_="title")
            date_span = cells[5].find("span", class_="typo-top-date")
            time_span = cells[5].find("span", class_="typo-bottom-date")
            rarity_span = cells[8].find("span", class_="typo-top")
            grade_img = cells[9].find("img")

            date_str = date_span.text.strip() if date_span else ""
            time_str = time_span.text.strip() if time_span else ""

            trophy = {
                "game": game_img["title"] if game_img else "N/A",
                "icon_url": trophy_img["src"] if trophy_img else "N/A",
                "title": title_anchor.text.strip() if title_anchor else "N/A",
                "timestamp": f"{date_str} {time_str}".strip(),
                "rarity_percent": rarity_span.text.strip() if rarity_span else "N/A",
                "grade": grade_img["title"] if grade_img else "N/A",
            }
            trophy_data.append(trophy)
        except (AttributeError, TypeError, KeyError) as e:
            print(f"Skipping a malformed row in trophy log: {e}")
            continue

    return trophy_data


# Scraping

def fetch_summary_data(
    session: requests.Session, base_url: str,
) -> Dict[str, Any]:
    """Fetches and parses only the summary data. Raises on network error."""
    try:
        summary_rs = session.get(base_url, timeout=15)
        summary_rs.raise_for_status()
        return parse_profile_summary(summary_rs.text)
    except requests.exceptions.RequestException as e:
        print(f"Network error fetching summary: {e}")
        raise


def fetch_full_trophy_log(
    session: requests.Session,
    base_url: str,
    progress_callback: Callable[[int, int], None],
    should_stop: Callable[[], bool],
) -> List[Dict[str, str]]:
    """
    Scrapes the entire trophy log, calling back with progress.
    It accepts a `should_stop` function to check if it should abort.
    """
    all_trophies = []
    page = 1

    start_time = time.time()
    logger.info(f"Starting full trophy log scrape for {base_url}...")
    session.headers.update({'Referer': base_url})

    while not should_stop():
        try:
            log_url = f"{base_url}/log?page={page}"
            log_rs = session.get(log_url, timeout=REQUEST_TIMEOUT_SECONDS)
            
            # If we get a 404, it's not an error, it's the end of the pages
            if log_rs.status_code == 404:
                break
            
            log_rs.raise_for_status()
            
            trophies_on_page = parse_trophy_log_page(log_rs.text)
            if not trophies_on_page:
                break
            
            all_trophies.extend(trophies_on_page)
            progress_callback(page, len(trophies_on_page))
            page += 1
            time.sleep(SCRAPE_DELAY_SECONDS)
            
        except requests.exceptions.RequestException as e:
            print(f"Network error on page {page}: {e}")
            raise

    end_time = time.time()
    duration = end_time - start_time
    
    # Create a structured log entry
    log_data = {
        "event": "scrape_complete",
        "profile_url": base_url,
        "duration_seconds": round(duration, 2),
        "pages_scraped": page - 1,
        "trophies_found": len(all_trophies),
    }

    logger.info(json.dumps(log_data))

    return all_trophies
