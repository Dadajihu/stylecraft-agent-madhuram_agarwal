# RetailMind Product Intelligence Agent

An AI-powered product intelligence agent built for **StyleCraft**, a D2C fashion brand. The agent answers natural language questions about the product catalog, proactively surfaces critical alerts, and supports multi-turn conversations — all through a Streamlit chat interface.

## Architecture

The agent uses an **LLM-powered Router Pattern** with OpenAI function calling:

```
User Query → LLM Router (intent classification) → Tool Execution → LLM Response
```

**Key components:**
- **`agent.py`** — LLM router that classifies user intent (INVENTORY / PRICING / REVIEWS / CATALOG / GENERAL) and dispatches to the appropriate tool via OpenAI function calling
- **`tools.py`** — 6 specialized analysis tools with properly defined schemas:
  1. `search_products` — Text-based product search with category filtering
  2. `get_inventory_health` — Stock levels, days-to-stockout, urgency flags
  3. `get_pricing_analysis` — Gross margins, price positioning, margin alerts
  4. `get_review_insights` — LLM-summarized customer review analysis
  5. `get_category_performance` — Aggregated category-level metrics
  6. `generate_restock_alert` — Catalog-wide stockout risk scanner
- **`app.py`** — Streamlit UI with chat interface, daily briefing, sidebar filters, and catalog summary
- **`config.py`** — LLM parameters (temperature, top_p, max_tokens) with rationale comments
- **`data_loader.py`** — CSV data loading with caching

**Conversation memory** is maintained via Streamlit session state, enabling multi-turn follow-up questions.

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Dadajihu/stylecraft-agent-madhuram_agarwal.git
cd stylecraft-agent-madhuram_agarwal
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure your API key

This project requires an LLM API key. **You must provide your own key** — no keys are included in the repo.

**Step 1:** Create a `.env` file in the project root:

```bash
cp .env.example .env
```

**Step 2:** Open the `.env` file and add your API key. Choose ONE of the following providers:

#### Option A: Google Gemini (free tier available)

1. Go to https://aistudio.google.com/apikey
2. Click "Create API Key"
3. Copy the key and paste it in `.env`:

```env
OPENAI_API_KEY=your-gemini-api-key-here
MODEL_NAME=gemini-2.5-flash
API_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
```

#### Option B: OpenAI

1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key and paste it in `.env`:

```env
OPENAI_API_KEY=sk-your-openai-key-here
MODEL_NAME=gpt-4o-mini
API_BASE_URL=
```

#### Option C: Groq (free tier available)

1. Go to https://console.groq.com/keys
2. Click "Create API Key"
3. Copy the key and paste it in `.env`:

```env
OPENAI_API_KEY=gsk_your-groq-key-here
MODEL_NAME=llama-3.3-70b-versatile
API_BASE_URL=https://api.groq.com/openai/v1
```

> **Important:** Never commit your `.env` file. It is already in `.gitignore`.

### 4. Place dataset files

Ensure these CSV files are in the project root (already included in the repo):
- `Set-B retailmind_products.csv`
- `Set-B retailmind_reviews.csv`

### 5. Run the application

```bash
python run.py
```

Then open **http://localhost:8501** in your browser.

A **Daily Briefing** will appear automatically on startup showing:
- Top 3 stockout risks with revenue at risk
- Worst-rated product with customer complaint summary
- Lowest-margin product with pricing recommendation

## Example Queries

- "Which dresses are low on stock?"
- "What's the gross margin on the Classic White Oxford Shirt?"
- "What do customers say about the Velvet Party Dress?"
- "Show me the performance of the Outerwear category"
- "Which products need restocking?"
- "Which product has the lowest margin?"

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | API key from Google Gemini, OpenAI, or Groq |
| `MODEL_NAME` | No | LLM model name (default: `gemini-2.5-flash`) |
| `API_BASE_URL` | No | Custom API endpoint (required for Gemini and Groq, leave empty for OpenAI) |

## .env.example

```
OPENAI_API_KEY=
MODEL_NAME=gemini-2.5-flash
API_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
```
