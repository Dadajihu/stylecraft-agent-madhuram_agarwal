"""
Tool-Calling Layer for RetailMind Product Intelligence Agent.
Implements 6 tools callable by the LLM, plus their OpenAI-format schemas.
"""

import json
from openai import OpenAI
from data_loader import get_products_df, get_reviews_df
from config import (
    OPENAI_API_KEY, API_BASE_URL, MODEL_NAME,
    SUMMARY_TEMPERATURE, SUMMARY_MAX_TOKENS,
    STOCKOUT_CRITICAL_DAYS, STOCKOUT_LOW_DAYS,
    LOW_MARGIN_THRESHOLD, LLM_TOP_P,
)

# Cache for review insights to avoid redundant LLM calls
_review_cache: dict = {}


def _get_llm_client():
    """Create an OpenAI client for review summarization."""
    kwargs = {"api_key": OPENAI_API_KEY}
    if API_BASE_URL:
        kwargs["base_url"] = API_BASE_URL
    return OpenAI(**kwargs)


# =============================================================================
# Tool 1: search_products
# =============================================================================
def search_products(query: str, category: str = None) -> list[dict]:
    """
    Search and return matching products from the catalog based on a text query
    and optional category filter. Returns top 5 matches with key details.
    """
    df = get_products_df()

    # Apply category filter if provided
    if category and category != "All Categories":
        df = df[df["category"].str.lower() == category.lower()]

    # Case-insensitive substring matching on product_name
    mask = df["product_name"].str.lower().str.contains(query.lower(), na=False)

    # If no direct match, try matching on category or product_id
    if mask.sum() == 0:
        mask = (
            df["product_name"].str.lower().str.contains(query.lower(), na=False)
            | df["category"].str.lower().str.contains(query.lower(), na=False)
            | df["product_id"].str.lower().str.contains(query.lower(), na=False)
        )

    results = df[mask].head(5)

    # If still no results, return all products (limited to 5) as fallback
    if results.empty:
        results = df.head(5)

    return results[
        ["product_id", "product_name", "category", "price", "stock_quantity", "avg_rating"]
    ].to_dict(orient="records")


# =============================================================================
# Tool 2: get_inventory_health
# =============================================================================
def get_inventory_health(product_id: str) -> dict:
    """
    Return inventory status for a product: current stock, average daily sales,
    estimated days to stockout, and a status flag (Critical / Low / Healthy).
    """
    df = get_products_df()
    product = df[df["product_id"] == product_id.upper()]

    if product.empty:
        return {"error": f"Product {product_id} not found"}

    row = product.iloc[0]
    stock = int(row["stock_quantity"])
    avg_daily_sales = float(row["avg_daily_sales"])

    # Handle division by zero: if no sales, stockout risk is effectively zero
    if avg_daily_sales == 0:
        days_to_stockout = float("inf")
        status = "Healthy"
    else:
        days_to_stockout = round(stock / avg_daily_sales, 1)
        if days_to_stockout < STOCKOUT_CRITICAL_DAYS:
            status = "Critical"
        elif days_to_stockout < STOCKOUT_LOW_DAYS:
            status = "Low"
        else:
            status = "Healthy"

    return {
        "product_id": row["product_id"],
        "product_name": row["product_name"],
        "current_stock": stock,
        "avg_daily_sales": avg_daily_sales,
        "days_to_stockout": days_to_stockout if days_to_stockout != float("inf") else "N/A (no sales)",
        "status": status,
        "reorder_level": int(row["reorder_level"]),
        "needs_reorder": stock <= int(row["reorder_level"]),
    }


# =============================================================================
# Tool 3: get_pricing_analysis
# =============================================================================
def get_pricing_analysis(product_id: str = None) -> dict:
    """
    Return pricing intelligence: gross margin %, price positioning
    (Premium / Mid-Range / Budget), and a flag if margin is below 20%.
    When product_id is omitted, returns a catalog-wide pricing overview
    with the lowest and highest margin products.
    """
    df = get_products_df()

    # Catalog-wide pricing overview when no product_id is given
    if not product_id or product_id.strip() == "":
        df = df.copy()
        df["gross_margin"] = round((df["price"] - df["cost"]) / df["price"] * 100, 2)
        lowest = df.loc[df["gross_margin"].idxmin()]
        highest = df.loc[df["gross_margin"].idxmax()]
        low_margin_products = df[df["gross_margin"] < LOW_MARGIN_THRESHOLD]
        return {
            "type": "catalog_overview",
            "avg_margin_pct": round(df["gross_margin"].mean(), 2),
            "lowest_margin_product": {
                "product_id": lowest["product_id"],
                "product_name": lowest["product_name"],
                "gross_margin_pct": round(lowest["gross_margin"], 2),
                "price": float(lowest["price"]),
                "cost": float(lowest["cost"]),
            },
            "highest_margin_product": {
                "product_id": highest["product_id"],
                "product_name": highest["product_name"],
                "gross_margin_pct": round(highest["gross_margin"], 2),
            },
            "low_margin_count": len(low_margin_products),
            "low_margin_products": low_margin_products[
                ["product_id", "product_name", "gross_margin"]
            ].to_dict(orient="records") if not low_margin_products.empty else [],
        }

    product = df[df["product_id"] == product_id.upper()]

    if product.empty:
        return {"error": f"Product {product_id} not found"}

    row = product.iloc[0]
    price = float(row["price"])
    cost = float(row["cost"])

    # Gross margin calculation: (selling price - cost) / selling price * 100
    gross_margin = round((price - cost) / price * 100, 2)

    # Category average price for positioning comparison
    category_products = df[df["category"] == row["category"]]
    category_avg_price = round(category_products["price"].mean(), 2)

    # Price positioning based on comparison to category average
    price_ratio = price / category_avg_price
    if price_ratio > 1.2:
        positioning = "Premium"
    elif price_ratio < 0.8:
        positioning = "Budget"
    else:
        positioning = "Mid-Range"

    return {
        "product_id": row["product_id"],
        "product_name": row["product_name"],
        "category": row["category"],
        "price": price,
        "cost": cost,
        "gross_margin_pct": gross_margin,
        "category_avg_price": category_avg_price,
        "price_positioning": positioning,
        "low_margin_flag": gross_margin < LOW_MARGIN_THRESHOLD,
        "margin_warning": f"Warning: Margin ({gross_margin}%) is below {LOW_MARGIN_THRESHOLD}%"
        if gross_margin < LOW_MARGIN_THRESHOLD
        else None,
    }


# =============================================================================
# Tool 4: get_review_insights
# =============================================================================
def get_review_insights(product_id: str) -> dict:
    """
    Use an LLM to summarise customer reviews for a given product.
    Returns: average rating, total reviews, a 2-sentence sentiment summary,
    and top 2 recurring themes (positive and negative).
    """
    # Return cached result if available (avoids redundant LLM calls)
    cache_key = product_id.upper()
    if cache_key in _review_cache:
        return _review_cache[cache_key]

    products_df = get_products_df()
    reviews_df = get_reviews_df()

    product = products_df[products_df["product_id"] == product_id.upper()]
    if product.empty:
        return {"error": f"Product {product_id} not found"}

    row = product.iloc[0]
    product_reviews = reviews_df[reviews_df["product_id"] == product_id.upper()]

    if product_reviews.empty:
        return {
            "product_id": row["product_id"],
            "product_name": row["product_name"],
            "avg_rating": float(row["avg_rating"]),
            "total_reviews": int(row["review_count"]),
            "summary": "No detailed reviews available for analysis.",
            "positive_themes": [],
            "negative_themes": [],
        }

    # Concatenate all review texts for LLM summarization
    review_texts = "\n".join(
        f"- Rating: {r['rating']}/5 | {r['review_title']}: {r['review_text']}"
        for _, r in product_reviews.iterrows()
    )

    # Calculate average rating from actual reviews
    avg_rating = round(product_reviews["rating"].mean(), 1)

    # Call LLM for summarization
    client = _get_llm_client()
    prompt = f"""Analyze these reviews for "{row['product_name']}". Reply with ONLY a JSON object, no markdown, no explanation.

Reviews:
{review_texts}

Return ONLY this JSON (keep values short and concise):
{{"summary": "Two sentences max.", "positive_themes": ["theme1", "theme2"], "negative_themes": ["theme1", "theme2"]}}"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a concise analyst. Reply with ONLY valid JSON, no markdown fences, no extra text."},
                {"role": "user", "content": prompt},
            ],
            # Low temperature for factual, consistent review summarization
            temperature=SUMMARY_TEMPERATURE,
            top_p=LLM_TOP_P,
            max_tokens=1024,  # Generous limit to avoid truncated JSON responses
        )
        result_text = response.choices[0].message.content.strip()
        # Parse JSON from LLM response (handle potential markdown wrapping)
        if "```" in result_text:
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()
        parsed = json.loads(result_text)
    except Exception:
        # Fallback if LLM call fails
        parsed = {
            "summary": "Review analysis is temporarily unavailable.",
            "positive_themes": ["Unable to analyze"],
            "negative_themes": ["Unable to analyze"],
        }

    result = {
        "product_id": row["product_id"],
        "product_name": row["product_name"],
        "avg_rating": avg_rating,
        "total_reviews": len(product_reviews),
        "summary": parsed.get("summary", ""),
        "positive_themes": parsed.get("positive_themes", []),
        "negative_themes": parsed.get("negative_themes", []),
    }

    # Cache the result for future calls
    _review_cache[cache_key] = result
    return result


# =============================================================================
# Tool 5: get_category_performance
# =============================================================================
def get_category_performance(category: str) -> dict:
    """
    Return aggregated category-level metrics: total SKUs, average rating,
    average margin %, total stock, low/critical stock count, and top 3
    revenue-generating products.
    """
    df = get_products_df()
    cat_df = df[df["category"].str.lower() == category.lower()]

    if cat_df.empty:
        return {"error": f"Category '{category}' not found"}

    # Compute margins for all products in category
    cat_df = cat_df.copy()
    cat_df["gross_margin"] = (cat_df["price"] - cat_df["cost"]) / cat_df["price"] * 100
    cat_df["days_to_stockout"] = cat_df.apply(
        lambda r: r["stock_quantity"] / r["avg_daily_sales"] if r["avg_daily_sales"] > 0 else float("inf"),
        axis=1,
    )
    cat_df["estimated_daily_revenue"] = cat_df["price"] * cat_df["avg_daily_sales"]

    # Count low and critical stock items
    critical_count = int((cat_df["days_to_stockout"] < STOCKOUT_CRITICAL_DAYS).sum())
    low_count = int(
        ((cat_df["days_to_stockout"] >= STOCKOUT_CRITICAL_DAYS) & (cat_df["days_to_stockout"] < STOCKOUT_LOW_DAYS)).sum()
    )

    # Top 3 revenue-generating products
    top3 = cat_df.nlargest(3, "estimated_daily_revenue")[
        ["product_id", "product_name", "price", "avg_daily_sales", "estimated_daily_revenue"]
    ].to_dict(orient="records")

    return {
        "category": category,
        "total_skus": len(cat_df),
        "avg_rating": round(cat_df["avg_rating"].mean(), 2),
        "avg_margin_pct": round(cat_df["gross_margin"].mean(), 2),
        "total_stock_units": int(cat_df["stock_quantity"].sum()),
        "critical_stock_items": critical_count,
        "low_stock_items": low_count,
        "top_3_revenue_products": top3,
    }


# =============================================================================
# Tool 6: generate_restock_alert
# =============================================================================
def generate_restock_alert(threshold_days: int = 7) -> list[dict]:
    """
    Scan all products and return those at risk of stockout within the
    specified number of days, sorted by urgency (fewest days first).
    Includes estimated revenue at risk.
    """
    df = get_products_df().copy()

    # Compute days to stockout for all products
    df["days_to_stockout"] = df.apply(
        lambda r: round(r["stock_quantity"] / r["avg_daily_sales"], 1) if r["avg_daily_sales"] > 0 else float("inf"),
        axis=1,
    )

    # Filter products at risk within the threshold
    at_risk = df[df["days_to_stockout"] <= threshold_days].copy()

    # Revenue at risk = price * avg_daily_sales * threshold_days
    at_risk["revenue_at_risk"] = round(at_risk["price"] * at_risk["avg_daily_sales"] * threshold_days, 2)

    # Sort by urgency (fewest days remaining first)
    at_risk = at_risk.sort_values("days_to_stockout", ascending=True)

    return at_risk[
        ["product_id", "product_name", "category", "stock_quantity",
         "avg_daily_sales", "days_to_stockout", "revenue_at_risk"]
    ].to_dict(orient="records")


# =============================================================================
# OpenAI Tool Schemas
# Properly defined schemas so the LLM knows when and how to call each tool.
# =============================================================================
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": (
                "Search and return matching products from the catalog based on a text query "
                "and optional category filter. Use this when the user asks to find, look up, "
                "or browse products by name, keyword, or category. Returns top 5 matches."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search text to match against product names (e.g., 'dress', 'cotton', 'jacket')",
                    },
                    "category": {
                        "type": "string",
                        "enum": ["Tops", "Dresses", "Bottoms", "Outerwear", "Accessories"],
                        "description": "Optional category filter to narrow results",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_inventory_health",
            "description": (
                "Return inventory health status for a specific product including current stock, "
                "average daily sales, estimated days to stockout, and urgency status "
                "(Critical / Low / Healthy). Use this when the user asks about stock levels, "
                "stockout risk, restock needs, or how long inventory will last for a specific product."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "The product ID (e.g., 'SC001', 'SC015')",
                    },
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pricing_analysis",
            "description": (
                "Return pricing intelligence: gross margin percentage, price positioning "
                "(Premium / Mid-Range / Budget), and margin flags. Pass a product_id for "
                "a specific product, or omit it for a catalog-wide pricing overview showing "
                "the lowest/highest margin products. Use this when the user asks about margins, "
                "pricing, profitability, cost efficiency, which product has the best/worst margin, "
                "or for a pricing overview."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "The product ID (e.g., 'SC001'). Omit for catalog-wide pricing overview.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_review_insights",
            "description": (
                "Get an LLM-generated summary of customer reviews for a specific product. "
                "Returns average rating, total review count, a 2-sentence sentiment summary, "
                "and top recurring positive and negative themes. Use this when the user asks "
                "about customer feedback, ratings, complaints, sentiment, or what customers think."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "The product ID (e.g., 'SC001', 'SC015')",
                    },
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_category_performance",
            "description": (
                "Return aggregated performance metrics for an entire product category: "
                "total SKUs, average rating, average margin %, total stock, count of low/critical "
                "stock items, and top 3 revenue-generating products. Use this when the user asks "
                "about category overviews, how a category is performing, or top products in a category."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["Tops", "Dresses", "Bottoms", "Outerwear", "Accessories"],
                        "description": "The product category to analyze",
                    },
                },
                "required": ["category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_restock_alert",
            "description": (
                "Scan all products and return a list of products at risk of stockout within "
                "the specified number of days, sorted by urgency. Includes estimated revenue "
                "at risk. Use this when the user asks about restock alerts, which products "
                "need reordering, or for a stockout risk overview across the entire catalog."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "threshold_days": {
                        "type": "integer",
                        "description": "Number of days threshold for stockout risk (default: 7)",
                        "default": 7,
                    },
                },
                "required": [],
            },
        },
    },
]

# Map function names to actual callables for the agent to dispatch
TOOL_FUNCTIONS = {
    "search_products": search_products,
    "get_inventory_health": get_inventory_health,
    "get_pricing_analysis": get_pricing_analysis,
    "get_review_insights": get_review_insights,
    "get_category_performance": get_category_performance,
    "generate_restock_alert": generate_restock_alert,
}
