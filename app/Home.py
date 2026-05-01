"""Streamlit entrypoint: dashboard.

Run with:  streamlit run app/Home.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Allow `from app.lib...` imports when Streamlit launches us directly.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st  # noqa: E402

# Load .env if present
_ENV_FILE = _ROOT / ".env"
if _ENV_FILE.exists():
    for line in _ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from app.lib import db  # noqa: E402
from app.lib.auth import require_auth  # noqa: E402
from app.lib.blitz_client import BlitzError, get_key_info  # noqa: E402

st.set_page_config(
    page_title="Blitz Console",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_auth()
db.init_db()

st.title("🎯 Blitz Console")
st.caption("Local prospecting cockpit for the Blitz API. Apollo-style filters, live counts, run history.")

# --- Credit balance card ---
col1, col2, col3 = st.columns([1, 1, 2])

if not os.environ.get("BLITZ_API_KEY"):
    st.error(
        "**No API key set.** Create a `.env` file in the project root with "
        "`BLITZ_API_KEY=blitz-...` (the file is gitignored). Or set it in Settings."
    )
else:
    try:
        info = get_key_info()
        with col1:
            st.metric("Credits", f"{info['remaining_credits']:,}")
            db.log_balance(info["remaining_credits"], note="dashboard load")
        with col2:
            st.metric("Rate limit", f"{info['max_requests_per_seconds']} rps")
        with col3:
            plans = ", ".join(p["name"] for p in info.get("active_plans") or [])
            st.metric("Plan", plans or "—")
            reset = info.get("next_reset_at", "")
            if reset:
                st.caption(f"Resets {reset}")
    except BlitzError as e:
        st.error(f"Could not reach Blitz: {e}")

st.divider()

# --- Recent runs ---
left, right = st.columns([2, 1])

with left:
    st.subheader("Recent runs")
    runs = db.list_runs(limit=10)
    if not runs:
        st.info("No runs yet. Head to **Build Search** to launch your first one.")
    else:
        for r in runs:
            cols = st.columns([1, 2, 1, 1, 1])
            with cols[0]:
                st.write(f"#{r['id']}")
            with cols[1]:
                st.write(r.get("icp_name") or "(unsaved)")
            with cols[2]:
                st.write(r["status"])
            with cols[3]:
                st.write(f"{r.get('emails_found') or 0} ✉️")
            with cols[4]:
                st.write(f"{r.get('credits_used') or 0} cr")

with right:
    st.subheader("Saved ICPs")
    icps = db.list_icps()
    if not icps:
        st.info("Save a filter set as an ICP from **Build Search**.")
    else:
        for i in icps[:8]:
            st.write(f"• {i['name']}")

st.divider()
st.caption(
    "Phase 1 build · Filters cover the 14 fields Blitz actually supports. "
    "See the *Build Search* page to start. "
    "Apollo features that Blitz doesn't expose (revenue, technographics, "
    "funding, state-level geo) are intentionally not shown."
)
