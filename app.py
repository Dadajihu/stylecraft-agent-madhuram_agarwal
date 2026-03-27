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

# --- Helper to render a chat label ---
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

# --- Display Chat Messages ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        _chat_label(msg["role"])
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
            response_text, updated_history = run_agent(
                user_message=user_input,
                conversation_history=st.session_state.conversation_history,
                category_filter=category_filter,
            )
            st.markdown(response_text)

    st.session_state.messages.append({"role": "assistant", "content": response_text})
    st.session_state.conversation_history = updated_history
