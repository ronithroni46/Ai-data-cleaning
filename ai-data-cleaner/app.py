"""
AI Data Cleaning Tool
----------------------
Streamlit app: upload a CSV/Excel file, let Claude find data quality issues
and suggest fixes, review & accept fixes, then download the cleaned file.

Run with:  streamlit run app.py
"""
import io
import os

import pandas as pd
import streamlit as st

from cleaner.profiler import build_profile, profile_to_prompt_text
from cleaner.llm_analyzer import analyze
from cleaner.fixer import apply_fix

st.set_page_config(page_title="AI Data Cleaner", page_icon="🧹", layout="wide")

# ---------------------------------------------------------------- session ---
if "df" not in st.session_state:
    st.session_state.df = None
if "original_df" not in st.session_state:
    st.session_state.original_df = None
if "issues" not in st.session_state:
    st.session_state.issues = []
if "log" not in st.session_state:
    st.session_state.log = []

st.title("🧹 AI Data Cleaning Tool")
st.caption("Upload messy tabular data, let Claude spot the problems, review the fixes, download clean data.")

# ------------------------------------------------------------- sidebar -----
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input(
        "Gemini API key",
        type="password",
        value=os.environ.get("GEMINI_API_KEY", ""),
        help="Reads from GEMINI_API_KEY env var if set. Never stored. "
             "Get a free key at aistudio.google.com/apikey",
    )
    st.markdown("---")
    if st.session_state.log:
        st.subheader("Change log")
        for entry in st.session_state.log:
            st.write(f"• {entry}")

# ------------------------------------------------------------- upload ------
uploaded = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx", "xls"])

if uploaded is not None and st.session_state.df is None:
    try:
        if uploaded.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded)
        else:
            df = pd.read_excel(uploaded)
        st.session_state.df = df
        st.session_state.original_df = df.copy()
    except Exception as e:
        st.error(f"Couldn't read that file: {e}")

if st.button("🔄 Start over / upload a different file"):
    st.session_state.df = None
    st.session_state.original_df = None
    st.session_state.issues = []
    st.session_state.log = []
    st.rerun()

# ------------------------------------------------------------- main --------
if st.session_state.df is not None:
    df = st.session_state.df

    st.subheader("Preview")
    st.dataframe(df.head(20), use_container_width=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", len(df))
    c2.metric("Columns", len(df.columns))
    c3.metric("Duplicate rows", int(df.duplicated().sum()))

    st.markdown("---")

    if st.button("🔍 Analyze with AI", type="primary", disabled=not api_key):
        if not api_key:
            st.warning("Enter your Gemini API key in the sidebar first.")
        else:
            with st.spinner("Profiling data and asking Claude for issues..."):
                profile = build_profile(df)
                prompt_text = profile_to_prompt_text(profile)
                try:
                    issues = analyze(prompt_text, api_key=api_key)
                    st.session_state.issues = issues
                    if not issues:
                        st.success("No significant issues found!")
                except Exception as e:
                    st.error(f"Analysis failed: {e}")

    if not api_key:
        st.caption("⚠️ Enter an API key in the sidebar to enable analysis.")

    # ----------------------------------------------------- issues review ---
    if st.session_state.issues:
        st.subheader(f"Found {len(st.session_state.issues)} issue(s)")

        severity_color = {"high": "🔴", "medium": "🟠", "low": "🟡"}

        for i, issue in enumerate(st.session_state.issues):
            col_label = issue.get("column", "?")
            sev = issue.get("severity", "low")
            with st.expander(
                f"{severity_color.get(sev, '⚪')} [{col_label}] {issue.get('issue', 'Issue')}",
                expanded=True,
            ):
                st.write(f"**Suggested fix:** {issue.get('suggested_fix', '—')}")
                st.code(issue.get("fix_action", {}), language="python")
                b1, b2 = st.columns(2)
                if b1.button("✅ Apply fix", key=f"apply_{i}"):
                    new_df, log_msg = apply_fix(st.session_state.df, issue)
                    st.session_state.df = new_df
                    st.session_state.log.append(log_msg)
                    st.session_state.issues.pop(i)
                    st.rerun()
                if b2.button("❌ Dismiss", key=f"dismiss_{i}"):
                    st.session_state.issues.pop(i)
                    st.rerun()

    # ----------------------------------------------------------- export ----
    if st.session_state.log:
        st.markdown("---")
        st.subheader("Download cleaned data")
        cleaned_df = st.session_state.df

        csv_buf = cleaned_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download as CSV", csv_buf, "cleaned_data.csv", "text/csv")

        excel_buf = io.BytesIO()
        cleaned_df.to_excel(excel_buf, index=False, engine="openpyxl")
        st.download_button(
            "⬇️ Download as Excel",
            excel_buf.getvalue(),
            "cleaned_data.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
else:
    st.info("👆 Upload a CSV or Excel file to get started.")
