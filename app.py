"""
Streamlit UI for RetailMind Product Intelligence Agent.

Features:
- Sidebar with category filter, catalog summary metrics, and clear chat button
- Auto-generated Daily Briefing on startup
- Chat interface with multi-turn conversation memory
"""

import streamlit as st
from agent import run_agent, generate_daily_briefing
from data_loader import get_products_df
from config import CATEGORIES, STOCKOUT_CRITICAL_DAYS

# --- Page Configuration ---
st.set_page_config(
    page_title="RetailMind Product Intelligence",
    page_icon="🛍️",
    layout="wide",
)


def compute_catalog_summary(category_filter: str = "All Categories") -> dict:
    """Compute catalog-level summary metrics for the sidebar panel."""
    df = get_products_df()

    if category_filter != "All Categories":
        df = df[df["category"] == category_filter]

    total_skus = len(df)

    # Compute days to stockout for critical stock count
    df = df.copy()
    df["days_to_stockout"] = df.apply(
        lambda r: r["stock_quantity"] / r["avg_daily_sales"] if r["avg_daily_sales"] > 0 else float("inf"),
        axis=1,
    )
    critical_count = int((df["days_to_stockout"] < STOCKOUT_CRITICAL_DAYS).sum())

    # Average margin across catalog
    df["gross_margin"] = (df["price"] - df["cost"]) / df["price"] * 100
    avg_margin = round(df["gross_margin"].mean(), 1)

    # Average rating
    avg_rating = round(df["avg_rating"].mean(), 1)

    return {
        "total_skus": total_skus,
        "critical_stock": critical_count,
        "avg_margin": avg_margin,
        "avg_rating": avg_rating,
    }


# =============================================================================
# Sidebar
# =============================================================================
with st.sidebar:
    st.header("RetailMind")
    st.caption("Product Intelligence Agent for StyleCraft")

    st.divider()

    # Category filter
    category_filter = st.selectbox(
        "Category Filter",
        ["All Categories"] + CATEGORIES,
        help="Scope the agent's analysis to a specific category",
    )

    st.divider()

    # Catalog Summary Panel (always visible)
    st.subheader("Catalog Summary")
    summary = compute_catalog_summary(category_filter)

    col1, col2 = st.columns(2)
    col1.metric("Total SKUs", summary["total_skus"])
    col2.metric("Critical Stock", summary["critical_stock"])

    col3, col4 = st.columns(2)
    col3.metric("Avg Margin %", f"{summary['avg_margin']}%")
    col4.metric("Avg Rating", f"{summary['avg_rating']}/5")

    st.divider()

    # Clear Chat button
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation_history = []
        st.session_state.briefing_generated = False
        st.rerun()


# =============================================================================
# Initialize Session State
# =============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

if "briefing_generated" not in st.session_state:
    st.session_state.briefing_generated = False


# =============================================================================
# Main Chat Area
# =============================================================================
st.title("RetailMind Product Intelligence Agent")
st.caption("AI-powered catalog analysis for StyleCraft | Ask about inventory, pricing, reviews, or categories")

# --- Daily Briefing (auto-generated on startup) ---
if not st.session_state.briefing_generated:
    with st.spinner("Generating daily briefing..."):
        briefing = generate_daily_briefing()

    # Store briefing as the first assistant message
    st.session_state.messages.append({"role": "assistant", "content": briefing})
    st.session_state.briefing_generated = True

# --- Display Conversation History ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Chat Input ---
if user_input := st.chat_input("Ask about your product catalog..."):
    # Display user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            response_text, updated_history = run_agent(
                user_message=user_input,
                conversation_history=st.session_state.conversation_history,
                category_filter=category_filter,
            )
            st.markdown(response_text)

    # Update state
    st.session_state.messages.append({"role": "assistant", "content": response_text})
    st.session_state.conversation_history = updated_history
