"""
Streamlit UI for RetailMind Product Intelligence Agent.
ChatGPT-inspired interface for StyleCraft's product manager.
"""

import streamlit as st
from agent import run_agent, generate_daily_briefing
from data_loader import get_products_df
from config import CATEGORIES, STOCKOUT_CRITICAL_DAYS


# --- Page Configuration ---
st.set_page_config(
    page_title="RetailMind | StyleCraft",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- ChatGPT-inspired CSS ---
st.markdown("""
<style>
    /* ---- Import font ---- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ---- Global ---- */
    html, body, .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .stApp {
        background-color: #212121;
    }

    /* ---- Hide Streamlit chrome (keep sidebar toggle visible) ---- */
    #MainMenu, footer {visibility: hidden;}
    .stDeployButton {display: none;}

    /* Make header bar blend seamlessly with the page */
    .stApp > header,
    .stApp > header > div,
    div[data-testid="stHeader"],
    div[data-testid="stHeader"] > div,
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"],
    div[data-testid="stStatusWidget"],
    div[data-testid="stStatusWidget"] > div {
        background-color: #212121 !important;
        background: #212121 !important;
        border: none !important;
        box-shadow: none !important;
    }

    /* Hide the file-change / rerun bar */
    div[data-testid="stNotification"],
    .stAlert {
        background-color: #2a2a2a !important;
        border: 1px solid #333 !important;
        border-radius: 8px !important;
        color: #d1d5db !important;
    }

    /* Style the sidebar collapse/expand button */
    button[data-testid="stSidebarCollapseButton"],
    button[data-testid="stSidebarExpandButton"] {
        color: #8e8e8e !important;
        background: transparent !important;
    }

    /* ---- Fix chat input dark artifacts ---- */
    /* Nuke every possible container inside the chat input */
    .stChatInput,
    .stChatInput *,
    .stChatInput > div > div,
    .stChatInput > div > div > div,
    .stChatInput div[data-baseweb],
    .stChatInput div[data-baseweb] > div {
        background-color: transparent !important;
        background: transparent !important;
    }

    /* Then re-apply the styled outer shell only */
    .stChatInput > div:first-child {
        background-color: #2f2f2f !important;
        border: 1px solid #3a3a3a !important;
        border-radius: 16px !important;
    }

    /* Remove dark shade behind the input bar (bottom dock) */
    .stBottom, div[data-testid="stBottom"],
    div[data-testid="stBottomBlockContainer"],
    .stBottomBlockContainer,
    div[class*="stBottom"],
    .block-container + div,
    div[data-testid="stBottom"] > div {
        background-color: #212121 !important;
        background: #212121 !important;
        border: none !important;
    }

    /* Fix the actual input textarea container */
    .stChatInput > div {
        background-color: #2f2f2f !important;
        border: 1px solid #3a3a3a !important;
        border-radius: 16px !important;
    }

    /* ---- Sidebar (dark, like ChatGPT) ---- */
    section[data-testid="stSidebar"] {
        background-color: #171717;
        border-right: 1px solid #2a2a2a;
    }

    section[data-testid="stSidebar"] * {
        color: #ececec !important;
    }

    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {
        color: #ececec !important;
    }

    section[data-testid="stSidebar"] div[data-baseweb="select"] {
        background-color: #2a2a2a !important;
        border-color: #3a3a3a !important;
        border-radius: 10px !important;
    }

    section[data-testid="stSidebar"] div[data-baseweb="select"] * {
        color: #ececec !important;
    }

    section[data-testid="stSidebar"] hr {
        border-color: #2a2a2a !important;
    }

    /* ---- Sidebar metric cards ---- */
    section[data-testid="stSidebar"] div[data-testid="stMetric"] {
        background: #2a2a2a;
        border: 1px solid #333;
        border-radius: 10px;
        padding: 10px 14px;
    }

    section[data-testid="stSidebar"] div[data-testid="stMetric"] label {
        color: #8e8e8e !important;
        font-size: 0.7rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    section[data-testid="stSidebar"] div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 1.3rem !important;
        font-weight: 700 !important;
    }

    /* ---- Sidebar button ---- */
    section[data-testid="stSidebar"] .stButton > button {
        background-color: #2a2a2a !important;
        color: #ececec !important;
        border: 1px solid #3a3a3a !important;
        border-radius: 10px !important;
        font-weight: 500 !important;
        transition: background-color 0.2s !important;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #333 !important;
        border-color: #4a4a4a !important;
    }

    /* ---- Main content area (centered like ChatGPT) ---- */
    .main .block-container {
        max-width: 820px !important;
        padding-top: 2rem !important;
        padding-bottom: 6rem !important;
        margin: 0 auto;
    }

    /* ---- Title area ---- */
    .main-title {
        color: #ececec;
        font-size: 1.3rem;
        font-weight: 600;
        text-align: center;
        margin-bottom: 4px;
    }

    .main-subtitle {
        color: #8e8e8e;
        font-size: 0.82rem;
        text-align: center;
        margin-bottom: 28px;
    }

    /* ---- Chat messages ---- */
    .stChatMessage {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 14px 0 !important;
        max-width: 820px;
        margin: 0 auto;
    }

    /* Base text styling */
    .stChatMessage p {
        color: #d1d5db !important;
        font-size: 0.92rem !important;
        line-height: 1.75 !important;
        margin-bottom: 8px !important;
    }

    /* Bold text stands out in white */
    .stChatMessage strong {
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    /* Headings in responses */
    .stChatMessage h1 {
        color: #ececec !important;
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        margin-top: 20px !important;
        margin-bottom: 10px !important;
        padding-bottom: 6px;
        border-bottom: 1px solid #333;
    }

    .stChatMessage h2 {
        color: #ececec !important;
        font-size: 1.05rem !important;
        font-weight: 600 !important;
        margin-top: 18px !important;
        margin-bottom: 8px !important;
    }

    .stChatMessage h3 {
        color: #10a37f !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        margin-top: 18px !important;
        margin-bottom: 8px !important;
    }

    /* Bullet lists */
    .stChatMessage ul {
        padding-left: 18px !important;
        margin-bottom: 10px !important;
    }

    .stChatMessage li {
        color: #d1d5db !important;
        font-size: 0.92rem !important;
        line-height: 1.75 !important;
        margin-bottom: 4px !important;
    }

    .stChatMessage li::marker {
        color: #10a37f !important;
    }

    /* Blockquotes (recommendations / insights) */
    .stChatMessage blockquote {
        border-left: 3px solid #10a37f !important;
        background: rgba(16, 163, 127, 0.06) !important;
        padding: 10px 16px !important;
        margin: 12px 0 !important;
        border-radius: 0 8px 8px 0 !important;
    }

    .stChatMessage blockquote p {
        color: #b4b4b4 !important;
        font-style: italic !important;
        margin-bottom: 0 !important;
    }

    /* Code blocks */
    .stChatMessage code {
        background: #2a2a2a !important;
        color: #10a37f !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
        font-size: 0.85rem !important;
    }

    .stChatMessage pre {
        background: #1a1a1a !important;
        border: 1px solid #333 !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
    }

    /* User messages with subtle background */
    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
        background: #2f2f2f !important;
        border-radius: 16px !important;
        padding: 12px 20px !important;
    }

    /* ---- Chat input (bottom bar like ChatGPT) ---- */
    .stChatInput {
        max-width: 820px;
        margin: 0 auto;
    }

    .stChatInput textarea {
        color: #ececec !important;
        caret-color: #ececec !important;
        background-color: transparent !important;
    }

    .stChatInput textarea::placeholder {
        color: #6b6b6b !important;
    }

    /* Send button inside input */
    .stChatInput button {
        background-color: transparent !important;
        color: #8e8e8e !important;
    }

    /* ---- Streamlit dataframe dark theme ---- */
    .stDataFrame, .stDataFrame * {
        color: #d1d5db !important;
    }
    .stDataFrame div[data-testid="stDataFrameResizable"] {
        border: 1px solid #333 !important;
        border-radius: 8px !important;
    }

    /* ---- Spinner ---- */
    .stSpinner > div > div {
        border-top-color: #10a37f !important;
    }

    .stSpinner > div > span {
        color: #8e8e8e !important;
    }

    /* ---- Scrollbar ---- */
    ::-webkit-scrollbar {
        width: 6px;
    }
    ::-webkit-scrollbar-track {
        background: #212121;
    }
    ::-webkit-scrollbar-thumb {
        background: #3a3a3a;
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #4a4a4a;
    }

    /* ---- Remove link underlines in chat ---- */
    .stChatMessage a {
        color: #10a37f !important;
        text-decoration: none;
    }

    /* ---- Hide chat avatar icons entirely ---- */
    [data-testid="stChatMessage"] [data-testid*="chatAvatar"],
    [data-testid="stChatMessage"] [data-testid*="Avatar"],
    .stChatMessage [data-testid*="chatAvatar"],
    .stChatMessage [data-testid*="Avatar"],
    [data-testid="stChatMessage"] > div:first-child img,
    [data-testid="stChatMessage"] > div:first-child svg,
    .stChatMessage > div:first-child img,
    .stChatMessage > div:first-child svg {
        display: none !important;
    }

    /* Remove avatar container background/shape */
    [data-testid="stChatMessage"] > div:first-child > div,
    .stChatMessage > div:first-child > div {
        background: none !important;
        border-radius: 0 !important;
        width: 0 !important;
        height: 0 !important;
        min-width: 0 !important;
        min-height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        overflow: hidden !important;
    }

    /* Collapse the avatar column itself */
    [data-testid="stChatMessage"] > div:first-child,
    .stChatMessage > div:first-child {
        width: 0 !important;
        min-width: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        flex: 0 0 0px !important;
    }

    /* ---- Tables in chat ---- */
    .stChatMessage table {
        border-collapse: collapse;
        margin: 12px 0;
        width: 100%;
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #333;
    }
    .stChatMessage th {
        background: #2a2a2a !important;
        color: #ececec !important;
        padding: 10px 14px !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        text-transform: uppercase;
        letter-spacing: 0.3px;
        text-align: left !important;
    }
    .stChatMessage td {
        color: #d1d5db !important;
        padding: 8px 14px !important;
        border-bottom: 1px solid #2a2a2a !important;
        font-size: 0.88rem !important;
    }
    .stChatMessage tr:hover td {
        background: rgba(16, 163, 127, 0.04) !important;
    }
</style>
""", unsafe_allow_html=True)


def compute_catalog_summary(category_filter: str = "All Categories") -> dict:
    """Compute catalog-level summary metrics for the sidebar panel."""
    df = get_products_df()
    if category_filter != "All Categories":
        df = df[df["category"] == category_filter]

    total_skus = len(df)
    df = df.copy()
    df["days_to_stockout"] = df.apply(
        lambda r: r["stock_quantity"] / r["avg_daily_sales"] if r["avg_daily_sales"] > 0 else float("inf"),
        axis=1,
    )
    critical_count = int((df["days_to_stockout"] < STOCKOUT_CRITICAL_DAYS).sum())
    df["gross_margin"] = (df["price"] - df["cost"]) / df["price"] * 100
    avg_margin = round(df["gross_margin"].mean(), 1)
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
    st.markdown("### RetailMind")
    st.caption("Product Intelligence for StyleCraft")

    st.divider()

    category_filter = st.selectbox(
        "Category",
        ["All Categories"] + CATEGORIES,
    )

    st.divider()

    st.caption("CATALOG OVERVIEW")
    summary = compute_catalog_summary(category_filter)

    col1, col2 = st.columns(2)
    col1.metric("SKUs", summary["total_skus"])
    col2.metric("At Risk", summary["critical_stock"])

    col3, col4 = st.columns(2)
    col3.metric("Margin", f"{summary['avg_margin']}%")
    col4.metric("Rating", f"{summary['avg_rating']}")

    st.divider()

    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation_history = []
        st.session_state.briefing_generated = False
        st.rerun()


# =============================================================================
# Session State
# =============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "briefing_generated" not in st.session_state:
    st.session_state.briefing_generated = False
if "briefing_data" not in st.session_state:
    st.session_state.briefing_data = None


# =============================================================================
# Main Chat Area
# =============================================================================
st.markdown('<div class="main-title">StyleCraft Intelligence</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">Ask anything about inventory, pricing, reviews, or catalog performance</div>', unsafe_allow_html=True)

# --- Generate Daily Briefing Data ---
if not st.session_state.briefing_generated:
    with st.spinner("Preparing your daily briefing..."):
        st.session_state.briefing_data = generate_daily_briefing()
    st.session_state.briefing_generated = True


def render_daily_briefing(data: dict):
    """Render the daily briefing using native Streamlit components."""

    st.markdown("---")

    # ---- Header ----
    st.markdown("""
    <div style="margin-bottom: 32px;">
        <span style="color: #10a37f; font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
                     letter-spacing: 2px;">DAILY BRIEFING</span>
        <h2 style="color: #ececec; font-size: 1.5rem; font-weight: 700; margin-top: 6px; margin-bottom: 6px;">
            Good morning, Priya.</h2>
        <p style="color: #888; font-size: 0.9rem; margin: 0;">Here's your catalog snapshot for today.</p>
    </div>
    """, unsafe_allow_html=True)

    # ---- Stockout Alerts ----
    alerts = data["stockout_alerts"]
    total_alerts = data["all_alerts_count"]

    st.markdown(f"""
    <div style="margin-bottom: 16px;">
        <h3 style="color: #ff6b6b; font-size: 1.05rem; font-weight: 700; margin-bottom: 4px;">
            Stockout Alerts</h3>
        <p style="color: #777; font-size: 0.85rem; margin: 0;">
            {total_alerts} products at risk of stockout within 7 days</p>
    </div>
    """, unsafe_allow_html=True)

    if alerts:
        for item in alerts:
            days = item["days_to_stockout"]
            urgency_color = "#ff4444" if days < 1 else "#ff8c00" if days < 3 else "#ffd700"
            st.markdown(f"""
            <div style="background: #2a2a2a; border-left: 4px solid {urgency_color}; border-radius: 0 10px 10px 0;
                        padding: 16px 20px; margin-bottom: 12px; display: flex; justify-content: space-between;
                        align-items: center;">
                <div>
                    <div style="color: #ececec; font-weight: 600; font-size: 0.95rem; margin-bottom: 6px;">
                        {item['product_name']}
                        <span style="color: #555; font-size: 0.8rem; margin-left: 8px;">{item['product_id']}</span>
                    </div>
                    <div style="color: #999; font-size: 0.82rem;">
                        <span style="color: #ccc; font-weight: 500;">{item['stock_quantity']} units</span> remaining
                        &nbsp;·&nbsp; ~<span style="color: {urgency_color}; font-weight: 600;">{days} days</span> to stockout
                    </div>
                </div>
                <div style="text-align: right; min-width: 120px;">
                    <div style="color: {urgency_color}; font-weight: 700; font-size: 1.15rem;">
                        ₹{item['revenue_at_risk']:,.0f}</div>
                    <div style="color: #666; font-size: 0.72rem; text-transform: uppercase;
                                letter-spacing: 0.5px;">revenue at risk</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    else:
        st.success("No critical stockout risks today.")

    st.markdown("<div style='margin-top: 36px;'></div>", unsafe_allow_html=True)

    # ---- Two columns: Worst Rated + Pricing Flag ----
    col1, col2 = st.columns(2, gap="medium")

    with col1:
        wp = data["worst_product"]
        st.markdown(f"""
        <div style="margin-bottom: 12px;">
            <h3 style="color: #ffa500; font-size: 1.05rem; font-weight: 700; margin-bottom: 4px;">
                Worst-Rated Product</h3>
        </div>
        <div style="background: #2a2a2a; border-radius: 12px; padding: 20px; border: 1px solid #333;">
            <div style="color: #ececec; font-weight: 600; font-size: 1rem; margin-bottom: 6px;">
                {wp['name']}</div>
            <div style="color: #666; font-size: 0.82rem; margin-bottom: 12px;">{wp['id']}</div>
            <div style="margin-bottom: 14px;">
                <span style="color: #ffa500; font-size: 2rem; font-weight: 700;">{wp['rating']}</span>
                <span style="color: #666; font-size: 0.9rem;"> / 5.0</span>
            </div>
            <div style="color: #aaa; font-size: 0.85rem; font-style: italic; border-left: 3px solid #ffa500;
                        padding: 8px 12px; background: rgba(255,165,0,0.05); border-radius: 0 6px 6px 0;">
                {wp['reason']}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        pr = data["pricing"]
        margin_color = "#ff6b6b" if pr["is_low"] else "#10a37f"
        st.markdown(f"""
        <div style="margin-bottom: 12px;">
            <h3 style="color: #10a37f; font-size: 1.05rem; font-weight: 700; margin-bottom: 4px;">
                Pricing Flag</h3>
        </div>
        <div style="background: #2a2a2a; border-radius: 12px; padding: 20px; border: 1px solid #333;">
            <div style="color: #ececec; font-weight: 600; font-size: 1rem; margin-bottom: 6px;">
                {pr['product_name']}</div>
            <span style="color: #666; font-size: 0.8rem;">{pr['product_id']} · Lowest margin</span>
            <div style="margin: 10px 0;">
                <span style="color: {margin_color}; font-size: 1.6rem; font-weight: 700;">{pr['margin']}%</span>
                <span style="color: #666; font-size: 0.85rem;"> gross margin</span>
            </div>
            <div style="color: #999; font-size: 0.82rem; border-left: 2px solid {margin_color};
                        padding-left: 10px;">
                {"⚠ Below 25% — consider renegotiating supplier costs or adjusting price." if pr["is_low"]
                 else "✓ All margins healthy. No action needed."}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)

    # ---- Category Performance Table ----
    cat_df = data["category_data"]

    st.markdown("""
    <div style="margin-bottom: 8px;">
        <span style="color: #8e8e8e; font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
                     letter-spacing: 1px;">📊 CATEGORY PERFORMANCE</span>
    </div>
    """, unsafe_allow_html=True)

    st.dataframe(
        cat_df.style.format({
            "Avg Rating": "{:.1f}",
            "Avg Margin %": "{:.1f}%",
        }).apply(
            lambda x: ["color: #ff6b6b" if v > 0 else "color: #10a37f" for v in x]
            if x.name == "At Risk" else [""] * len(x),
            axis=0,
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")


# --- Render Briefing ---
if st.session_state.briefing_data:
    render_daily_briefing(st.session_state.briefing_data)

# =============================================================================
# Chat Response Component Renderers
# =============================================================================
def _chat_label(role: str):
    """Render a styled text label (RetailMind / User) at the top of a chat message."""
    if role == "assistant":
        st.markdown(
            '<div style="color: #10a37f; font-size: 0.78rem; font-weight: 700; margin-bottom: 2px;">RetailMind</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="color: #ececec; font-size: 0.78rem; font-weight: 700; margin-bottom: 2px;">User</div>',
            unsafe_allow_html=True,
        )


def _render_inventory_component(data: dict):
    """Render an inventory health card for a single product."""
    status = data.get("status", "Healthy")
    colors = {"Critical": "#ff4444", "Low": "#ff8c00", "Healthy": "#10a37f"}
    color = colors.get(status, "#10a37f")
    days = data.get("days_to_stockout", "N/A")

    st.markdown(f"""
    <div style="background: #2a2a2a; border-left: 4px solid {color}; border-radius: 0 10px 10px 0;
                padding: 16px 20px; margin: 8px 0 16px 0;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="color: #ececec; font-weight: 600; font-size: 0.95rem; margin-bottom: 6px;">
                    {data.get('product_name', '')}
                    <span style="color: #555; font-size: 0.8rem; margin-left: 8px;">{data.get('product_id', '')}</span>
                </div>
                <div style="color: #999; font-size: 0.82rem;">
                    <span style="color: #ccc; font-weight: 500;">{data.get('current_stock', 0)} units</span> remaining
                    &nbsp;&middot;&nbsp; Sells ~{data.get('avg_daily_sales', 0)}/day
                    &nbsp;&middot;&nbsp; <span style="color: {color}; font-weight: 600;">~{days} days</span> to stockout
                </div>
            </div>
            <div>
                <span style="background: {color}18; color: {color}; padding: 4px 14px; border-radius: 20px;
                             font-weight: 600; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.5px;">
                    {status}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_restock_component(data: list):
    """Render stockout alert cards (same style as daily briefing)."""
    if not data:
        return
    for item in data[:5]:
        days = item.get("days_to_stockout", 0)
        urgency_color = "#ff4444" if days < 1 else "#ff8c00" if days < 3 else "#ffd700"
        rev = item.get("revenue_at_risk", 0)
        rev_fmt = f"\u20b9{rev:,.0f}" if isinstance(rev, (int, float)) else str(rev)
        st.markdown(f"""
        <div style="background: #2a2a2a; border-left: 4px solid {urgency_color}; border-radius: 0 10px 10px 0;
                    padding: 14px 18px; margin-bottom: 8px; display: flex; justify-content: space-between;
                    align-items: center;">
            <div>
                <div style="color: #ececec; font-weight: 600; font-size: 0.92rem; margin-bottom: 4px;">
                    {item.get('product_name', '')}
                    <span style="color: #555; font-size: 0.78rem; margin-left: 8px;">{item.get('product_id', '')}</span>
                </div>
                <div style="color: #999; font-size: 0.8rem;">
                    <span style="color: #ccc; font-weight: 500;">{item.get('stock_quantity', 0)} units</span> left
                    &nbsp;&middot;&nbsp; ~<span style="color: {urgency_color}; font-weight: 600;">{days} days</span>
                </div>
            </div>
            <div style="text-align: right; min-width: 100px;">
                <div style="color: {urgency_color}; font-weight: 700; font-size: 1.05rem;">{rev_fmt}</div>
                <div style="color: #666; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.5px;">
                    revenue at risk</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)


def _render_pricing_component(data: dict):
    """Render a pricing analysis card."""
    if data.get("type") == "catalog_overview":
        low = data.get("lowest_margin_product", {})
        high = data.get("highest_margin_product", {})
        avg = data.get("avg_margin_pct", 0)
        st.markdown(f"""
        <div style="background: #2a2a2a; border-radius: 12px; padding: 18px 22px; margin: 8px 0 16px 0;
                    border: 1px solid #333;">
            <div style="color: #8e8e8e; font-size: 0.7rem; font-weight: 600; text-transform: uppercase;
                        letter-spacing: 1px; margin-bottom: 14px;">PRICING OVERVIEW</div>
            <div style="display: flex; gap: 24px; margin-bottom: 14px;">
                <div>
                    <div style="color: #666; font-size: 0.75rem;">Avg Margin</div>
                    <div style="color: #ececec; font-size: 1.4rem; font-weight: 700;">{avg}%</div>
                </div>
                <div>
                    <div style="color: #666; font-size: 0.75rem;">Highest</div>
                    <div style="color: #10a37f; font-size: 1.1rem; font-weight: 600;">{high.get('gross_margin_pct', 0)}%</div>
                    <div style="color: #888; font-size: 0.78rem;">{high.get('product_name', '')}</div>
                </div>
                <div>
                    <div style="color: #666; font-size: 0.75rem;">Lowest</div>
                    <div style="color: #ff6b6b; font-size: 1.1rem; font-weight: 600;">{low.get('gross_margin_pct', 0)}%</div>
                    <div style="color: #888; font-size: 0.78rem;">{low.get('product_name', '')}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        margin = data.get("gross_margin_pct", 0)
        is_low = data.get("low_margin_flag", False)
        color = "#ff6b6b" if is_low else "#10a37f"
        price = data.get("price", 0)
        cost = data.get("cost", 0)
        price_fmt = f"\u20b9{price:,.0f}" if isinstance(price, (int, float)) else str(price)
        cost_fmt = f"\u20b9{cost:,.0f}" if isinstance(cost, (int, float)) else str(cost)
        st.markdown(f"""
        <div style="background: #2a2a2a; border-left: 4px solid {color}; border-radius: 0 10px 10px 0;
                    padding: 16px 20px; margin: 8px 0 16px 0;">
            <div style="color: #ececec; font-weight: 600; font-size: 0.95rem; margin-bottom: 6px;">
                {data.get('product_name', '')}
                <span style="color: #555; font-size: 0.8rem; margin-left: 8px;">{data.get('product_id', '')}</span>
            </div>
            <div style="display: flex; gap: 20px; align-items: baseline; margin-bottom: 8px;">
                <div>
                    <span style="color: {color}; font-size: 1.6rem; font-weight: 700;">{margin}%</span>
                    <span style="color: #666; font-size: 0.82rem;"> margin</span>
                </div>
                <div style="color: #999; font-size: 0.82rem;">
                    {price_fmt} price &nbsp;&middot;&nbsp; {cost_fmt} cost
                    &nbsp;&middot;&nbsp; <span style="color: #ccc; font-weight: 500;">{data.get('price_positioning', '')}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def _render_review_component(data: dict):
    """Render a review insights card with rating, summary, and themes."""
    rating = data.get("avg_rating", 0)
    rating_color = "#ff4444" if rating < 3 else "#ffa500" if rating < 4 else "#10a37f"

    pos_themes = data.get("positive_themes", [])
    neg_themes = data.get("negative_themes", [])
    pos_html = " ".join(
        f'<span style="background: #10a37f18; color: #10a37f; padding: 3px 10px; border-radius: 12px; '
        f'font-size: 0.78rem; margin-right: 6px;">{t}</span>' for t in pos_themes
    )
    neg_html = " ".join(
        f'<span style="background: #ff6b6b18; color: #ff6b6b; padding: 3px 10px; border-radius: 12px; '
        f'font-size: 0.78rem; margin-right: 6px;">{t}</span>' for t in neg_themes
    )

    st.markdown(f"""
    <div style="background: #2a2a2a; border-radius: 12px; padding: 18px 22px; margin: 8px 0 16px 0;
                border: 1px solid #333;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
            <div>
                <div style="color: #ececec; font-weight: 600; font-size: 0.95rem; margin-bottom: 4px;">
                    {data.get('product_name', '')}</div>
                <div style="color: #666; font-size: 0.8rem;">{data.get('product_id', '')} &middot; {data.get('total_reviews', 0)} reviews</div>
            </div>
            <div style="text-align: right;">
                <span style="color: {rating_color}; font-size: 1.8rem; font-weight: 700;">{rating}</span>
                <span style="color: #666; font-size: 0.85rem;"> / 5.0</span>
            </div>
        </div>
        <div style="color: #aaa; font-size: 0.85rem; font-style: italic; border-left: 3px solid {rating_color};
                    padding: 8px 12px; margin-bottom: 14px; background: {rating_color}08; border-radius: 0 6px 6px 0;">
            {data.get('summary', '')}</div>
        <div style="margin-bottom: 6px;">
            <span style="color: #666; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.5px;">Positive: </span>
            {pos_html}
        </div>
        <div>
            <span style="color: #666; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.5px;">Negative: </span>
            {neg_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_category_component(data: dict):
    """Render a category performance card with stats and top products."""
    critical = data.get("critical_stock_items", 0)
    low = data.get("low_stock_items", 0)
    risk_color = "#ff4444" if critical > 0 else "#10a37f"

    top3 = data.get("top_3_revenue_products", [])
    top3_html = ""
    for i, p in enumerate(top3, 1):
        rev = p.get("estimated_daily_revenue", 0)
        rev_fmt = f"\u20b9{rev:,.0f}" if isinstance(rev, (int, float)) else str(rev)
        border = "border-bottom: 1px solid #333;" if i < len(top3) else ""
        top3_html += (
            f'<div style="display: flex; justify-content: space-between; padding: 6px 0; {border}">'
            f'<span style="color: #ccc; font-size: 0.82rem;">{i}. {p.get("product_name", "")}</span>'
            f'<span style="color: #10a37f; font-size: 0.82rem; font-weight: 600;">{rev_fmt}/day</span>'
            f'</div>'
        )

    stock_total = data.get("total_stock_units", 0)
    stock_fmt = f"{stock_total:,}" if isinstance(stock_total, (int, float)) else str(stock_total)

    st.markdown(f"""
    <div style="background: #2a2a2a; border-radius: 12px; padding: 18px 22px; margin: 8px 0 16px 0;
                border: 1px solid #333;">
        <div style="color: #ececec; font-weight: 700; font-size: 1.05rem; margin-bottom: 14px;">
            {data.get('category', '')}
            <span style="color: #555; font-size: 0.82rem; font-weight: 400; margin-left: 8px;">
                {data.get('total_skus', 0)} SKUs</span>
        </div>
        <div style="display: flex; gap: 16px; margin-bottom: 16px;">
            <div style="flex: 1; background: #212121; border-radius: 8px; padding: 10px 14px; text-align: center;">
                <div style="color: #666; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.5px;">Rating</div>
                <div style="color: #ececec; font-size: 1.2rem; font-weight: 700;">{data.get('avg_rating', 0)}</div>
            </div>
            <div style="flex: 1; background: #212121; border-radius: 8px; padding: 10px 14px; text-align: center;">
                <div style="color: #666; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.5px;">Margin</div>
                <div style="color: #ececec; font-size: 1.2rem; font-weight: 700;">{data.get('avg_margin_pct', 0)}%</div>
            </div>
            <div style="flex: 1; background: #212121; border-radius: 8px; padding: 10px 14px; text-align: center;">
                <div style="color: #666; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.5px;">Stock</div>
                <div style="color: #ececec; font-size: 1.2rem; font-weight: 700;">{stock_fmt}</div>
            </div>
            <div style="flex: 1; background: #212121; border-radius: 8px; padding: 10px 14px; text-align: center;">
                <div style="color: #666; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.5px;">At Risk</div>
                <div style="color: {risk_color}; font-size: 1.2rem; font-weight: 700;">{critical + low}</div>
            </div>
        </div>
        <div style="color: #8e8e8e; font-size: 0.7rem; font-weight: 600; text-transform: uppercase;
                    letter-spacing: 1px; margin-bottom: 8px;">TOP REVENUE PRODUCTS</div>
        {top3_html}
    </div>
    """, unsafe_allow_html=True)


def _render_search_component(data: list):
    """Render search results as compact product cards."""
    if not data:
        return
    for item in data:
        rating = item.get("avg_rating", 0)
        rating_color = "#ff4444" if rating < 3 else "#ffa500" if rating < 4 else "#10a37f"
        price = item.get("price", 0)
        price_fmt = f"\u20b9{price:,.0f}" if isinstance(price, (int, float)) else str(price)
        st.markdown(f"""
        <div style="background: #2a2a2a; border-radius: 10px; padding: 14px 18px; margin-bottom: 8px;
                    border: 1px solid #333; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="color: #ececec; font-weight: 600; font-size: 0.92rem;">
                    {item.get('product_name', '')}
                    <span style="color: #555; font-size: 0.78rem; margin-left: 8px;">{item.get('product_id', '')}</span>
                </div>
                <div style="color: #888; font-size: 0.8rem; margin-top: 4px;">
                    {item.get('category', '')} &nbsp;&middot;&nbsp; {price_fmt}
                    &nbsp;&middot;&nbsp; {item.get('stock_quantity', 0)} in stock
                </div>
            </div>
            <div>
                <span style="color: {rating_color}; font-size: 1.1rem; font-weight: 700;">{rating}</span>
                <span style="color: #666; font-size: 0.75rem;"> / 5</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)


def render_tool_components(tool_results: list):
    """Dispatch tool results to the appropriate component renderer."""
    if not tool_results:
        return
    for tr in tool_results:
        name = tr["tool_name"]
        result = tr["result"]
        # Skip error results
        if isinstance(result, dict) and "error" in result:
            continue
        if name == "get_inventory_health":
            _render_inventory_component(result)
        elif name == "generate_restock_alert":
            _render_restock_component(result)
        elif name == "get_pricing_analysis":
            _render_pricing_component(result)
        elif name == "get_review_insights":
            _render_review_component(result)
        elif name == "get_category_performance":
            _render_category_component(result)
        elif name == "search_products":
            _render_search_component(result)


# --- Display Chat Messages ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        _chat_label(msg["role"])
        if msg.get("tool_results"):
            render_tool_components(msg["tool_results"])
        st.markdown(msg["content"])

# --- Chat Input ---
if user_input := st.chat_input("Message RetailMind..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        _chat_label("user")
        st.markdown(user_input)

    with st.chat_message("assistant"):
        _chat_label("assistant")
        with st.spinner("Thinking..."):
            response_text, updated_history, tool_results = run_agent(
                user_message=user_input,
                conversation_history=st.session_state.conversation_history,
                category_filter=category_filter,
            )
            render_tool_components(tool_results)
            st.markdown(response_text)

    st.session_state.messages.append({"role": "assistant", "content": response_text, "tool_results": tool_results})
    st.session_state.conversation_history = updated_history
