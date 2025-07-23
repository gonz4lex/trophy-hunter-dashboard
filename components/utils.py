import re
from datetime import datetime

import streamlit as st

def render_sidebar_footer():
    """
    A reusable component to create a footer in the sidebar,
    anchored to the bottom.
    """
    st.markdown(
        """
        <style>
            .sidebar-footer {
                position: fixed;
                bottom: 10px;
                width: 280px; /* TODO: Adjust this width to match sidebar */
            }
        </style>

        <div class="sidebar-footer">
            <details>
                <summary>About</summary>
                <p>
                The Trophy Hunter Dashboard gathers data by (respectfully) scraping your public <a href="http://psnprofiles.com/" target="_blank">PSNProfiles</a> trophy log. Results are cached 24 hours.
                <br><br>
                </p>
            </details>
            <a href="https://github.com/gonz4lex/trophy-hunter-dashboard" target="_blank">View on GitHub</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar():
    """
    A reusable function to create the sidebar content for all pages.
    """

    with st.sidebar:
        st.title("🏆 Trophy Hunter Dashboard")
        username_input = st.text_input(
            "Enter PSN Username", placeholder="Username", key="username_input_key"
        )
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Analyze Profile", key="analyze_btn"):
                st.session_state.username_to_search = username_input
                st.session_state.profile_data = None
                st.session_state.scraping_in_progress = True
                st.rerun()

        with col2:
            if st.session_state.get("scraping_in_progress"):
                if st.button("Stop", key="stop_btn", type="primary"):
                    st.session_state.scraping_in_progress = False
                    st.warning("Scraping stopped.")
                    st.rerun()

        render_sidebar_footer()


def parse_custom_timestamp(timestamp_str):
        cleaned = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", timestamp_str)
        return datetime.strptime(cleaned, "%d %b %Y %I:%M:%S %p")