"""
This module contains all functions related to displaying data
and visualizations in the Streamlit app.
"""

from typing import List, Dict, Any
from datetime import datetime

import streamlit as st
import pandas as pd
import numpy as np

import plotly.express as px
import plotly.graph_objects as go

from components.utils import parse_custom_timestamp


def display_header(username: str, avatar_url: str):
    c1, c2 = st.columns([0.05, 0.95])

    with c1:
        st.image(avatar_url)
    with c2:
        st.header(f"{username}")


# Showcase


def display_summary(summary: Dict[str, Any]):
    """Displays the profile summary metrics."""
    if summary and summary.get("total_trophies"):
        st.subheader("Profile Summary")
        trophies = summary["total_trophies"]
        cols = st.columns(5)
        cols[0].metric("🏆 Total Trophies", f"{trophies.get('total', 0):,}")
        cols[1].metric("💎 Platinum", f"{trophies.get('platinum', 0):,}")
        cols[2].metric("🥇 Gold", f"{trophies.get('gold', 0):,}")
        cols[3].metric("🥈 Silver", f"{trophies.get('silver', 0):,}")
        cols[4].metric("🥉 Bronze", f"{trophies.get('bronze', 0):,}")


def display_platinum_mosaic(df: pd.DataFrame):
    """
    Finds all platinum trophies in the log and displays their icons in a mosaic.
    """
    if df.empty:
        return

    st.subheader("💎 Platinum Trophy Mosaic")

    platinums = df[df["grade"] == "Platinum"].to_dict("records")
    if not platinums:
        st.info("No Platinum trophies found in the provided data.")
        return

    # Create an HTML/CSS grid for the mosaic
    st.markdown(
        """
    <style>
    .mosaic {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(64px, 1fr));
        gap: 10px;
    }
    .mosaic-item img {
        width: 100%;
        border-radius: 10px;
        box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.2);
        transition: transform 0.2s;
    }
    .mosaic-item img:hover {
        transform: scale(1.1);
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Generate the HTML for each trophy icon
    image_html = ""
    for plat in platinums:
        # Each image is wrapped in a div with a title for hover-over info
        image_html += f'<div class="mosaic-item" title="{plat["game"]}: {plat["title"]}"><img src="{plat["icon_url"]}" alt="{plat["title"]}"></div>'

    st.markdown(f'<div class="mosaic">{image_html}</div>', unsafe_allow_html=True)


def display_rarest_trophies(df: pd.DataFrame, n: int = 5):
    """
    Displays a random sample of N trophies from the user's top 100 rarest.
    """
    st.subheader("🏆 Some of Your Rarest Trophies")

    df_copy = df.copy()
    df_copy["rarity_numeric"] = pd.to_numeric(
        df_copy["rarity_percent"].str.replace("%", ""), errors="coerce"
    )

    top_100_rarest_under_5_rarity = (
        df_copy.dropna(subset=["rarity_numeric"])
        .query("rarity_numeric < 5")
        .sort_values("rarity_numeric")
        .head(100)
    )

    if top_100_rarest_under_5_rarity.empty:
        st.info("Could not determine rarest trophies from the provided data.")
        return

    sample_size = min(n, len(top_100_rarest_under_5_rarity))
    rarest_sample = top_100_rarest_under_5_rarity.sample(sample_size)

    for _, row in rarest_sample.iterrows():
        col1, col2 = st.columns([1, 9])
        with col1:
            st.image(row["icon_url"], width=50)
        with col2:
            st.markdown(f"**{row['title']}**")
            st.markdown(f"*{row['game']}* - **{row['rarity_percent']} Rarity**")
        st.divider()


def display_showcase_tab(df: pd.DataFrame):
    """Renders all visualizations for The Showcase tab."""
    # display_summary(summary)
    if not df.empty:
        col1, col2 = st.columns(2)

        with col1:
            display_platinum_mosaic(df)

        with col2:
            display_rarest_trophies(df)


# Timeline


def display_trophy_timeline(df: pd.DataFrame):
    """
    Visualizes the trophy earning timeline with markers for platinum trophies.
    """
    st.subheader("Trophy Earning Timeline")

    df_copy = df.copy()
    df_copy["month_start"] = df_copy["timestamp"].dt.to_period("M").dt.start_time
    monthly_counts = (
        df.groupby([pd.Grouper(key="timestamp", freq="MS"), "grade"])
        .size()
        .unstack(fill_value=0)
    )

    grade_order = ["Bronze", "Silver", "Gold", "Platinum"]
    for grade in grade_order:
        if grade not in monthly_counts.columns:
            monthly_counts[grade] = 0

    monthly_counts = monthly_counts[grade_order]

    fig = go.Figure()
    color_map = {
        "Bronze": "#cd7f32",
        "Silver": "#c0c0c0",
        "Gold": "#ffd700",
        "Platinum": "#87cefa",
    }

    for grade in grade_order:
        fig.add_trace(
            go.Bar(
                x=monthly_counts.index,
                y=monthly_counts[grade],
                name=grade,
                marker_color=color_map.get(grade),
                hovertemplate=f"%{{y}} {grade}<extra></extra>",
                legendgroup="platinum" if grade == "Platinum" else None,
            )
        )

    if "Platinum" in df["grade"].unique():
        platinum_df = df[df["grade"] == "Platinum"].copy()

        plat_dates = []
        plat_y_values = []
        plat_hover_texts = []

        platinum_df["month_start"] = (
            platinum_df["timestamp"].dt.to_period("M").dt.start_time
        )
        platinum_groups = platinum_df.groupby("month_start")

        for month_start_date, group in platinum_groups:
            if not group.empty and month_start_date in monthly_counts.index:
                total_on_month = monthly_counts.loc[month_start_date].sum()
                count = len(group)
                game_names = ", ".join(group["game"].unique())

                plat_dates.append(month_start_date)
                plat_y_values.append(total_on_month + (total_on_month * 0.05) + 0.5)
                plat_hover_texts.append(f"<b>{count}x Platinum</b><br>{game_names}")

        fig.add_trace(
            go.Scatter(
                x=plat_dates,
                y=plat_y_values,
                mode="text",
                text=["💎"] * len(plat_dates),
                textfont=dict(size=16),
                customdata=plat_hover_texts,
                hovertemplate="%{customdata}<extra></extra>",
                showlegend=False,
                legendgroup="platinum",
            )
        )

    fig.update_layout(
        barmode="stack",
        title="Trophies Earned Per Month",
        xaxis_title="Date",
        yaxis_title="Trophies Earned",
        template="plotly_white",
        hovermode="x unified",
        height=500,
        showlegend=True,
        legend_orientation="h",
        legend_yanchor="bottom",
        legend_y=1.02,
        legend_xanchor="right",
        legend_x=1,
    )
    st.plotly_chart(fig, use_container_width=True)


def display_trophy_heatmap(df: pd.DataFrame):
    """
    Implements a calendar heatmap showing the count of trophies earned per day.
    """
    st.subheader("Daily Trophy Activity Heatmap")

    if df.empty:
        st.info("No trophy data available for heatmap.")
        return

    daily_counts = (
        df.set_index("timestamp").resample("D").size().reset_index(name="count")
    )
    daily_counts = daily_counts[
        daily_counts["count"] > 0
    ]  # Keep only days with activity

    years = daily_counts["timestamp"].dt.year.unique()
    if len(years) == 0:
        st.info("No trophy activity to display in heatmap.")
        return

    year_tabs = st.tabs([str(y) for y in sorted(years, reverse=True)])

    for i, selected_year in enumerate(sorted(years, reverse=True)):
        with year_tabs[i]:
            year_df = daily_counts[daily_counts["timestamp"].dt.year == selected_year]

            # Fill date range gaps
            all_days = pd.date_range(
                start=f"{selected_year}-01-01", end=f"{selected_year}-12-31", freq="D"
            )
            year_df = (
                year_df.set_index("timestamp")
                .reindex(all_days, fill_value=0)
                .reset_index()
            )
            year_df.columns = ["date", "count"]

            # Calendar grid
            year_df["day_of_week"] = year_df["date"].dt.dayofweek
            year_df["week_of_year"] = year_df["date"].dt.isocalendar().week

            # Adjust for weeks spanning across years
            if year_df["week_of_year"].iloc[0] > 50:
                year_df.loc[year_df["week_of_year"] > 50, "week_of_year"] = 0

            fig = go.Figure(
                data=go.Heatmap(
                    z=year_df["count"],
                    x=year_df["week_of_year"],
                    y=year_df["day_of_week"],
                    colorscale="Greens",
                    hovertemplate="<b>Date</b>: %{customdata|%Y-%m-%d}<br><b>Trophies</b>: %{z}<extra></extra>",
                    customdata=year_df["date"],
                    showscale=False,
                )
            )

            fig.update_layout(
                yaxis=dict(
                    tickmode="array",
                    tickvals=[0, 1, 2, 3, 4, 5, 6],
                    ticktext=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                    title="",
                ),
                xaxis=dict(title="Week of Year"),
                height=300,
            )

            st.plotly_chart(fig, use_container_width=True)


def display_streak_analysis(df: pd.DataFrame):
    """
    Analyzes and displays the longest and current gaming streaks.
    """
    st.subheader("Gaming Streaks")

    unique_days = (
        pd.Series(df["timestamp"].dt.normalize().unique())
        .sort_values()
        .reset_index(drop=True)
    )

    if len(unique_days) < 2:
        st.info("Not enough data to calculate streaks.")
        return

    # Identify streaks
    streaks = []
    if not unique_days.empty:
        current_streak_start = unique_days.iloc[0]
        for i in range(1, len(unique_days)):
            if (unique_days.iloc[i] - unique_days.iloc[i - 1]).days > 1:
                streaks.append((current_streak_start, unique_days.iloc[i - 1]))
                current_streak_start = unique_days.iloc[i]
        streaks.append((current_streak_start, unique_days.iloc[-1]))

    # Calculate longest
    longest_streak_len = 0
    streak_period_str = "No streaks found :("
    if streaks:
        streak_lengths = [(end - start).days + 1 for start, end in streaks]
        if streak_lengths:
            longest_streak_len = max(streak_lengths)
            longest_streak_index = streak_lengths.index(longest_streak_len)
            longest_start, longest_end = streaks[longest_streak_index]
            streak_period_str = f"{longest_start.strftime('%b %d, %Y')} - {longest_end.strftime('%b %d, %Y')}"

    # Calculate current streak
    current_streak = 0
    if streaks:
        last_streak_start, last_streak_end = streaks[-1]
        today = pd.to_datetime(datetime.now().date())
        if (today - last_streak_end).days <= 1:
            current_streak = (last_streak_end - last_streak_start).days + 1

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "🔥 Longest Streak", f"{longest_streak_len} days", help=streak_period_str
        )
    with col3:
        st.metric("🏃 Current Streak", f"{current_streak} days")


def display_activity_by_hour_and_weekday(df: pd.DataFrame):
    """
    Displays radial plots for trophy activity by hour of day and day of week.
    """
    st.subheader("🎮 Your Gaming Habits")
    col1, col2 = st.columns(2)

    with col1:
        hourly_counts = df.groupby(df["timestamp"].dt.hour).size()
        active_days_per_hour = df.groupby(df["timestamp"].dt.hour)["timestamp"].apply(
            lambda x: x.dt.date.nunique()
        )
        hourly_avg = hourly_counts / active_days_per_hour

        all_hours = pd.Index(range(24))
        hourly_avg = hourly_avg.reindex(all_hours, fill_value=0).sort_index()

        r_values = list(hourly_avg.values)
        r_values.append(r_values[0])
        theta_values = [str(h) for h in hourly_avg.index]
        theta_values.append(theta_values[0])

        fig_hourly = go.Figure(
            go.Scatterpolar(
                r=r_values,
                theta=theta_values,
                fill="toself",
                mode="lines+markers",
                name="Trophies",
                customdata=np.stack([np.round(r_values, 2)], axis=-1),
                hovertemplate="<b>Hour</b>: %{theta}<br><b>Avg Trophies</b>: %{r:.2f}<extra></extra>",  # fix: not working
            )
        )

        fig_hourly.update_layout(
            title="Average Trophies by Hour of Day",
            template="plotly_dark",
            polar=dict(
                radialaxis=dict(visible=True, showticklabels=False),
                angularaxis=dict(direction="clockwise", tickvals=list(range(0, 24, 3))),
            ),
            height=300,
            margin=dict(t=60, b=40),
        )
        st.plotly_chart(fig_hourly, use_container_width=True)

    with col2:
        daily_counts = df.groupby(df["timestamp"].dt.day_name()).size()
        active_weeks_per_day = df.groupby(df["timestamp"].dt.day_name())[
            "timestamp"
        ].apply(lambda x: x.dt.to_period("W").nunique())
        daily_avg = daily_counts / active_weeks_per_day

        day_order = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        daily_avg = daily_avg.reindex(day_order, fill_value=0)

        r_values_daily = list(daily_avg.values)
        r_values_daily.append(r_values_daily[0])
        theta_values_daily = list(daily_avg.index)
        theta_values_daily.append(theta_values_daily[0])

        fig_daily = go.Figure(
            go.Scatterpolar(
                r=r_values_daily,
                theta=theta_values_daily,
                fill="toself",
                name="Trophies",
                customdata=np.stack([np.round(r_values_daily, 2)], axis=-1),
                hovertemplate="<b>Day</b>: %{theta}<br><b>Avg Trophies</b>: %{customdata[0]}<extra></extra>",  # fix: not working
            )
        )

        fig_daily.update_layout(
            title="Average Trophies by Day of Week",
            template="plotly_dark",
            polar=dict(
                radialaxis=dict(visible=True, showticklabels=False),
                angularaxis=dict(direction="clockwise", tickvals=list(range(0, 24, 3))),
            ),
            height=300,
            margin=dict(t=60, b=40),
        )
        st.plotly_chart(fig_daily, use_container_width=True)


def display_streak_and_activity(df: pd.DataFrame):
    c1, c2 = st.columns(2)

    # with c1:
    display_streak_analysis(df)

    # with c2:
    display_activity_by_hour_and_weekday(df)


def display_timeline_tab(df: pd.DataFrame):
    """Renders all visualizations for The Timeline tab."""
    if df.empty:
        return

    df["timestamp"] = df["timestamp"].apply(parse_custom_timestamp)
    df.dropna(subset=["timestamp"], inplace=True)
    df["date"] = df["timestamp"].dt.date

    display_trophy_timeline(df)
    st.divider()

    display_streak_and_activity(df)
    st.divider()

    display_trophy_heatmap(df)


# Deep Dive


def display_top_games(df: pd.DataFrame):
    """ """
    with st.expander("Top Games", expanded=True):
        n = st.slider("How many games to show?", min_value=1, max_value=30, value=5)
        game_counts = df["game"].value_counts().nlargest(n).reset_index()
        game_counts.columns = ["Game", "Trophies Earned"]
        fig2 = px.pie(
            game_counts,
            names="Game",
            values="Trophies Earned",
            title=f"Top {n} Games by Trophies Earned",
            hole=0.3,
        )
        st.plotly_chart(fig2, use_container_width=True)


def display_acquisition_curve(df: pd.DataFrame):
    """
    Visualizes the time taken to earn each trophy after starting a game.
    This helps to show which games were completed quickly versus those
    that were a long grind.
    """
    st.subheader("Trophy Acquisition Speed")

    if "timestamp" not in df.columns or df["timestamp"].isnull().all():
        st.warning("Timestamp data is required for this visualization.")
        return

    df_sorted = df.sort_values("timestamp")
    start_dates = df_sorted.groupby("game")["timestamp"].transform("min")
    df_sorted["days_from_start"] = (df_sorted["timestamp"] - start_dates).dt.days
    df_sorted["trophy_num"] = df_sorted.groupby("game").cumcount() + 1

    game_list = df_sorted["game"].unique()
    selected_game = st.selectbox("Select a Game to Analyze", options=game_list)

    if selected_game:
        game_df = df_sorted[df_sorted["game"] == selected_game]

        fig = px.line(
            game_df,
            x="trophy_num",
            y="days_from_start",
            markers=True,
            line_shape="spline",
            title=f"Trophy Acquisition Speed for {selected_game}",
            labels={
                "trophy_num": "Number of Trophies",
                "days_from_start": "Days Since First Trophy",
            },
            hover_data={"title": True, "grade": True, "rarity_percent": True},
            text="trophy_num",
        )
        fig.update_traces(textposition="top center", marker=dict(size=8))
        fig.update_layout(template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)


def display_time_to_platinum(df: pd.DataFrame):
    """
    Displays a horizontal bar chart ranking the fastest platinums.
    """
    st.subheader("Time-to-Platinum Leaderboard")

    platinums = df[df["grade"] == "Platinum"]
    if platinums.empty:
        st.info("No Platinum trophies found to analyze.")
        return

    first_trophies = df.groupby("game")["timestamp"].min().rename("start_time")
    plats_with_start = platinums.merge(first_trophies, on="game")
    plats_with_start["time_to_plat_days"] = (
        plats_with_start["timestamp"] - plats_with_start["start_time"]
    ).dt.days

    fastest_plats = plats_with_start.sort_values("time_to_plat_days").head(20)

    fig = px.bar(
        fastest_plats,
        x="time_to_plat_days",
        y="game",
        orientation="h",
        title="Your Fastest Platinum Trophies",
        labels={"time_to_plat_days": "Days to Platinum", "game": "Game"},
        hover_data={"title": True},
        text="time_to_plat_days",
    )

    fig.update_traces(textangle=0, textposition="outside")

    fig.update_layout(
        template="plotly_white",
        yaxis={"categoryorder": "total ascending"},
        height=30 * len(fastest_plats),
    )
    st.plotly_chart(fig, use_container_width=True)


def display_rarity_distribution(df: pd.DataFrame):
    """
    Displays a bar chart showing the user's trophy rarity distribution.
    """
    st.subheader("Trophy Rarity Distribution")

    df_copy = df.copy()
    df_copy["rarity_numeric"] = pd.to_numeric(
        df_copy["rarity_percent"].str.replace("%", ""), errors="coerce"
    )
    df_copy.dropna(subset=["rarity_numeric"], inplace=True)

    bins = [0, 5, 10, 20, 50, 101]
    labels = [
        "Ultra Rare (0-5%)",
        "Very Rare (5-10%)",
        "Rare (10-20%)",
        "Uncommon (20-50%)",
        "Common (50%+)",
    ]
    df_copy["rarity_bucket"] = pd.cut(
        df_copy["rarity_numeric"], bins=bins, labels=labels, right=False
    )

    rarity_counts = (
        df_copy["rarity_bucket"].value_counts().reindex(labels, fill_value=0)
    )

    fig = px.bar(
        rarity_counts,
        x=rarity_counts.index,
        y=rarity_counts.values,
        title="Your Trophy Hunting Style by Rarity",
        labels={"rarity_bucket": "Rarity Category", "y": "Number of Trophies"},
        text="count",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)


def display_deep_dive_tab(df: pd.DataFrame):
    """Renders all visualizations for the Deep Dive tab."""
    if not df.empty:
        display_acquisition_curve(df)
        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            display_time_to_platinum(df)
            st.divider()

        with c2:
            display_rarity_distribution(df)
            st.divider()


# Milestones


def display_milestone_card(title: str, trophy: pd.Series):
    """Helper function to display a single milestone trophy."""
    if trophy is None or trophy.empty:
        return

    col1, col2 = st.columns([1, 4])
    with col1:
        st.image(trophy["icon_url"], width=64)
    with col2:
        st.markdown(f"**{title}**")
        st.markdown(f"**{trophy['title']}** ({trophy['grade']})")
        st.markdown(f"*{trophy['game']}* - {trophy['timestamp'].strftime('%b %d, %Y')}")

    st.divider()


def display_milestones(df: pd.DataFrame):
    """Identifies and displays key trophy milestones dynamically."""
    st.subheader("🏔️ Key Milestones")
    st.divider()

    if df.empty:
        st.info("No trophy data to identify milestones.")
        return

    df_sorted = df.sort_values("timestamp", ascending=False).reset_index(drop=True)

    platinums = (
        df_sorted[df_sorted["grade"] == "Platinum"]
        .sort_values("timestamp", ascending=False)
        .reset_index(drop=True)
    )

    milestones = []

    # Basic

    first_trophy = df_sorted.iloc[-1]
    milestones.append(("First Ever Trophy", first_trophy))

    if not platinums.empty:
        milestones.append(("First Platinum", platinums.iloc[-1]))
        milestones.append(("Latest Platinum", platinums.iloc[0]))

        first_trophies_per_game = df_sorted.groupby("game")["timestamp"].min()
        plats_with_start = platinums.merge(
            first_trophies_per_game.rename("start_time"), on="game"
        )
        plats_with_start["time_to_plat"] = (
            plats_with_start["timestamp"] - plats_with_start["start_time"]
        )
        fastest_plat = plats_with_start.loc[plats_with_start["time_to_plat"].idxmin()]
        time_str = str(fastest_plat["time_to_plat"]).split(".")[0]
        milestones.append((f"Fastest Platinum ({time_str})", fastest_plat))

    # Comedy Festival
    if len(df_sorted) >= 69:
        milestones.append(("69th Trophy", df_sorted.iloc[-69]))
    if len(df_sorted) >= 420:
        milestones.append(("420th Trophy", df_sorted.iloc[-420]))
    if len(df_sorted) >= 666:
        milestones.append(("666th Trophy", df_sorted.iloc[-666]))
    if len(df_sorted) >= 1337:
        milestones.append(("1337th Trophy (Leet!)", df_sorted.iloc[-1337]))

    # Dynamic Repeating Milestones
    for i in range(1000, len(df_sorted) + 1, 1000):
        milestones.append((f"{i:,}th Trophy", df_sorted.iloc[-i]))

    for i in range(10, len(platinums) + 1, 10):
        milestones.append((f"{i}th Platinum", platinums.iloc[-i]))

    # Sort milestones chronologically
    milestones.sort(key=lambda x: x[1]["timestamp"])

    cols = st.columns(3)
    for i, (title, trophy) in enumerate(milestones):
        with cols[i % 3]:
            display_milestone_card(title, trophy)


# Raw Data


@st.cache_data
def convert_df_to_csv(df: pd.DataFrame):
    """Helper function to convert DataFrame to CSV for downloading."""
    return df.to_csv(index=False).encode("utf-8")


def display_raw_data(df: pd.DataFrame):
    if df.empty:
        st.warning("No trophy data to display.")
        return

    with st.expander("Show Filters"):
        filter_cols = st.columns([2, 2])

        with filter_cols[0]:
            min_date = df["timestamp"].min().date()
            max_date = df["timestamp"].max().date()
            start_date = st.date_input(
                "Start date",
                min_date,
                min_value=min_date,
                max_value=max_date,
                key="start_date_filter",
            )

            unique_games = sorted(df["game"].unique())
            game_search = st.text_input("Search for a game", key="game_search_filter")

            if game_search:
                filtered_game_options = [
                    game for game in unique_games if game_search.lower() in game.lower()
                ]
            else:
                filtered_game_options = unique_games

            selected_games = st.multiselect(
                "Filter by Game",
                options=filtered_game_options,
                default=filtered_game_options,
                key="game_multiselect_filter",
            )

        with filter_cols[1]:
            end_date = st.date_input(
                "End date",
                max_date,
                min_value=min_date,
                max_value=max_date,
                key="end_date_filter",
            )
            unique_grades = ["Platinum", "Gold", "Silver", "Bronze"]
            selected_grades = st.multiselect(
                "Filter by Grade",
                options=unique_grades,
                default=unique_grades,
                key="grade_filter",
            )

            # Reset
            st.write("")
            st.write("")
            if st.button("Reset Filters"):
                keys_to_clear = [
                    "start_date_filter",
                    "end_date_filter",
                    "grade_filter",
                    "game_search_filter",
                    "game_multiselect_filter",
                ]
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

    filtered_df = df[
        (df["timestamp"].dt.date >= start_date)
        & (df["timestamp"].dt.date <= end_date)
        & (df["grade"].isin(selected_grades))
        & (df["game"].isin(selected_games))
    ]

    st.markdown(f"**Displaying {len(filtered_df)} of {len(df)} trophies**")

    col_order = [
        "game",
        "title",
        "timestamp",
        "grade",
        "rarity_percent",
        "icon_url",
    ]
    existing_cols = [col for col in col_order if col in filtered_df.columns]
    st.dataframe(filtered_df[existing_cols])

    csv = convert_df_to_csv(filtered_df[existing_cols])
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name="trophy_data.csv",
        mime="text/csv",
    )
