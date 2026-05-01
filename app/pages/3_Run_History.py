"""Run History — info-rich cards with summary, cost split, duration, re-run."""

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

from app.lib import db, design  # noqa: E402
from app.lib.auth import require_auth  # noqa: E402
from app.lib.filter_model import (  # noqa: E402
    RunOptions, SearchFilters, filter_summary,
)
from app.lib.runner import (  # noqa: E402
    cancel_run, is_pid_alive, parse_progress, spawn_pipeline_run,
)

st.set_page_config(page_title="Run history · Blitz", page_icon="◐", layout="wide")
design.apply()
require_auth()

with st.sidebar:
    design.sidebar_brand()

design.page_header(
    title="Run history",
    subtitle="Past and live runs — outputs, cost breakdown, audit trail.",
    eyebrow="Runs",
)

cols = st.columns([3, 1])
with cols[1]:
    auto_refresh = st.toggle("Auto-refresh (5s)", value=False)

runs = db.list_runs(limit=50)
if not runs:
    design.empty_state(
        "No runs yet. Launch one from <b>Build Search</b>."
    )
    st.stop()


def _fmt_duration(start: float | None, end: float | None) -> str:
    if not start:
        return "—"
    end = end or time.time()
    s = int(end - start)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60:02d}s"
    return f"{s // 3600}h {(s % 3600) // 60}m"


any_live = False

for r in runs:
    pid = r.get("pid")
    alive = is_pid_alive(pid) if pid else False
    if r["status"] == "running" and not alive:
        log = parse_progress(r.get("log_path") or "")
        if log.get("phase") == "done":
            db.update_run(
                r["id"], status="done",
                finished_at=time.time(),
                emails_found=log.get("emails_found") or 0,
                leads_total=log.get("leads_total") or 0,
                credits_used=(log.get("search_credits") or 0)
                + (log.get("enrich_credits_total") or 0),
            )
        else:
            db.update_run(r["id"], status="error",
                          finished_at=time.time(),
                          error="process exited")
        r = db.get_run(r["id"])

    is_live = r["status"] == "running" and alive
    if is_live:
        any_live = True

    status = r["status"] if r["status"] in (
        "running", "done", "error", "queued", "cancelled"
    ) else "queued"
    name = r.get("icp_name") or "Untitled"
    started = (
        time.strftime("%b %d, %Y · %H:%M",
                      time.localtime(r["started_at"]))
        if r.get("started_at") else "—"
    )

    # Parse filters → plain English
    summary = ""
    try:
        sf = SearchFilters.from_dict(json.loads(r["filters_json"]))
        summary = filter_summary(sf)
    except Exception:
        sf = None

    # Parse options
    try:
        opts = RunOptions.from_dict(json.loads(r["options_json"]))
    except Exception:
        opts = None

    leads = r.get("leads_total") or 0
    emails = r.get("emails_found") or 0
    credits_used = r.get("credits_used") or 0
    duration = _fmt_duration(r.get("started_at"), r.get("finished_at"))
    hit_rate = (100 * emails / leads) if leads else 0

    with st.container(border=True):
        # Header row: status dot + name + started
        h1, h2 = st.columns([3, 1])
        with h1:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:6px;">'
                f'{design.status_dot(status)}'
                f'<span style="font-weight:600;font-size:15px;'
                f'letter-spacing:-0.01em;">#{r["id"]} — {name}</span>'
                f'<span style="color:{design.TEXT_3};font-size:12px;'
                f'margin-left:0.6rem;">{status}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with h2:
            st.markdown(
                f'<p style="text-align:right;color:{design.TEXT_3};'
                f'font-size:11.5px;margin:6px 0 0 0;">{started}</p>',
                unsafe_allow_html=True,
            )

        # Plain-English summary of what was searched
        if summary:
            st.markdown(
                f'<div class="bc-icp-summary" style="margin-top:6px;">'
                f'{summary}</div>',
                unsafe_allow_html=True,
            )

        # Live progress (only for running)
        if is_live:
            log = parse_progress(r.get("log_path") or "")
            phase = log.get("phase", "?")
            if phase == "search":
                line = (
                    f"Searching · tier {log.get('last_tier','?')} · "
                    f"page {log.get('last_page','?')} · "
                    f"{log.get('unique_leads', 0)} unique leads"
                )
            elif phase == "enrich":
                pct = 0
                if log.get("enrich_done"):
                    pct = 100 * log["enrich_hits"] / max(log["enrich_done"], 1)
                line = (
                    f"Enriching · {log.get('enrich_done', 0)} processed · "
                    f"{log.get('enrich_hits', 0)} hits ({pct:.0f}%)"
                )
            else:
                line = f"Phase: {phase}"
            st.info(line)
            if st.button("Cancel run", key=f"cancel_{r['id']}"):
                cancel_run(r["id"])
                st.rerun()

        # Metric strip
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Leads", f"{leads:,}")
        m2.metric("Emails", f"{emails:,}")
        m3.metric("Hit rate", f"{hit_rate:.0f}%" if leads else "—")
        m4.metric("Credits", f"{credits_used:,}")
        m5.metric("Duration", duration)

        # Optional config detail row
        if opts:
            st.markdown(
                f'<p style="color:{design.TEXT_3};font-size:11.5px;'
                f'margin:6px 0 0 0;">'
                f'Target {opts.target_leads:,} · '
                f'per-co cap {opts.per_company_cap} · '
                f'credit cap {opts.hard_credit_cap:,} · '
                f'{"emails on" if opts.enrich_emails else "no enrichment"}'
                f'</p>',
                unsafe_allow_html=True,
            )

        # Action row: download CSVs, re-run, log
        st.markdown('<div style="height:0.6rem"></div>',
                    unsafe_allow_html=True)
        csv = r.get("csv_path") or ""
        a1, a2, a3, a4 = st.columns(4)

        with a1:
            if csv and Path(csv).exists():
                with open(csv, "rb") as f:
                    st.download_button(
                        "CSV (email-only)", data=f.read(),
                        file_name=Path(csv).name, mime="text/csv",
                        key=f"dl_csv_{r['id']}", use_container_width=True,
                    )
            else:
                st.markdown(
                    f'<p style="color:{design.TEXT_3};font-size:12px;'
                    f'text-align:center;padding:8px;">No CSV</p>',
                    unsafe_allow_html=True,
                )

        with a2:
            all_csv = csv.replace(".csv", "_all.csv") if csv else ""
            if all_csv and Path(all_csv).exists():
                with open(all_csv, "rb") as f:
                    st.download_button(
                        "CSV (all leads)", data=f.read(),
                        file_name=Path(all_csv).name, mime="text/csv",
                        key=f"dl_all_{r['id']}", use_container_width=True,
                    )

        with a3:
            if (sf and opts and r.get("status") in ("done", "error", "cancelled")
                    and st.button("Re-run", key=f"rerun_{r['id']}",
                                   use_container_width=True)):
                if not os.environ.get("BLITZ_API_KEY"):
                    st.error("No BLITZ_API_KEY in env.")
                else:
                    run_id = db.create_run(
                        icp_id=r.get("icp_id"), icp_name=r.get("icp_name"),
                        filters_dict=json.loads(r["filters_json"]),
                        options_dict=json.loads(r["options_json"]),
                        raw_path="", enriched_path="", csv_path="",
                        log_path="",
                    )
                    spawn_pipeline_run(run_id, sf, opts,
                                       os.environ["BLITZ_API_KEY"])
                    st.success(f"Re-running as #{run_id}.")

        with a4:
            if (sf and opts and st.button("Open as new ICP",
                                          key=f"open_{r['id']}",
                                          use_container_width=True)):
                st.session_state.filters = sf
                st.session_state.options = opts
                st.session_state.active_filter = None
                st.switch_page("pages/1_Build_Search.py")

        # Log (collapsed)
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
