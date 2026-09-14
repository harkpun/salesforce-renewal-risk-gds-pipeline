"""Databricks App for the Renewal Risk Analyst workflow.

The app is deliberately small and sequential:

1. Connect to a Databricks SQL warehouse.
2. Read the highest-risk accounts from the gold table.
3. Let the user choose an account.
4. Display the governed account summary that can be sent to an LLM.

For the compact project, this app is optional. The primary agentic workflow can
also be done with setup/03_ai_query_account_briefing.sql.
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st
from databricks import sql


CATALOG = os.getenv("UC_CATALOG", "renewal_risk_lakehouse")
SCHEMA = os.getenv("UC_SCHEMA", "renewal_risk_dev")
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "")
SERVER_HOSTNAME = os.getenv("DATABRICKS_HOST", "")
ACCESS_TOKEN = os.getenv("DATABRICKS_TOKEN", "")


def run_sql(query: str) -> pd.DataFrame:
    """Run a SQL query against Databricks and return a Pandas DataFrame."""

    if not WAREHOUSE_ID or not SERVER_HOSTNAME or not ACCESS_TOKEN:
        st.warning(
            "Set DATABRICKS_HOST, DATABRICKS_TOKEN, and DATABRICKS_WAREHOUSE_ID "
            "in the app environment before querying live data."
        )
        return pd.DataFrame()

    with sql.connect(
        server_hostname=SERVER_HOSTNAME.replace("https://", ""),
        http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
        access_token=ACCESS_TOKEN,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall_arrow().to_pandas()


def load_priority_queue() -> pd.DataFrame:
    """Load the top customer success actions from the gold serving table."""

    return run_sql(
        f"""
        SELECT
          priority_rank,
          account_id,
          account_name,
          customer_segment,
          arr,
          days_to_renewal,
          risk_score,
          risk_band,
          recommended_action
        FROM {CATALOG}.{SCHEMA}.gold_csm_priority_queue
        ORDER BY priority_rank
        LIMIT 25
        """
    )


def load_account_summary(account_id: str) -> pd.DataFrame:
    """Load one governed account summary for the selected account."""

    safe_account_id = account_id.replace("'", "''")
    return run_sql(
        f"""
        SELECT
          account_name,
          risk_band,
          risk_score,
          account_summary_text
        FROM {CATALOG}.{SCHEMA}.gold_account_360_summary
        WHERE account_id = '{safe_account_id}'
        """
    )


st.set_page_config(page_title="Renewal Risk Analyst", layout="wide")
st.title("Renewal Risk Analyst")

queue = load_priority_queue()

if queue.empty:
    st.info("No live data loaded yet. Run the Lakeflow pipeline, then redeploy or refresh this app.")
else:
    st.subheader("Customer Success Priority Queue")
    st.dataframe(queue.drop(columns=["account_id"]), use_container_width=True, hide_index=True)

    selected_name = st.selectbox("Account", queue["account_name"].tolist())
    selected_id = queue.loc[queue["account_name"] == selected_name, "account_id"].iloc[0]
    summary = load_account_summary(selected_id)

    if not summary.empty:
        row = summary.iloc[0]
        st.subheader(f"Briefing: {row['account_name']}")
        st.metric("Risk score", int(row["risk_score"]), row["risk_band"])
        st.write(row["account_summary_text"])
        st.caption(
            "In production, this text is grounded context for ai_query, AI Search, "
            "or a tool-calling Databricks agent."
        )
