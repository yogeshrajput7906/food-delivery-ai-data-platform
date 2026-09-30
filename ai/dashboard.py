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


st.title("Zomato operations dashboard")
st.caption("Gold-layer marts, built by dbt and refreshed by the daily `zomato_batch` DAG.")

try:
    data = load_marts()
except ConfigError as exc:
    st.error(str(exc))
    st.stop()
except Exception as exc:  # noqa: BLE001
    st.error(
        f"Could not read the marts: {exc}\n\n"
        "If a table is missing, run `make pipeline` or trigger the `zomato_batch` DAG. "
        "`mart_review_insights` only exists after the AI enrichment step has run."
    )
    st.stop()

revenue = data["revenue"]
sla = data["sla"]
restaurants = data["restaurants"]
reviews = data["reviews"]

if revenue.empty:
    st.warning("The marts are empty. Load some data first.")
    st.stop()

# ---------------------------------------------------------------------------
# Headline KPIs
# ---------------------------------------------------------------------------
total_gmv = revenue["gmv"].sum()
total_orders = revenue["orders"].sum()
delivered = revenue["delivered_orders"].sum()
overall_cancel_rate = revenue["cancelled_orders"].sum() / total_orders if total_orders else 0
overall_aov = total_gmv / delivered if delivered else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("GMV (delivered)", f"₹{total_gmv:,.0f}")
col2.metric("Orders", f"{total_orders:,.0f}")
col3.metric("Average order value", f"₹{overall_aov:,.2f}")
col4.metric("Cancel rate", f"{overall_cancel_rate:.2%}")

st.divider()

