# RetailMind Product Intelligence Agent

An AI-powered product intelligence agent built for **StyleCraft**, a D2C fashion brand with 30+ SKUs across 5 categories. RetailMind answers natural language questions about inventory, pricing, reviews, and catalog performance through a conversational chat interface.

---

## Quick Start (3 steps)

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure your API key

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Open `.env` and paste your API key. Pick **any one** provider:

| Provider | Free Tier | Get Key | `.env` values |
|----------|-----------|---------|---------------|
| **Google Gemini** | Yes | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | `OPENAI_API_KEY=your-key`<br>`MODEL_NAME=gemini-2.5-flash`<br>`API_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/` |
| **Groq** | Yes | [console.groq.com/keys](https://console.groq.com/keys) | `OPENAI_API_KEY=your-key`<br>`MODEL_NAME=llama-3.3-70b-versatile`<br>`API_BASE_URL=https://api.groq.com/openai/v1` |
| **OpenAI** | No | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | `OPENAI_API_KEY=sk-your-key`<br>`MODEL_NAME=gpt-4o-mini`<br>`API_BASE_URL=` |

### 3. Run

```bash
python run.py
```

Opens at **http://localhost:8501**. The Daily Briefing loads automatically on startup.

---

## What to Expect on Launch

When the app starts, a **Daily Briefing** is generated automatically:

- **Stockout Alerts** — Top 3 products at risk of running out, with revenue at risk and urgency color coding
- **Worst-Rated Product** — Lowest-rated SKU with an LLM-generated summary of customer complaints
- **Pricing Flag** — Lowest-margin product with a margin health indicator
- **Category Performance Table** — All 5 categories with SKU count, avg rating, avg margin, stock levels, and at-risk counts

Below the briefing is a chat input where you can ask anything about the catalog.

---

## Test Prompts (by Feature)

Copy-paste these to test each capability:

### Inventory & Stockout Risk
```
Which products are at risk of running out of stock?
```
```
Check inventory health for SC001
```
```
How many days of stock does SC015 have left?
```

### Pricing & Margins
```
Give me a pricing overview of the entire catalog
```
```
What's the margin on SC010?
```
```
Which product has the lowest margin?
```

### Customer Reviews & Sentiment
```
What are customers saying about SC005?
```
```
Show me review insights for the worst-rated product
```

### Catalog Search & Category Analysis
```
Find all dresses in the catalog
```
```
How is the Outerwear category performing?
```
```
What are the top selling accessories?
```

### Multi-Turn Follow-ups
```
Tell me about the Classic Denim Jacket
```
Then follow up with:
```
What's its margin?
```

### General / Agent Persona
```
Who are you and what can you do?
```
```
What should I prioritize this week?
```

### Sidebar Interaction
- Change the **Category** dropdown to "Tops", then ask: `How is this category doing?`
- Click **Clear Chat** to reset the conversation and reload the briefing

---

## Architecture

```
User Query --> LLM Router (intent classification via function calling) --> Tool Execution --> LLM Response
```

| File | Role |
|------|------|
| `app.py` | Streamlit UI — chat interface, daily briefing, sidebar, CSS styling |
| `agent.py` | LLM router agent — classifies intent and dispatches to tools; generates daily briefing data |
| `tools.py` | 6 analysis tools with OpenAI-format schemas (search, inventory, pricing, reviews, category, restock) |
| `config.py` | LLM parameters, API config, business constants |
| `data_loader.py` | CSV loader with caching |
| `run.py` | Entry point — launches Streamlit |

### Tools

| # | Tool | Purpose |
|---|------|---------|
| 1 | `search_products` | Text search across the product catalog with optional category filter |
| 2 | `get_inventory_health` | Stock level, days-to-stockout, urgency flag for a single product |
| 3 | `get_pricing_analysis` | Gross margin, price positioning, margin alerts (single product or catalog-wide) |
| 4 | `get_review_insights` | LLM-summarized review sentiment with positive/negative themes |
| 5 | `get_category_performance` | Aggregated category metrics with top 3 revenue products |
| 6 | `generate_restock_alert` | Catalog-wide stockout risk scan sorted by urgency |

### Key Design Decisions

- **LLM-based routing** — The LLM decides which tool to call via OpenAI function calling. No keyword matching or regex.
- **Multi-turn memory** — Conversation history is maintained in Streamlit session state for follow-up questions.
- **Provider-agnostic** — Works with any OpenAI-compatible API (Gemini, Groq, OpenAI) via a single config change.
- **Daily Briefing** — Proactive intelligence generated on startup without the user needing to ask.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | API key from Google Gemini, OpenAI, or Groq |
| `MODEL_NAME` | No | LLM model name (default: `gemini-2.5-flash`) |
| `API_BASE_URL` | No | Custom API endpoint (required for Gemini/Groq, leave empty for OpenAI) |

---

## Dataset

The app uses two CSV files (included in the repo):
- `Set-B retailmind_products.csv` — 30 products with price, cost, stock, sales, ratings
- `Set-B retailmind_reviews.csv` — Customer reviews with ratings, titles, and text
