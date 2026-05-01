"""Spawn blitz_pipeline.py as a subprocess and let the UI track progress.

Why subprocess and not threading: Streamlit reruns the script on every
interaction. A subprocess survives reruns; a thread does not. The pipeline
already persists state per page/per lead, so we just have to spawn it and
poll the log + DB for progress.
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from . import db
from .filter_model import RunOptions, SearchFilters

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_PY = PROJECT_ROOT / "blitz_pipeline.py"
RUNS_DIR = PROJECT_ROOT / "runs"
RUNS_DIR.mkdir(exist_ok=True)


# Regexes used to parse the existing pipeline's stderr output.
RE_CREDITS_BEFORE = re.compile(r"Credits before(?: search| enrichment)?: (\d+)")
RE_PAGE = re.compile(
    r"\[tier=(\w+)\] page (\d+): \+(\d+) "
    r"\(tier total (\d+), unique-after-dedupe (\d+),"
)
RE_ENRICH = re.compile(r"\[(\d+)\] tier=(\w+) hits=(\d+) \(\d+%\) credits_used=(\d+)")
RE_SEARCH_DONE = re.compile(
    r"Search done\. unique leads: (\d+)\. credits used: (\d+)\. remaining: (\d+)"
)
RE_ENRICH_DONE = re.compile(
    r"Enrichment done\. emails found: (\d+)/(\d+)\. credits used: (\d+)\. remaining: (\d+)"
)


def _bash_quote_env_export(api_key: str) -> str:
    # Avoid passing the key as a CLI arg — keep it in the spawned env.
    return api_key


def spawn_pipeline_run(
    run_id: int,
    filters: SearchFilters,
    options: RunOptions,
    api_key: str,
) -> int:
    """Write a body.json + driver script for the run, spawn it, return PID.

    The driver writes filters into a temp body.json, then calls blitz_pipeline.py
    `search` and (optionally) `enrich` and `csv` in sequence.

    The existing blitz_pipeline.py uses hardcoded TIERS/INDUSTRIES/SIZE constants.
    For the v1, we override these by writing the filters to a JSON file and
    monkey-patching the pipeline's globals via a wrapper. (Cleaner refactor of
    blitz_pipeline.py to read filters from JSON is a Phase-2 improvement.)
    """
    run_dir = RUNS_DIR / f"run_{run_id:06d}"
    run_dir.mkdir(parents=True, exist_ok=True)

    body_json = run_dir / "filters.json"
    body_json.write_text(_filters_to_pipeline_config(filters, options))

    log_path = run_dir / "run.log"
    raw_path = run_dir / "leads_raw.json"
    enriched_path = run_dir / "leads_enriched.json"
    csv_path = run_dir / "leads_for_saleshandy.csv"

    db.update_run(
        run_id,
        raw_path=str(raw_path),
        enriched_path=str(enriched_path),
        csv_path=str(csv_path),
        log_path=str(log_path),
    )

    driver = run_dir / "driver.sh"
    driver.write_text(_build_driver_script(
        run_id=run_id,
        body_json=body_json,
        raw_path=raw_path,
        enriched_path=enriched_path,
        csv_path=csv_path,
        log_path=log_path,
        options=options,
    ))
    driver.chmod(0o755)

    env = os.environ.copy()
    env["BLITZ_API_KEY"] = api_key

    f_log = open(log_path, "ab")
    proc = subprocess.Popen(
        [str(driver)],
        cwd=str(PROJECT_ROOT),
        stdout=f_log,
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True,
    )
    db.update_run(run_id, status="running", started_at=time.time(), pid=proc.pid)
    return proc.pid


def cancel_run(run_id: int) -> bool:
    r = db.get_run(run_id)
    if not r or not r.get("pid"):
        return False
    try:
        os.killpg(os.getpgid(r["pid"]), signal.SIGTERM)
    except ProcessLookupError:
        pass
    db.update_run(run_id, status="cancelled", finished_at=time.time())
    return True


def is_pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def parse_progress(log_path: str | Path) -> dict:
    """Tail-friendly progress snapshot from the run's log."""
    p = Path(log_path)
    if not p.exists():
        return {"phase": "starting"}
    text = p.read_text(errors="replace")

    snap: dict[str, Any] = {"phase": "search"}
    pages = RE_PAGE.findall(text)
    if pages:
        last = pages[-1]
        snap["last_tier"] = last[0]
        snap["last_page"] = int(last[1])
        snap["unique_leads"] = int(last[4])

    sd = RE_SEARCH_DONE.search(text)
    if sd:
        snap["phase"] = "enrich"
        snap["search_total"] = int(sd.group(1))
        snap["search_credits"] = int(sd.group(2))
        snap["balance_after_search"] = int(sd.group(3))

    enr = RE_ENRICH.findall(text)
    if enr:
        last = enr[-1]
        snap["enrich_done"] = int(last[0])
        snap["enrich_tier"] = last[1]
        snap["enrich_hits"] = int(last[2])
        snap["enrich_credits"] = int(last[3])

    ed = RE_ENRICH_DONE.search(text)
    if ed:
        snap["phase"] = "done"
        snap["emails_found"] = int(ed.group(1))
        snap["leads_total"] = int(ed.group(2))
        snap["enrich_credits_total"] = int(ed.group(3))
        snap["balance_after"] = int(ed.group(4))

    return snap


# --- internals -------------------------------------------------------------


def _filters_to_pipeline_config(filters: SearchFilters, options: RunOptions) -> str:
    """Dump filter config + run options to JSON the wrapper can read."""
    import json
    return json.dumps({
        "search_body": filters.to_search_body(),
        "tiers": _build_tier_definitions(filters),
        "options": options.to_dict(),
    }, indent=2)


def _build_tier_definitions(filters: SearchFilters) -> list[dict]:
    """If no titles set, fall back to the existing 6-tier cascade.

    If titles ARE set, use them as a single tier (no cascade).
    The pipeline file iterates tiers; we feed it whatever shape matches.
    """
    titles = list(filters.people.job_title.include)
    if titles:
        return [{"label": "user", "titles": titles}]
    # No titles set → run a single broad search — the pipeline's cascade is
    # founder/CEO/VP/Director/Head/Manager focused on marketing/growth/sales.
    return []  # signals "use built-in TIERS"


def _build_driver_script(
    run_id: int,
    body_json: Path,
    raw_path: Path,
    enriched_path: Path,
    csv_path: Path,
    log_path: Path,
    options: RunOptions,
) -> str:
    """Driver: invokes a small Python wrapper that monkey-patches the pipeline
    with the body from filters.json, then runs search → enrich → csv.

    Phase 2 will refactor blitz_pipeline.py to natively read JSON filters.
    """
    py_wrapper = (RUNS_DIR / f"run_{run_id:06d}" / "wrapper.py")
    py_wrapper.write_text(_build_wrapper_py(
        body_json=body_json,
        raw_path=raw_path,
        enriched_path=enriched_path,
        csv_path=csv_path,
        options=options,
    ))
    return f"""#!/bin/bash
set -uo pipefail
cd "{PROJECT_ROOT}"
echo "[$(date '+%H:%M:%S')] driver starting run {run_id}"
python3 "{py_wrapper}" 2>&1
echo "[$(date '+%H:%M:%S')] driver finished"
"""


def _build_wrapper_py(
    body_json: Path,
    raw_path: Path,
    enriched_path: Path,
    csv_path: Path,
    options: RunOptions,
) -> str:
    """Generate a small wrapper that re-uses blitz_pipeline.py functions
    but with a custom search body and tier list from filters.json."""
    return f"""#!/usr/bin/env python3
import json, sys, os
sys.path.insert(0, {str(PROJECT_ROOT)!r})
import blitz_pipeline as bp

cfg = json.load(open({str(body_json)!r}))
search_body = cfg["search_body"]
tiers = cfg["tiers"]
options = cfg["options"]

# 1) If the UI specified job titles, replace TIERS with a single tier.
#    Otherwise the built-in 6-tier cascade runs (founder→manager).
if tiers:
    bp.TIERS = [(t["label"], t["titles"]) for t in tiers]

# 2) Industry and employee-count are read from module globals by cmd_search,
#    so override them when the UI provided values.
if search_body.get("company"):
    cb = search_body["company"]
    if "industry" in cb and "include" in cb["industry"]:
        bp.INDUSTRIES = list(cb["industry"]["include"])
    if "employee_count" in cb:
        ec = cb["employee_count"]
        if "min" in ec: bp.EMPLOYEE_MIN = int(ec["min"])
        if "max" in ec: bp.EMPLOYEE_MAX = int(ec["max"])

# 3) All other filters (country, city, function, level, founded_year,
#    keywords, type, followers, etc.) flow through bp.EXTRA_BODY which
#    cmd_search deep-merges into every search request.
extra = dict(search_body)
# Strip the bits we already mapped above to avoid double-application.
extra.pop("max_results", None)
extra.pop("cursor", None)
bp.EXTRA_BODY = extra

# Phase 1 — search
class _Args: pass
a = _Args()
a.out = {str(raw_path)!r}
a.target = int(options["target_leads"])
a.pages_per_tier = 20
a.per_company = int(options["per_company_cap"])
a.max_credits = 0
bp.cmd_search(a)

# Phase 2 — enrichment (only if requested)
if options.get("enrich_emails"):
    a2 = _Args()
    a2.in_ = {str(raw_path)!r}
    a2.out = {str(enriched_path)!r}
    a2.limit = 0
    a2.max_credits = int(options.get("hard_credit_cap", 5000))
    bp.cmd_enrich(a2)

    # Phase 3 — CSV
    a3 = _Args()
    a3.in_ = {str(enriched_path)!r}
    a3.out = {str(csv_path)!r}
    a3.email_only = True
    a3.limit = 0
    bp.cmd_csv(a3)

    a4 = _Args()
    a4.in_ = {str(enriched_path)!r}
    a4.out = {str(csv_path).replace('.csv', '_all.csv')!r}
    a4.email_only = False
    a4.limit = 0
    bp.cmd_csv(a4)
"""
