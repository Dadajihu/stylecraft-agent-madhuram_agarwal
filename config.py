"""
Configuration module for RetailMind Product Intelligence Agent.
Loads environment variables and defines LLM parameters and constants.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- LLM Configuration ---
# Using OpenAI-compatible API (works with OpenAI, Groq, or any compatible provider)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")
# Optional: set a custom base URL for Groq or other providers
# e.g., "https://api.groq.com/openai/v1" for Groq
API_BASE_URL = os.getenv("API_BASE_URL", None)

# --- LLM Parameters (with rationale) ---

# temperature=0.3: Low temperature for accurate, deterministic data analysis.
# Higher values would risk hallucinating numbers or inconsistent calculations.
LLM_TEMPERATURE = 0.3

# top_p=0.9: Nucleus sampling allows slight creativity in natural language
# summaries while keeping outputs focused and relevant.
LLM_TOP_P = 0.9

# max_tokens=1024: Sufficient for detailed analysis responses including
# tables, bullet points, and multi-product comparisons.
LLM_MAX_TOKENS = 1024

# For review summarization, we use even lower temperature for factual accuracy
SUMMARY_TEMPERATURE = 0.2
SUMMARY_MAX_TOKENS = 512

# --- Data File Paths ---
PRODUCTS_CSV = "Set-B retailmind_products.csv"
REVIEWS_CSV = "Set-B retailmind_reviews.csv"

# --- Business Constants ---
CATEGORIES = ["Tops", "Dresses", "Bottoms", "Outerwear", "Accessories"]
STOCKOUT_CRITICAL_DAYS = 7    # Critical if less than 7 days of stock
STOCKOUT_LOW_DAYS = 14        # Low if between 7-14 days of stock
LOW_MARGIN_THRESHOLD = 20     # Flag products with margin below 20%
BRIEFING_MARGIN_THRESHOLD = 25  # Daily briefing flags margins below 25%
