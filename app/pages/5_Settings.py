"""Settings: API key, defaults, credit history chart."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st  # noqa: E402

from app.lib import db  # noqa: E402
from app.lib.auth import require_auth  # noqa: E402

st.set_page_config(page_title="Settings · Blitz", layout="wide")
require_auth()
st.title("⚙️ Settings")

# --- API key ---
st.subheader("API key")
env_file = _ROOT / ".env"
key_present = bool(os.environ.get("BLITZ_API_KEY"))
st.write(f"`.env` file: {'✅ found' if env_file.exists() else '❌ not found'} at `{env_file}`")
st.write(f"`BLITZ_API_KEY` env var loaded: {'✅' if key_present else '❌'}")

new_key = st.text_input(
    "Set / update API key (writes to .env, gitignored)",
    value="",
    type="password",
    placeholder="blitz-...",
)
if st.button("Save API key", disabled=not new_key.strip()):
    body = ""
    if env_file.exists():
        body = env_file.read_text()
        # Replace existing line if present
        new_lines = []
        replaced = False
        for line in body.splitlines():
            if line.startswith("BLITZ_API_KEY="):
                new_lines.append(f"BLITZ_API_KEY={new_key.strip()}")
                replaced = True
            else:
                new_lines.append(line)
        if not replaced:
            new_lines.append(f"BLITZ_API_KEY={new_key.strip()}")
        body = "\n".join(new_lines) + "\n"
    else:
        body = f"BLITZ_API_KEY={new_key.strip()}\n"
    env_file.write_text(body)
    os.environ["BLITZ_API_KEY"] = new_key.strip()
    st.success("Saved. Restart Streamlit to ensure all pages pick up the new key.")

st.divider()

# --- Credit history ---
st.subheader("Credit balance history")
hist = db.credit_history(limit=200)
if hist:
    import pandas as pd
    df = pd.DataFrame(hist)
    df["ts"] = pd.to_datetime(df["ts"], unit="s")
    df = df.sort_values("ts")
    st.line_chart(df.set_index("ts")["balance"])
    st.caption(
        "Logged each time the dashboard or a count call queries balance. "
        "Sudden unexplained drops = possible key leak."
    )
else:
    st.info("No balance samples logged yet. Visit the dashboard to seed it.")

st.divider()

# --- Diagnostics ---
st.subheader("Diagnostics")
st.write(f"Project root: `{_ROOT}`")
st.write(f"Database: `{_ROOT / 'blitz.db'}`")
st.write(f"Runs dir: `{_ROOT / 'runs'}`")
