"""Run history: status, progress for live runs, CSV downloads for completed runs."""

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
from app.lib.runner import cancel_run, is_pid_alive, parse_progress  # noqa: E402

st.set_page_config(page_title="Run History · Blitz", layout="wide")
require_auth()
st.title("📜 Run History")

auto_refresh = st.checkbox("Auto-refresh every 5s (for live runs)", value=False)

runs = db.list_runs(limit=50)
if not runs:
    st.info("No runs yet.")
    st.stop()

any_live = False

for r in runs:
    pid = r.get("pid")
    alive = is_pid_alive(pid) if pid else False
    if r["status"] == "running" and not alive:
        # Process died without completing — reconcile state.
        log = parse_progress(r.get("log_path") or "")
        if log.get("phase") == "done":
            db.update_run(
                r["id"],
                status="done",
                finished_at=time.time(),
                emails_found=log.get("emails_found") or 0,
                leads_total=log.get("leads_total") or 0,
                credits_used=(log.get("search_credits") or 0) + (log.get("enrich_credits_total") or 0),
            )
        else:
            db.update_run(r["id"], status="error", finished_at=time.time(), error="process exited")
        r = db.get_run(r["id"])

    is_live = r["status"] == "running" and alive
    if is_live:
        any_live = True

    icon = {
        "queued": "⏳",
        "running": "⏵",
        "done": "✅",
        "error": "❌",
        "cancelled": "🚫",
    }.get(r["status"], "•")

    title = f"{icon} #{r['id']} · {r.get('icp_name') or '(unsaved)'} · {r['status']}"
    with st.expander(title, expanded=is_live):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Leads", r.get("leads_total") or 0)
        c2.metric("Emails", r.get("emails_found") or 0)
        c3.metric("Credits", r.get("credits_used") or 0)
        if r.get("started_at"):
            c4.metric("Started", time.strftime("%H:%M:%S", time.localtime(r["started_at"])))

        if is_live:
            log = parse_progress(r.get("log_path") or "")
            st.write(f"**Phase:** {log.get('phase', '?')}")
            if log.get("phase") == "search":
                st.write(
                    f"Tier `{log.get('last_tier','?')}` page {log.get('last_page','?')} · "
                    f"{log.get('unique_leads', 0)} unique leads"
                )
            elif log.get("phase") == "enrich":
                pct = 0
                if log.get("enrich_done"):
                    pct = 100 * log["enrich_hits"] / max(log["enrich_done"], 1)
                st.write(
                    f"Enriched {log.get('enrich_done', 0)} · "
                    f"hits {log.get('enrich_hits', 0)} ({pct:.0f}%) · "
                    f"credits used {log.get('enrich_credits', 0)}"
                )
            if st.button("✋ Cancel", key=f"cancel_{r['id']}"):
                cancel_run(r["id"])
                st.rerun()

        # Downloads
        csv = r.get("csv_path") or ""
        if csv and Path(csv).exists():
            with open(csv, "rb") as f:
                st.download_button(
                    "⬇ Download CSV (email-only, SalesHandy-ready)",
                    data=f.read(),
                    file_name=Path(csv).name,
                    mime="text/csv",
                    key=f"dl_csv_{r['id']}",
                )
        all_csv = csv.replace(".csv", "_all.csv") if csv else ""
        if all_csv and Path(all_csv).exists():
            with open(all_csv, "rb") as f:
                st.download_button(
                    "⬇ Download all leads CSV",
                    data=f.read(),
                    file_name=Path(all_csv).name,
                    mime="text/csv",
                    key=f"dl_all_{r['id']}",
                )

        if r.get("log_path") and Path(r["log_path"]).exists():
            with st.expander("Run log", expanded=False):
                st.text(Path(r["log_path"]).read_text(errors="replace")[-5000:])

        if r.get("error"):
            st.error(r["error"])

if auto_refresh and any_live:
    time.sleep(5)
    st.rerun()
