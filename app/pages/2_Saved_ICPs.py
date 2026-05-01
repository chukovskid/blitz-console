"""Manage saved ICP profiles: list, view JSON, rename, delete, clone."""

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

from app.lib import db  # noqa: E402
from app.lib.auth import require_auth  # noqa: E402
from app.lib.filter_model import RunOptions, SearchFilters  # noqa: E402

st.set_page_config(page_title="Saved ICPs · Blitz", layout="wide")
require_auth()
st.title("📚 Saved ICPs")

icps = db.list_icps()
if not icps:
    st.info("No ICPs saved yet. Build one on the **Build Search** page and click 💾 Save.")
    st.stop()

for i in icps:
    rec = db.get_icp(i["name"])
    if not rec:
        continue
    with st.expander(f"📌 {rec['name']}", expanded=False):
        st.caption(
            f"Created {time.strftime('%Y-%m-%d %H:%M', time.localtime(rec['created_at']))} · "
            f"Updated {time.strftime('%Y-%m-%d %H:%M', time.localtime(rec['updated_at']))}"
        )
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            try:
                f = SearchFilters.from_dict(json.loads(rec["filters_json"]))
                body = f.to_search_body()
                st.code(json.dumps(body, indent=2), language="json")
            except Exception as e:
                st.error(f"Could not parse filters: {e}")
        with col2:
            new_name = st.text_input("Rename to", key=f"rename_{rec['id']}")
            if st.button("Rename", key=f"do_rename_{rec['id']}"):
                if new_name.strip() and new_name != rec["name"]:
                    db.upsert_icp(
                        new_name.strip(),
                        json.loads(rec["filters_json"]),
                        json.loads(rec["options_json"]),
                    )
                    db.delete_icp(rec["name"])
                    st.success(f"Renamed to {new_name}")
                    st.rerun()
            if st.button("Clone", key=f"clone_{rec['id']}"):
                db.upsert_icp(
                    f"{rec['name']}-copy",
                    json.loads(rec["filters_json"]),
                    json.loads(rec["options_json"]),
                )
                st.rerun()
        with col3:
            if st.button("🗑 Delete", key=f"del_{rec['id']}"):
                db.delete_icp(rec["name"])
                st.rerun()
