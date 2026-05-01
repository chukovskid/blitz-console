"""Saved ICPs — friendlier card layout: summary in plain English, key chips,
one-click load + edit, run-now action."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Load .env
_ENV_FILE = _ROOT / ".env"
if _ENV_FILE.exists():
    for line in _ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import streamlit as st  # noqa: E402

from app.components import filter_panel  # noqa: E402
from app.lib import db, design  # noqa: E402
from app.lib.auth import require_auth  # noqa: E402
from app.lib.filter_model import (  # noqa: E402
    RunOptions, SearchFilters, filter_summary,
)
from app.lib.runner import spawn_pipeline_run  # noqa: E402

st.set_page_config(page_title="Saved ICPs · Blitz", page_icon="◐", layout="wide")
design.apply()
require_auth()

with st.sidebar:
    design.sidebar_brand()

design.page_header(
    title="Saved ICPs",
    subtitle="Filter presets — load to edit, run, or duplicate.",
    eyebrow="Library",
)

icps = db.list_icps()
if not icps:
    design.empty_state(
        "No ICPs saved yet. Build a filter set on <b>Build search</b> "
        "and click <b>Save profile</b>."
    )
    st.stop()


# ---- Card per ICP --------------------------------------------------------

for i in icps:
    rec = db.get_icp(i["name"])
    if not rec:
        continue

    try:
        sf = SearchFilters.from_dict(json.loads(rec["filters_json"]))
        options = RunOptions.from_dict(json.loads(rec["options_json"]))
        summary = filter_summary(sf) or "No filters set."
    except Exception:
        sf, options, summary = None, None, "Could not parse filters."

    updated = time.strftime("%b %d, %Y · %H:%M",
                            time.localtime(rec["updated_at"]))

    with st.container(border=True):
        # Header row
        h1, h2 = st.columns([3, 1])
        with h1:
            st.markdown(
                f'<div class="bc-icp-name">{rec["name"]}</div>'
                f'<div class="bc-icp-time">Updated {updated}</div>',
                unsafe_allow_html=True,
            )
        with h2:
            if options:
                st.markdown(
                    f'<p style="text-align:right;color:{design.TEXT_3};'
                    f'font-size:11.5px;margin:6px 0 0 0;">'
                    f'{options.target_leads:,} target · cap {options.hard_credit_cap:,} cr</p>',
                    unsafe_allow_html=True,
                )

        # Plain English summary
        st.markdown(
            f'<div class="bc-icp-summary">{summary}</div>',
            unsafe_allow_html=True,
        )

        # Active filter chips
        if sf:
            filter_panel.render_active_chips(sf)

        # Action row
        st.markdown('<div style="height:0.6rem"></div>',
                    unsafe_allow_html=True)
        a1, a2, a3, a4 = st.columns(4)
        with a1:
            if st.button("Load & edit", key=f"load_{rec['id']}",
                         type="primary", use_container_width=True):
                st.session_state.filters = sf or SearchFilters()
                st.session_state.options = options or RunOptions()
                st.session_state.active_filter = None
                st.switch_page("pages/1_Build_Search.py")
        with a2:
            if st.button("Run now", key=f"run_{rec['id']}",
                         use_container_width=True):
                if not os.environ.get("BLITZ_API_KEY"):
                    st.error("No BLITZ_API_KEY in env.")
                else:
                    run_id = db.create_run(
                        icp_id=rec["id"], icp_name=rec["name"],
                        filters_dict=json.loads(rec["filters_json"]),
                        options_dict=json.loads(rec["options_json"]),
                        raw_path="", enriched_path="", csv_path="", log_path="",
                    )
                    spawn_pipeline_run(run_id, sf, options,
                                       os.environ["BLITZ_API_KEY"])
                    st.success(f"Run #{run_id} started.")
        with a3:
            if st.button("Clone", key=f"clone_{rec['id']}",
                         use_container_width=True):
                db.upsert_icp(
                    f"{rec['name']}-copy",
                    json.loads(rec["filters_json"]),
                    json.loads(rec["options_json"]),
                )
                st.rerun()
        with a4:
            if st.button("Delete", key=f"del_{rec['id']}",
                         use_container_width=True):
                db.delete_icp(rec["name"])
                st.rerun()

        # Rename + technical details (collapsed)
        with st.expander("Rename / inspect JSON", expanded=False):
            new_name = st.text_input(
                "Rename to", key=f"rename_{rec['id']}",
                placeholder="new-name",
            )
            if (st.button("Rename", key=f"do_rename_{rec['id']}",
                          disabled=not new_name.strip()
                          or new_name == rec["name"])):
                db.upsert_icp(
                    new_name.strip(),
                    json.loads(rec["filters_json"]),
                    json.loads(rec["options_json"]),
                )
                db.delete_icp(rec["name"])
                st.rerun()

            st.markdown(
                f'<p class="bc-eyebrow" style="margin-top:0.8rem;">'
                f'Request body</p>',
                unsafe_allow_html=True,
            )
            if sf:
                st.code(
                    json.dumps(sf.to_search_body(), indent=2),
                    language="json",
                )
