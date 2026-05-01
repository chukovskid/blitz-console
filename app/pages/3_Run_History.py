"""Run history: live progress for in-flight runs, CSV downloads when done."""

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
from app.lib.runner import cancel_run, is_pid_alive, parse_progress  # noqa: E402

st.set_page_config(page_title="Run history · Blitz", page_icon="◐", layout="wide")
design.apply()
require_auth()

with st.sidebar:
    design.sidebar_brand()

design.page_header(
    title="Run history",
    subtitle="Live progress, downloadable outputs, audit trail.",
    eyebrow="Runs",
)

cols = st.columns([3, 1])
with cols[1]:
    auto_refresh = st.toggle("Auto-refresh (5s)", value=False)

runs = db.list_runs(limit=50)
if not runs:
    design.empty_state("No runs yet. Launch one from <b>Build Search</b>.")
    st.stop()

any_live = False

for r in runs:
    pid = r.get("pid")
    alive = is_pid_alive(pid) if pid else False
    if r["status"] == "running" and not alive:
        log = parse_progress(r.get("log_path") or "")
        if log.get("phase") == "done":
            db.update_run(
                r["id"],
                status="done",
                finished_at=time.time(),
                emails_found=log.get("emails_found") or 0,
                leads_total=log.get("leads_total") or 0,
                credits_used=(log.get("search_credits") or 0)
                             + (log.get("enrich_credits_total") or 0),
            )
        else:
            db.update_run(r["id"], status="error", finished_at=time.time(),
                          error="process exited")
        r = db.get_run(r["id"])

    is_live = r["status"] == "running" and alive
    if is_live:
        any_live = True

    status = r["status"] if r["status"] in (
        "running", "done", "error", "queued", "cancelled"
    ) else "queued"
    name = r.get("icp_name") or "Untitled"
    when = (
        time.strftime("%b %d · %H:%M", time.localtime(r["started_at"]))
        if r.get("started_at") else "—"
    )

    # Render the row as a clean header above the expander, then put details
    # inside an unlabelled expander positioned right below.
    st.markdown(
        f'<div class="bc-run-row" style="border-bottom:none;padding-bottom:6px;">'
        f'<div>{design.status_dot(status)}</div>'
        f'<div>'
        f'<div class="bc-run-name">#{r["id"]} — {name}</div>'
        f'<div class="bc-run-meta">{when} · {status}</div>'
        f'</div>'
        f'<div class="bc-run-stat"><strong>{r.get("emails_found") or 0:,}</strong><span>emails</span></div>'
        f'<div class="bc-run-stat"><strong>{r.get("credits_used") or 0:,}</strong><span>cr</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    with st.expander("Details", expanded=is_live):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Leads", r.get("leads_total") or 0)
        c2.metric("Emails", r.get("emails_found") or 0)
        c3.metric("Credits", r.get("credits_used") or 0)
        if r.get("started_at"):
            c4.metric("Started", time.strftime("%H:%M:%S",
                                               time.localtime(r["started_at"])))

        if is_live:
            log = parse_progress(r.get("log_path") or "")
            phase = log.get("phase", "?")
            if phase == "search":
                line = (
                    f"Tier <b>{log.get('last_tier','?')}</b> · page "
                    f"{log.get('last_page','?')} · {log.get('unique_leads', 0)} "
                    f"unique leads"
                )
            elif phase == "enrich":
                pct = 0
                if log.get("enrich_done"):
                    pct = 100 * log["enrich_hits"] / max(log["enrich_done"], 1)
                line = (
                    f"Enriched <b>{log.get('enrich_done', 0)}</b> · hits "
                    f"<b>{log.get('enrich_hits', 0)}</b> ({pct:.0f}%) · "
                    f"credits used {log.get('enrich_credits', 0)}"
                )
            else:
                line = f"Phase <b>{phase}</b>"
            st.markdown(
                f'<p style="color:{design.TEXT_2};font-size:13px;">{line}</p>',
                unsafe_allow_html=True,
            )
            if st.button("Cancel run", key=f"cancel_{r['id']}"):
                cancel_run(r["id"])
                st.rerun()

        # Downloads
        csv = r.get("csv_path") or ""
        download_cols = st.columns(2)
        with download_cols[0]:
            if csv and Path(csv).exists():
                with open(csv, "rb") as f:
                    st.download_button(
                        "Download CSV (email-only)",
                        data=f.read(),
                        file_name=Path(csv).name,
                        mime="text/csv",
                        key=f"dl_csv_{r['id']}",
                        use_container_width=True,
                    )
        with download_cols[1]:
            all_csv = csv.replace(".csv", "_all.csv") if csv else ""
            if all_csv and Path(all_csv).exists():
                with open(all_csv, "rb") as f:
                    st.download_button(
                        "Download CSV (all leads)",
                        data=f.read(),
                        file_name=Path(all_csv).name,
                        mime="text/csv",
                        key=f"dl_all_{r['id']}",
                        use_container_width=True,
                    )

        if r.get("log_path") and Path(r["log_path"]).exists():
            with st.expander("Run log", expanded=False):
                st.code(
                    Path(r["log_path"]).read_text(errors="replace")[-5000:],
                    language="bash",
                )

        if r.get("error"):
            st.error(r["error"])

if auto_refresh and any_live:
    time.sleep(5)
    st.rerun()
