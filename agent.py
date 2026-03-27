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
from config import (
    get_llm_client, MODEL_NAME,
    LLM_TEMPERATURE, LLM_TOP_P, LLM_MAX_TOKENS,
    SUMMARY_TEMPERATURE, SUMMARY_MAX_TOKENS,
    BRIEFING_MARGIN_THRESHOLD,
)
from tools import TOOL_SCHEMAS, TOOL_FUNCTIONS, generate_restock_alert
from data_loader import get_products_df, get_reviews_df


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
   → Call `get_pricing_analysis(product_id)` for a specific product
   → Call `get_pricing_analysis()` without product_id for catalog-wide pricing overview
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
- Maintain conversation context for follow-up questions.
- If a category filter is active, mention it in your response and scope your analysis accordingly.

## Response Formatting Rules
Format every response using rich markdown for readability:

- **Start with a one-line summary** in bold that directly answers the question
- Use **### Subheadings** to organize sections (e.g., ### Inventory Status, ### Recommendation)
- Use **bold** for product names, key numbers, and status labels (e.g., **Critical**, **INR 2,999**)
- Use bullet points (`-`) for listing multiple items or metrics
- Use markdown tables when comparing 3+ products side by side
- Use `>` blockquotes for actionable recommendations or key insights
- Add a **### Recommendation** section at the end with 1-2 actionable business suggestions
- Keep paragraphs short (2-3 sentences max)
- Use line breaks between sections for visual breathing room

Example structure:
```
**Direct answer to the question in one line.**

### Section Heading
- **Metric 1:** Value
- **Metric 2:** Value

### Recommendation
> Actionable business insight here.
```
"""


def run_agent(user_message: str, conversation_history: list, category_filter: str = None) -> tuple[str, list, list]:
    """
    Process a user message through the LLM router agent.

    Args:
        user_message: The user's natural language query
        conversation_history: List of prior messages (OpenAI format)
        category_filter: Optional active category filter from the UI sidebar

    Returns:
        Tuple of (assistant_response_text, updated_conversation_history, tool_results)
        tool_results is a list of {"tool_name": str, "result": dict|list} for UI rendering
    """
    client = get_llm_client()

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

    tool_results = []  # Collect tool call results for UI component rendering

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
        error_msg = f"Sorry, I encountered an issue connecting to the AI service. Please try again. (Error: {e})"
        updated_history = conversation_history.copy()
        updated_history.append({"role": "user", "content": user_message})
        updated_history.append({"role": "assistant", "content": error_msg})
        return error_msg, updated_history, []

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

            # Capture raw result for UI component rendering
            tool_results.append({"tool_name": fn_name, "result": result})

            # Add tool result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, default=str),
            })

        # Call the LLM again with tool results to generate a natural language response
        try:
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
        except Exception as e:
            # If the follow-up LLM call fails, return a graceful error
            response_text = f"I retrieved the data but couldn't generate a summary. Please try again. (Error: {e})"
            updated_history = conversation_history.copy()
            updated_history.append({"role": "user", "content": user_message})
            updated_history.append({"role": "assistant", "content": response_text})
            return response_text, updated_history, tool_results

    # Extract the final text response
    response_text = assistant_message.content or "I couldn't generate a response. Please try again."

    # Update conversation history (keep it lean — only user + assistant text messages)
    updated_history = conversation_history.copy()
    updated_history.append({"role": "user", "content": user_message})
    updated_history.append({"role": "assistant", "content": response_text})

    return response_text, updated_history, tool_results


# =============================================================================
# Daily Briefing Generator
# =============================================================================
def _llm_summarize_complaints(product_name: str, review_texts: str) -> str:
    """Use LLM to generate a one-line summary of why customers are unhappy."""
    client = get_llm_client()
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a concise retail analyst. Answer in one sentence only."},
                {"role": "user", "content": (
                    f"Based on these negative reviews for '{product_name}', "
                    f"write ONE sentence explaining why customers are unhappy:\n\n{review_texts}"
                )},
            ],
            temperature=SUMMARY_TEMPERATURE,
            max_tokens=100,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "Customer feedback indicates quality and delivery concerns."


def generate_daily_briefing() -> dict:
    """
    Generate structured daily briefing data for the UI to render.
    Returns a dict with all data needed for rich Streamlit rendering.
    """
    import pandas as pd
    df = get_products_df()
    reviews_df = get_reviews_df()

    # --- 1. Stockout Risks ---
    restock_alerts = generate_restock_alert(threshold_days=7)
    top3_alerts = restock_alerts[:3]

    # --- 2. Worst-Rated Product (with LLM summary) ---
    worst = df.loc[df["avg_rating"].idxmin()]
    worst_reviews = reviews_df[reviews_df["product_id"] == worst["product_id"]]

    if not worst_reviews.empty:
        low_reviews = worst_reviews[worst_reviews["rating"] <= 3]
        if not low_reviews.empty:
            review_texts = "\n".join(
                f"- {r['review_title']}: {r['review_text']}"
                for _, r in low_reviews.iterrows()
            )
            unhappy_reason = _llm_summarize_complaints(worst["product_name"], review_texts)
        else:
            unhappy_reason = "Mixed reviews with room for improvement."
    else:
        unhappy_reason = "Limited review data available."

    # --- 3. Pricing Flag ---
    df_copy = df.copy()
    df_copy["gross_margin"] = round((df_copy["price"] - df_copy["cost"]) / df_copy["price"] * 100, 1)
    lowest_margin = df_copy.loc[df_copy["gross_margin"].idxmin()]
    margin_val = round(lowest_margin["gross_margin"], 1)

    # --- 4. Category health data for chart ---
    category_data = []
    for cat in df["category"].unique():
        cat_df = df_copy[df_copy["category"] == cat]
        cat_stock = cat_df.copy()
        cat_stock["days_to_stockout"] = cat_stock.apply(
            lambda r: r["stock_quantity"] / r["avg_daily_sales"] if r["avg_daily_sales"] > 0 else float("inf"),
            axis=1,
        )
        critical = int((cat_stock["days_to_stockout"] < 7).sum())
        category_data.append({
            "Category": cat,
            "SKUs": len(cat_df),
            "Avg Rating": round(cat_df["avg_rating"].mean(), 1),
            "Avg Margin %": round(cat_df["gross_margin"].mean(), 1),
            "Total Stock": int(cat_df["stock_quantity"].sum()),
            "At Risk": critical,
        })

    return {
        "stockout_alerts": top3_alerts,
        "all_alerts_count": len(restock_alerts),
        "worst_product": {
            "name": worst["product_name"],
            "id": worst["product_id"],
            "rating": worst["avg_rating"],
            "reason": unhappy_reason,
        },
        "pricing": {
            "product_name": lowest_margin["product_name"],
            "product_id": lowest_margin["product_id"],
            "margin": margin_val,
            "is_low": margin_val < BRIEFING_MARGIN_THRESHOLD,
        },
        "category_data": pd.DataFrame(category_data),
    }
