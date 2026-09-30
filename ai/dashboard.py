"""
Streamlit dashboard over the Gold marts.

This is the "so what" layer: the same tables the text-to-SQL app queries
invisibly, laid out as a fixed set of charts the business actually asked for.

Every chart reads a mart, never a raw table — if a number here looks wrong, the
bug is in dbt, not in this file.

Usage:
    streamlit run ai/dashboard.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    AI_READONLY_ROLE,
    ConfigError,
    fetch_dataframe,
    get_connection,
)

st.set_page_config(page_title="Zomato operations dashboard", page_icon="📈", layout="wide")


@st.cache_data(ttl=600, show_spinner=False)
def load_marts() -> dict[str, pd.DataFrame]:
    """
    Pull all four marts in one connection.

    A 10-minute TTL: long enough that clicking around the dashboard does not
    re-query Snowflake on every widget interaction, short enough that a fresh
    dbt run shows up while you are still looking at the screen.
    """
    queries = {
        "revenue": "SELECT * FROM ZOMATO.MARTS.MART_DAILY_CITY_REVENUE",
        "sla": "SELECT * FROM ZOMATO.MARTS.MART_DELIVERY_SLA",
        "restaurants": "SELECT * FROM ZOMATO.MARTS.MART_RESTAURANT_PERFORMANCE",
        "reviews": "SELECT * FROM ZOMATO.MARTS.MART_REVIEW_INSIGHTS",
    }
    # Role comes from the shared constant, not a hard-coded string, so changing
    # SNOWFLAKE_AI_ROLE changes it here too.
    with get_connection(role=AI_READONLY_ROLE, schema="MARTS") as conn:
        return {name: fetch_dataframe(conn, sql) for name, sql in queries.items()}

