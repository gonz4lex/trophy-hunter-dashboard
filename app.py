"""
This is the main Streamlit application for the PSNProfiles Dashboard.
It handles the user interface, caching, and calls the scraper module.
"""

import streamlit as st
import pandas as pd
import time
import math
import cloudscraper
import requests
from typing import Dict, Any

from core.cache import load_from_cache, save_to_cache
from core.scraper import fetch_summary_data, fetch_full_trophy_log
from components.visualizations import (
    display_header,
    display_summary,
    display_showcase_tab,
    display_timeline_tab,
    display_deep_dive_tab,
    display_milestones,
    display_raw_data,

)
from components.utils import render_sidebar


def main():
    """Main function to run the Streamlit application."""
    st.set_page_config(page_title="Trophy Hunter Dashboard", layout="wide")

    # Initialize session state
    if "profile_data" not in st.session_state:
        st.session_state.profile_data = None
    if "username_to_search" not in st.session_state:
        st.session_state.username_to_search = ""
    if "scraping_in_progress" not in st.session_state:
        st.session_state.scraping_in_progress = False

    # Sidebar
    render_sidebar()

    # Main
    if st.session_state.username_to_search:
        username = st.session_state.username_to_search

        # Start of a new scrape
        if (
            st.session_state.profile_data is None
            and st.session_state.scraping_in_progress
        ):
            run_scraper(username)

        # Displaying the final data
        elif st.session_state.profile_data:
            summary_data = st.session_state.profile_data.get("profile_summary")
            trophy_log_data = st.session_state.profile_data.get("trophy_log")

            df = pd.DataFrame(trophy_log_data) if trophy_log_data else pd.DataFrame()

            display_header(username, summary_data["avatar_url"])

            display_summary(summary_data)

            showcase, timeline, deep_dive, milestones, raw_data = st.tabs(
                ["Showcase", "Timeline", "Deep Dive", "Milestones", "Raw Data",]
            )

            with showcase:
                display_showcase_tab(df)

            with timeline:
                display_timeline_tab(df)

            with deep_dive:
                display_deep_dive_tab(df)

            with milestones:
                display_milestones(df)

            with raw_data:
                # TODO: filters, timeline, etc...
                display_raw_data(df)



def run_scraper(username: str):
    """Handles the entire scraping and UI update process."""
    st.header(f"Analysis for: `{username}`")

    cached_data = load_from_cache(username)
    if cached_data:
        st.success("Loaded full profile data from cache!")
        st.session_state.profile_data = cached_data
        st.session_state.scraping_in_progress = False
        st.rerun()
        return

    try:
        session = cloudscraper.create_scraper()
        base_url = f"https://psnprofiles.com/{username}"
        session.headers.update({'User-Agent': 'TrophyHunter/1.0 (hello@alexgonzalezc.dev)'})

        summary_data = fetch_summary_data(session, base_url)

        if not summary_data.get("total_trophies"):
            st.error(
                f"Could not find profile for '{username}'. Please check the username and try again."
            )
            st.session_state.scraping_in_progress = False
            return

        st.session_state.profile_data = {
            "profile_summary": summary_data,
            "trophy_log": [],
        }
        display_summary(summary_data)

        total_trophies = summary_data["total_trophies"].get("total", 0)
        total_pages = math.ceil(total_trophies / 50)

        st.info("Full profile not in cache. Fetching complete trophy log...")
        st.write(f"Estimated pages to fetch: **{total_pages}**")
        progress_bar = st.progress(0)
        progress_text = st.empty()

        def progress_callback(page_num, _):
            progress = min(1.0, page_num / total_pages if total_pages > 0 else 1)
            progress_bar.progress(progress)
            progress_text.text(f"Scraping page {page_num} of ~{total_pages}...")

        should_stop_scraping = lambda: not st.session_state.get("scraping_in_progress")

        trophy_log = fetch_full_trophy_log(
            session=session,
            base_url=base_url,
            progress_callback=progress_callback,
            should_stop=should_stop_scraping,
        )

        st.session_state.profile_data["trophy_log"] = trophy_log
        save_to_cache(username, st.session_state.profile_data)

        if not st.session_state.get("scraping_in_progress"):
            progress_text.warning("Scraping was stopped. Displaying partial results.")
        else:
            progress_text.success("Successfully scraped and cached full profile!")

        st.session_state.scraping_in_progress = False
        time.sleep(2)
        st.rerun()

    except requests.exceptions.RequestException as e:
        st.error(
            f"A network error occurred. The profile may be private or the username incorrect. (Error: {e})"
        )
        st.session_state.scraping_in_progress = False
        st.rerun()


if __name__ == "__main__":
    main()
