# Mini-Project Sprint: Multi-Agent Travel Planner

Build a manager-worker travel-planning agent that delegates to flight, hotel, and activity workers, drafts an itinerary, critiques it with Reflexion, and produces a refined final travel plan.

## Prerequisites

- Python 3.10 or 3.11
- VS Code, JupyterLab, or Jupyter Notebook
- OpenAI API key only if running `DEMO_MODE=live`
- LangSmith account only if enabling tracing

The default `offline` mode runs without paid APIs using deterministic classroom-safe logic and local sample data.

The project now also validates the Singapore trip request contract (Mumbai → Singapore, 4 days, 2 travellers, hotel budget under ₹45,000, red-eye avoidance, and food/view/culture preferences) before generating the itinerary.

## Setup

Download or clone this folder, then open a terminal inside the project root.

### Option A: venv

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### Option B: conda

```bash
conda create -n travel-planner-agent python=3.11
conda activate travel-planner-agent
pip install -r requirements.txt
```

### Configure environment

```bash
cp .env.sample .env
```

For the first run, keep:

```text
DEMO_MODE=offline
```

For live OpenAI calls, update `.env`:

```text
DEMO_MODE=live
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
```

Optional LangSmith tracing:

```text
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=ls__your-key-here
LANGSMITH_PROJECT=BIA_Mini_Project_Sprint_Travel_Planner
```

## How to run

### Guided teaching notebook

```bash
jupyter notebook notebook.ipynb
```

Run cells from top to bottom. The notebook starts in offline mode unless `.env` says otherwise.

### Command-line demo

```bash
python main.py
```

### Streamlit web UI

```bash
streamlit run streamlit_app.py
```

The Streamlit page uses the same planner logic and defaults to offline mode for a safe demo. It also includes an Expedia FAQ search section that uses hybrid retrieval over `data/E_FAQs.pdf`.

Print the complete manager-worker trace:

```bash
python main.py --show-trace
```

Ask the Expedia FAQ PDF directly:

```bash
python main.py --faq "What is Expedia's cancellation policy?"
```

Use the Singapore demo request:

```bash
python main.py --request "Plan a 4-day Singapore trip from Mumbai for two people. Mid-budget. Avoid red-eye flights. Prefer food, city views, and cultural sites. Keep hotel budget under ₹45,000."
```

The run writes a readable Markdown plan into `outputs/` (for example `outputs/trip_plan_YYYYMMDD-HHMMSS.md`).

Sample output section:

```bash
python main.py --demo-mode offline --request "Plan a 4-day Singapore trip from Mumbai for two people. Mid-budget. Avoid red-eye flights. Prefer food, city views, and cultural sites. Keep hotel budget under ₹45,000."
```

Expected generated Markdown file:

```text
outputs/trip_plan_YYYYMMDD-HHMMSS.md
```

Force live mode for a run:

```bash
python main.py --demo-mode live
```

## What each file does

- `notebook.ipynb` — guided practical walkthrough for live teaching
- `main.py` — command-line runner for the complete pipeline
- `agents/manager.py` — manager agent that extracts requirements, delegates, synthesises, and refines
- `agents/workers.py` — flight, hotel, and activity worker agents
- `agents/critic.py` — Reflexion-style critic
- `tools/travel_tools.py` — local deterministic search tools over sample data
- `utils.py` — environment loading, OpenAI wrapper, JSON helpers
- `langgraph_flow.py` — LangGraph orchestration for the planner flow
- `prompts/langgraph_prompts.py` — LangChain prompt templates used by the graph nodes
- `data/sample_flights.json` — simulated flight inventory
- `data/sample_hotels.json` — simulated hotel inventory
- `data/sample_activities.json` — simulated activity inventory
- `data/demo_requests.json` — sample classroom prompts
- `prompts/prompt_contracts.md` — agent input/output contracts
- `outputs/sample_run_offline.md` — expected output shape
- `.env.sample` — environment variable template
- `trainer_guide.md` — trainer flow, timing, questions, and troubleshooting

## Expected output

A successful run prints:

1. A structured requirement extraction
2. Worker outputs with ReAct-style traces
3. A draft itinerary
4. A critic report
5. A refined final itinerary
6. Changes made after critique

Offline mode gives deterministic results. Live mode may produce different wording and ranking explanations while staying grounded in local data.

## Estimated API cost

Offline mode costs ₹0.

Live mode uses approximately 5–7 compact OpenAI calls over small local data. With `gpt-4o-mini`, a full demo run is designed to remain well below the session target cost. Keep sample data small during class to avoid unnecessary token usage.

## Troubleshooting

### `OPENAI_API_KEY is missing`

Either add a valid key to `.env` or set:

```text
DEMO_MODE=offline
```

### `ModuleNotFoundError`

Confirm the virtual environment is activated and dependencies are installed:

```bash
pip install -r requirements.txt
```

### No matching flights or hotels

The local dataset is intentionally small. Use one of the included demo requests or add new records to the JSON files.

### LangSmith traces not appearing

Check that:

```text
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=...
```

Then run in `DEMO_MODE=live`.

## Further reading

- OpenAI Python SDK documentation: https://github.com/openai/openai-python
- LangSmith tracing documentation: https://docs.smith.langchain.com/
- ReAct prompting paper: https://arxiv.org/abs/2210.03629
- Reflexion paper: https://arxiv.org/abs/2303.11366
- Expedia in ChatGPT product page: https://www.expedia.com/product/expedia-in-chatgpt/
- Booking.com and OpenAI case study: https://openai.com/index/booking-com/
