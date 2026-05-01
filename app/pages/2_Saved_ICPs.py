"""Saved ICPs: list, view JSON, rename, clone, delete."""

from __future__ import annotations

import json
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
from app.lib.filter_model import RunOptions, SearchFilters  # noqa: E402

st.set_page_config(page_title="Saved ICPs · Blitz", page_icon="◐", layout="wide")
design.apply()
require_auth()

design.page_header(
    title="Saved ICPs",
    subtitle="Filter presets, ready to clone or load.",
    eyebrow="Library",
)

icps = db.list_icps()
if not icps:
    st.markdown(
        '<div class="bc-card-muted">No ICPs yet. Build a filter set on '
        '<b>Build search</b> and click <b>Save profile</b>.</div>',
        unsafe_allow_html=True,
    )
    st.stop()

for i in icps:
    rec = db.get_icp(i["name"])
    if not rec:
        continue
    with st.expander(rec["name"], expanded=False):
        created = time.strftime("%b %d, %Y · %H:%M", time.localtime(rec["created_at"]))
        updated = time.strftime("%b %d, %Y · %H:%M", time.localtime(rec["updated_at"]))
        st.markdown(
            f'<p class="caption" style="color:{design.TEXT_3};font-size:11.5px;">'
            f'Created {created} · Updated {updated}</p>',
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns([3, 1])
        with col1:
            try:
                f = SearchFilters.from_dict(json.loads(rec["filters_json"]))
                body = f.to_search_body()
                st.code(json.dumps(body, indent=2), language="json")
            except Exception as e:
                st.error(f"Could not parse filters: {e}")

        with col2:
            new_name = st.text_input(
                "Rename to", key=f"rename_{rec['id']}", placeholder="new-name",
            )
            if st.button("Rename", key=f"do_rename_{rec['id']}",
                         use_container_width=True,
                         disabled=not new_name.strip() or new_name == rec["name"]):
                db.upsert_icp(
                    new_name.strip(),
                    json.loads(rec["filters_json"]),
                    json.loads(rec["options_json"]),
                )
                db.delete_icp(rec["name"])
                st.rerun()
            if st.button("Clone", key=f"clone_{rec['id']}", use_container_width=True):
                db.upsert_icp(
                    f"{rec['name']}-copy",
                    json.loads(rec["filters_json"]),
                    json.loads(rec["options_json"]),
                )
                st.rerun()
            if st.button("Delete", key=f"del_{rec['id']}", use_container_width=True):
                db.delete_icp(rec["name"])
                st.rerun()
