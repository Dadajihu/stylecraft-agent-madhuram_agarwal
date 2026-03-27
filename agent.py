"""
Router Agent and Orchestration for RetailMind Product Intelligence Agent.

Implements an LLM-powered Router that classifies each user query and dispatches
it to the correct tool. Uses OpenAI function calling for intent classification
(NOT keyword/regex matching) — the LLM decides which tool to invoke.

Routes:
  INVENTORY  → get_inventory_health(), generate_restock_alert()
  PRICING    → get_pricing_analysis()
  REVIEWS    → get_review_insights()
  CATALOG    → search_products(), get_category_performance()
  GENERAL    → LLM responds from its own knowledge + conversation context
"""

import json
from openai import OpenAI
from config import (
    OPENAI_API_KEY, API_BASE_URL, MODEL_NAME,
    LLM_TEMPERATURE, LLM_TOP_P, LLM_MAX_TOKENS,
    SUMMARY_TEMPERATURE, SUMMARY_MAX_TOKENS,
    BRIEFING_MARGIN_THRESHOLD,
)
from tools import TOOL_SCHEMAS, TOOL_FUNCTIONS, generate_restock_alert
from data_loader import get_products_df, get_reviews_df


def _get_client():
    """Create an OpenAI client."""
    kwargs = {"api_key": OPENAI_API_KEY}
    if API_BASE_URL:
        kwargs["base_url"] = API_BASE_URL
    return OpenAI(**kwargs)


# =============================================================================
# System Prompt — defines the agent persona and routing behavior
# =============================================================================
SYSTEM_PROMPT = """You are the RetailMind Product Intelligence Assistant — an AI agent built for StyleCraft, a D2C fashion brand with 30+ SKUs across 5 categories (Tops, Dresses, Bottoms, Outerwear, Accessories).

Your role is to help StyleCraft's product manager, Priya Mehta, make data-driven merchandising decisions by analyzing the product catalog in real time.

## How You Route Queries (Intent Classification)

You have access to 6 specialized tools. Based on the user's intent, you MUST call the appropriate tool(s):

1. **INVENTORY queries** (stock levels, stockout risk, restock needs, how long inventory lasts):
   → Call `get_inventory_health(product_id)` for a specific product
   → Call `generate_restock_alert(threshold_days)` for a catalog-wide stockout scan

2. **PRICING queries** (margins, pricing tiers, profitability, cost efficiency):
   → Call `get_pricing_analysis(product_id)`
   → Highlight low-margin items and suggest pricing actions if margin < 20%

3. **REVIEW queries** (customer feedback, ratings, complaints, sentiment):
   → Call `get_review_insights(product_id)`
   → Present the sentiment summary and key themes clearly

4. **CATALOG queries** (product search, category overviews, top performers, browsing):
   → Call `search_products(query, category)` for product lookups
   → Call `get_category_performance(category)` for category-level analysis

5. **GENERAL queries** (greetings, meta questions about you, general retail knowledge):
   → Respond using your own knowledge. Use conversation context if prior data was discussed.

## Important Guidelines
- Always use tools when data is needed. Never make up numbers or product details.
- When a user mentions a product by name (not ID), first use search_products to find the product ID, then call the relevant analysis tool.
- Present data in a clear, structured format using bullet points or tables.
- Add business-relevant insights and actionable recommendations.
- Maintain conversation context for follow-up questions.
- If a category filter is active, mention it in your response and scope your analysis accordingly.
"""


def run_agent(user_message: str, conversation_history: list, category_filter: str = None) -> tuple[str, list]:
    """
    Process a user message through the LLM router agent.

    Args:
        user_message: The user's natural language query
        conversation_history: List of prior messages (OpenAI format)
        category_filter: Optional active category filter from the UI sidebar

    Returns:
        Tuple of (assistant_response_text, updated_conversation_history)
    """
    client = _get_client()

    # Build the system prompt, optionally scoped by category filter
    system_content = SYSTEM_PROMPT
    if category_filter and category_filter != "All Categories":
        system_content += (
            f"\n\n## Active Category Filter: {category_filter}\n"
            f"The user has selected '{category_filter}' in the sidebar. "
            f"Scope your analysis to this category when relevant."
        )

    messages = [{"role": "system", "content": system_content}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    # Call the LLM with tool schemas — the LLM acts as the router by choosing
    # which tool(s) to call based on the user's intent
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",  # Let the LLM decide whether and which tools to call
            temperature=LLM_TEMPERATURE,  # Low temp for consistent routing and data analysis
            top_p=LLM_TOP_P,
            max_tokens=LLM_MAX_TOKENS,
        )
    except Exception as e:
        error_msg = f"LLM API error: {e}"
        updated_history = conversation_history.copy()
        updated_history.append({"role": "user", "content": user_message})
        updated_history.append({"role": "assistant", "content": error_msg})
        return error_msg, updated_history

    assistant_message = response.choices[0].message

    # If the LLM decided to call tool(s), execute them and feed results back
    while assistant_message.tool_calls:
        # Add the assistant's tool-calling message to conversation
        messages.append(assistant_message)

        # Execute each tool call
        for tool_call in assistant_message.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)

            # Dispatch to the correct tool function
            if fn_name in TOOL_FUNCTIONS:
                result = TOOL_FUNCTIONS[fn_name](**fn_args)
            else:
                result = {"error": f"Unknown tool: {fn_name}"}

            # Add tool result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, default=str),
            })

        # Call the LLM again with tool results so it can generate a natural language response
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=LLM_TEMPERATURE,
            top_p=LLM_TOP_P,
            max_tokens=LLM_MAX_TOKENS,
        )
        assistant_message = response.choices[0].message

    # Extract the final text response
    response_text = assistant_message.content or "I couldn't generate a response. Please try again."

    # Update conversation history (keep it lean — only user + assistant text messages)
    updated_history = conversation_history.copy()
    updated_history.append({"role": "user", "content": user_message})
    updated_history.append({"role": "assistant", "content": response_text})

    return response_text, updated_history


# =============================================================================
# Daily Briefing Generator
# =============================================================================
def generate_daily_briefing() -> str:
    """
    Generate a daily briefing that runs on app startup.
    Includes:
      1. Top 3 critically low-stock products with days-to-stockout and revenue at risk
      2. Worst-rated product and a one-line summary of why customers are unhappy
      3. One pricing flag — lowest gross margin product (if below 25%)
    """
    df = get_products_df()
    reviews_df = get_reviews_df()

    # --- 1. Top 3 Stockout Risks ---
    restock_alerts = generate_restock_alert(threshold_days=7)
    top3_alerts = restock_alerts[:3]

    stockout_section = ""
    if top3_alerts:
        stockout_section = "### Stockout Alerts\n"
        for i, item in enumerate(top3_alerts, 1):
            stockout_section += (
                f"{i}. **{item['product_name']}** ({item['product_id']}) — "
                f"Only **{item['stock_quantity']} units** left, "
                f"~**{item['days_to_stockout']} days** to stockout | "
                f"Revenue at risk: **INR {item['revenue_at_risk']:,.0f}**\n"
            )
    else:
        stockout_section = "### Stockout Alerts\nNo critical stockout risks today.\n"

    # --- 2. Worst-Rated Product ---
    worst = df.loc[df["avg_rating"].idxmin()]
    worst_reviews = reviews_df[reviews_df["product_id"] == worst["product_id"]]

    # Generate a one-line summary of why customers are unhappy
    unhappy_reason = ""
    if not worst_reviews.empty:
        low_reviews = worst_reviews[worst_reviews["rating"] <= 3]
        if not low_reviews.empty:
            complaints = "; ".join(low_reviews["review_title"].tolist()[:3])
            unhappy_reason = f"Key complaints: {complaints}"
        else:
            unhappy_reason = "Mixed reviews with room for improvement"
    else:
        unhappy_reason = "Limited review data available"

    rating_section = (
        f"### Worst-Rated Product\n"
        f"**{worst['product_name']}** ({worst['product_id']}) — "
        f"Rating: **{worst['avg_rating']}/5.0** | {unhappy_reason}\n"
    )

    # --- 3. Pricing Flag ---
    df_copy = df.copy()
    df_copy["gross_margin"] = (df_copy["price"] - df_copy["cost"]) / df_copy["price"] * 100
    lowest_margin = df_copy.loc[df_copy["gross_margin"].idxmin()]
    margin_val = round(lowest_margin["gross_margin"], 1)

    if margin_val < BRIEFING_MARGIN_THRESHOLD:
        pricing_section = (
            f"### Pricing Flag\n"
            f"**{lowest_margin['product_name']}** ({lowest_margin['product_id']}) has the lowest "
            f"gross margin at **{margin_val}%**. Consider renegotiating supplier costs or "
            f"adjusting the selling price to improve profitability.\n"
        )
    else:
        pricing_section = (
            f"### Pricing Flag\n"
            f"All products have margins above {BRIEFING_MARGIN_THRESHOLD}%. "
            f"Lowest is **{lowest_margin['product_name']}** at {margin_val}%.\n"
        )

    # Combine the briefing
    briefing = (
        f"## Daily Briefing — RetailMind Product Intelligence\n\n"
        f"{stockout_section}\n"
        f"{rating_section}\n"
        f"{pricing_section}"
    )

    return briefing
