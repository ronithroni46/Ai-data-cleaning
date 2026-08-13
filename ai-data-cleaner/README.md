# 🧹 AI Data Cleaning Tool

A Streamlit web app that uses Claude to spot data quality issues in a CSV/Excel
file and suggest fixes in plain language. You review and accept each fix, then
download the cleaned file.

## How it works

1. Upload a CSV or Excel file.
2. The app builds a **profile** of the data (column types, missing values,
   duplicates, outliers, sample rows) — not the raw dataset — and sends it to
   Claude.
3. Claude returns a list of issues, each with a human-readable description
   and a structured "fix action" (e.g. fill missing values, strip whitespace,
   standardize casing, convert types, clip outliers, drop duplicates...).
4. You click "Apply" or "Dismiss" on each issue.
5. Download the cleaned CSV/Excel when you're done.

## Setup

```bash
cd ai-data-cleaner
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Get a free Gemini API key at https://aistudio.google.com/apikey (no billing
required for the free tier, but it is rate-limited).

Set it either as an environment variable:

```bash
export GEMINI_API_KEY=your-api-key-here   # Windows: set GEMINI_API_KEY=...
```

or paste it into the sidebar field when the app is running.

## Run

```bash
streamlit run app.py
```

Then open the local URL Streamlit prints (usually http://localhost:8501).

## Project structure

```
ai-data-cleaner/
├── app.py                  # Streamlit UI
├── cleaner/
│   ├── profiler.py         # Builds a compact data profile for the LLM
│   ├── llm_analyzer.py     # Calls Claude, parses structured issues
│   └── fixer.py            # Applies accepted fixes to the DataFrame
├── requirements.txt
├── .env.example
└── README.md
```

## Extending it

- **New fix types:** add a case in `cleaner/fixer.py`'s `apply_fix()` and
  mention the new `fix_action.type` in the system prompt in
  `cleaner/llm_analyzer.py`.
- **Bigger files:** the profiler samples rows and summarizes columns rather
  than sending the whole file, so it scales to large files reasonably well.
  For very wide files, consider profiling only a subset of columns per call.
- **Batch/CLI mode:** the `cleaner/` package has no Streamlit dependency, so
  you can import `build_profile`, `analyze`, and `apply_fix` directly in a
  script for a non-UI / batch workflow.
- **Persisting audit logs:** `st.session_state.log` currently lives only in
  the browser session — write it to a file or DB if you need a durable audit
  trail.

## Notes

- Only a statistical *profile* of your data is sent to Claude, not the full
  dataset (aside from a small sample of rows for context) — useful if your
  data is sensitive, but be aware the sample rows do leave your machine.
- This is a starting point, not a production data pipeline: review Claude's
  suggested fixes before trusting them on important data.
