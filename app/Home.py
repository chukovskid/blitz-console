"""Streamlit entrypoint: console overview.

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

from app.lib import db, design  # noqa: E402
from app.lib.auth import require_auth  # noqa: E402
from app.lib.blitz_client import BlitzError, get_key_info  # noqa: E402

st.set_page_config(
    page_title="Blitz Console",
    page_icon="◐",
    layout="wide",
    initial_sidebar_state="expanded",
)
design.apply()
require_auth()
db.init_db()


# ----- Header ---------------------------------------------------------------

design.page_header(
    title="Console",
    subtitle="Local prospecting cockpit for the Blitz API.",
    eyebrow="Blitz",
)


# ----- Status row -----------------------------------------------------------

if not os.environ.get("BLITZ_API_KEY"):
    st.error(
        "No API key set. Create `.env` in the project root with "
        "`BLITZ_API_KEY=blitz-…`, or set it from Settings."
    )
else:
    try:
        info = get_key_info()
        db.log_balance(info["remaining_credits"], note="dashboard load")

        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            st.metric("Credits", f"{info['remaining_credits']:,}")
        with c2:
            st.metric("Rate limit", f"{info['max_requests_per_seconds']} rps")
        with c3:
            plan_name = next(
                (p["name"] for p in info.get("active_plans") or []), "—"
            )
            st.metric("Plan", plan_name)

        reset = info.get("next_reset_at", "")
        if reset:
            st.markdown(
                f'<p class="caption" style="margin-top:.2rem;color:#A3A3A3;font-size:12px">'
                f'Credits reset {reset[:10]}.</p>',
                unsafe_allow_html=True,
            )
    except BlitzError as e:
        st.error(f"Could not reach Blitz: {e}")


design.hairline()


# ----- Recent runs + saved ICPs --------------------------------------------

left, right = st.columns([2, 1], gap="large")

with left:
    st.markdown("## Recent runs")
    runs = db.list_runs(limit=10)
    if not runs:
        st.markdown(
            '<div class="bc-card-muted">No runs yet — '
            'open <b>Build Search</b> to launch your first one.</div>',
            unsafe_allow_html=True,
        )
    else:
        rows_html = []
        for r in runs:
            status = r["status"]
            dot = design.status_dot(status if status in
                                    ("running", "done", "error", "queued", "cancelled")
                                    else "queued")
            name = r.get("icp_name") or "Untitled"
            emails = r.get("emails_found") or 0
            credits_used = r.get("credits_used") or 0
            ts = r.get("started_at")
            when = (
                time.strftime("%b %d · %H:%M", time.localtime(ts)) if ts else "—"
            )
            rows_html.append(f"""
            <div style="display:grid;grid-template-columns:24px 1fr auto auto;
                        align-items:center;padding:14px 4px;
                        border-bottom:1px solid {design.BORDER};font-size:13.5px;">
                <div>{dot}</div>
                <div>
                    <div style="font-weight:500;color:{design.TEXT};">#{r['id']} — {name}</div>
                    <div style="color:{design.TEXT_3};font-size:11.5px;margin-top:2px;">
                        {when} · {status}
                    </div>
                </div>
                <div style="color:{design.TEXT_2};text-align:right;padding-right:18px;
                            font-feature-settings:'tnum' 1;">
                    <span style="color:{design.TEXT};font-weight:500;">{emails}</span>
                    <span style="color:{design.TEXT_3};font-size:11.5px;"> emails</span>
                </div>
                <div style="color:{design.TEXT_2};text-align:right;
                            font-feature-settings:'tnum' 1;">
                    <span style="color:{design.TEXT};font-weight:500;">{credits_used}</span>
                    <span style="color:{design.TEXT_3};font-size:11.5px;"> cr</span>
                </div>
            </div>
            """)
        st.markdown("".join(rows_html), unsafe_allow_html=True)


with right:
    st.markdown("## Saved ICPs")
    icps = db.list_icps()
    if not icps:
        st.markdown(
            '<div class="bc-card-muted">'
            'Build a filter set and save it from <b>Build Search</b>.'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        items = []
        for i in icps[:8]:
            updated = time.strftime("%b %d", time.localtime(i["updated_at"]))
            items.append(f"""
            <div style="display:flex;justify-content:space-between;
                        align-items:baseline;padding:10px 4px;
                        border-bottom:1px solid {design.BORDER};font-size:13.5px;">
                <span style="color:{design.TEXT};font-weight:500;">{i['name']}</span>
                <span style="color:{design.TEXT_3};font-size:11.5px;">{updated}</span>
            </div>
            """)
        st.markdown("".join(items), unsafe_allow_html=True)


# ----- Footer ---------------------------------------------------------------

st.markdown(
    f'<p style="margin-top:3rem;color:{design.TEXT_3};font-size:12px;'
    f'text-align:center;">Filters reflect what Blitz actually supports. '
    f'Apollo features Blitz lacks (revenue, technographics, funding, '
    f'state-level geography, years of experience) are intentionally absent.</p>',
    unsafe_allow_html=True,
)
