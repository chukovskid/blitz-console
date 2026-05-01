"""Settings: API key, credit history."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st  # noqa: E402

from app.lib import db, design  # noqa: E402
from app.lib.auth import require_auth  # noqa: E402

st.set_page_config(page_title="Settings · Blitz", page_icon="◐", layout="wide")
design.apply()
design.topnav(current="Settings")
require_auth()

design.page_header(
    title="Settings",
    subtitle="API access and credit history.",
    eyebrow="Configuration",
)

# --- API key ---
st.markdown("## API key")

env_file = _ROOT / ".env"
key_present = bool(os.environ.get("BLITZ_API_KEY"))

c1, c2 = st.columns(2)
with c1:
    st.markdown(
        f'<div class="bc-card">'
        f'<p class="bc-eyebrow">.env file</p>'
        f'<p style="font-weight:500;font-size:14px;margin:0.2rem 0 0 0;">'
        f'{"Present" if env_file.exists() else "Missing"}</p>'
        f'<p style="color:{design.TEXT_3};font-size:11.5px;margin-top:0.4rem;'
        f'font-family:{design.FONT_MONO};">{env_file}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f'<div class="bc-card">'
        f'<p class="bc-eyebrow">BLITZ_API_KEY</p>'
        f'<p style="font-weight:500;font-size:14px;margin:0.2rem 0 0 0;">'
        f'{"Loaded" if key_present else "Not set"}</p>'
        f'<p style="color:{design.TEXT_3};font-size:11.5px;margin-top:0.4rem;">'
        f'{"Set in environment" if key_present else "Add via field below"}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown('<div style="height:1.5rem"></div>', unsafe_allow_html=True)

new_key = st.text_input(
    "Update API key",
    value="",
    type="password",
    placeholder="blitz-…",
    help="Writes to .env (gitignored). Restart Streamlit to take effect across all pages.",
)
if st.button("Save key", disabled=not new_key.strip(), type="primary"):
    body = ""
    if env_file.exists():
        body = env_file.read_text()
        new_lines, replaced = [], False
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
    st.success("Saved. Restart Streamlit so all pages pick up the new key.")


design.hairline()

# --- Credit history ---
st.markdown("## Credit balance")

hist = db.credit_history(limit=200)
if hist:
    import pandas as pd
    df = pd.DataFrame(hist)
    df["ts"] = pd.to_datetime(df["ts"], unit="s")
    df = df.sort_values("ts")
    st.line_chart(df.set_index("ts")["balance"], height=260)
    st.markdown(
        f'<p style="color:{design.TEXT_3};font-size:11.5px;">Sampled on every '
        f'dashboard load and count refresh. Sudden drops without a corresponding '
        f'run usually mean the API key was used elsewhere — rotate it.</p>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<div class="bc-card-muted">No samples yet — visit the dashboard to seed one.</div>',
        unsafe_allow_html=True,
    )


design.hairline()

# --- Diagnostics ---
st.markdown("## Diagnostics")
st.markdown(
    f'<div class="bc-card-muted" style="font-family:{design.FONT_MONO};font-size:12px;">'
    f'project root  {_ROOT}<br>'
    f'database      {_ROOT / "blitz.db"}<br>'
    f'runs dir      {_ROOT / "runs"}'
    f'</div>',
    unsafe_allow_html=True,
)
