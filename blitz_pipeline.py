#!/usr/bin/env python3
"""Blitz lead-sourcing pipeline.

Stage 1 (search):  POST /v2/search/people  per priority tier, paginated, deduped by company.
Stage 2 (enrich):  POST /v2/enrichment/email  per surviving lead.
Stage 3 (output):  CSV in SalesHandy-friendly column order.

State is persisted to JSON between stages so a crash doesn't burn credits twice.
Rate-limited to 4 rps (under the 5 rps account cap, leaves headroom).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Iterable

import urllib.request
import urllib.error

API_BASE = "https://api.blitz-api.ai"
API_KEY = os.environ.get("BLITZ_API_KEY", "")
if not API_KEY:
    print("ERROR: set BLITZ_API_KEY env var", file=sys.stderr)
    sys.exit(2)

INDUSTRIES = ["Software Development", "IT Services and IT Consulting"]
EMPLOYEE_MIN = 20
EMPLOYEE_MAX = 100

# Priority tiers — index = priority (lower wins on dedupe).
# Each entry: (label, list_of_title_keywords). Use [Brackets] for exact match.
TIERS: list[tuple[str, list[str]]] = [
    ("founder",   ["[Founder]", "[Co-Founder]", "[Co Founder]", "[Cofounder]"]),
    ("ceo",       ["[CEO]", "[Chief Executive Officer]"]),
    ("vp",        ["VP Marketing", "VP Growth", "VP Sales", "VP Customer Acquisition",
                   "Vice President Marketing", "Vice President Growth", "Vice President Sales"]),
    ("director",  ["Marketing Director", "Growth Director", "Sales Director",
                   "Director of Marketing", "Director of Growth", "Director of Sales",
                   "Director of Customer Acquisition"]),
    ("head",      ["Head of Marketing", "Head of Growth", "Head of Sales",
                   "Head of Customer Acquisition"]),
    ("manager",   ["Marketing Manager", "Growth Manager", "Sales Manager",
                   "Customer Acquisition Manager"]),
]

MIN_INTERVAL_S = 0.25  # 4 rps

# Extra filters merged into every /v2/search/people body. Set by the
# Streamlit UI wrapper to plumb through filters beyond industry/size/title
# (founded_year, hq country/city/continent, job_function, job_level, etc.)
# Deep-merged into body_base in cmd_search.
EXTRA_BODY: dict = {}


def _deep_merge(dst: dict, src: dict) -> dict:
    """Recursive merge: src wins on scalar/list, dicts merge by key."""
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def _request(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "x-api-key": API_KEY,
            "accept": "application/json",
            "content-type": "application/json",
        },
    )
    backoff = 1.0
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            err_body = e.read().decode(errors="replace")
            if e.code == 429:
                time.sleep(backoff)
                backoff *= 2
                continue
            if 500 <= e.code < 600 and attempt < 4:
                time.sleep(backoff)
                backoff *= 2
                continue
            raise RuntimeError(f"{method} {path} -> {e.code}: {err_body}") from e
        except urllib.error.URLError as e:
            if attempt < 4:
                time.sleep(backoff)
                backoff *= 2
                continue
            raise RuntimeError(f"{method} {path} network error: {e}") from e
    raise RuntimeError(f"{method} {path} exhausted retries")


_last_call_t = 0.0


def _throttled(method: str, path: str, body: dict | None = None) -> dict:
    global _last_call_t
    delta = time.monotonic() - _last_call_t
    if delta < MIN_INTERVAL_S:
        time.sleep(MIN_INTERVAL_S - delta)
    out = _request(method, path, body)
    _last_call_t = time.monotonic()
    return out


def get_credit_info() -> dict:
    return _throttled("GET", "/v2/account/key-info")


def search_people_tier(tier_label: str, titles: list[str], page_cap: int) -> list[dict]:
    """Page through Find People for a single tier; return all results."""
    body_base: dict[str, Any] = {
        "company": {
            "industry": {"include": INDUSTRIES},
            "employee_count": {"min": EMPLOYEE_MIN, "max": EMPLOYEE_MAX},
        },
        "people": {
            "job_title": {"include": titles},
        },
        "max_results": 50,
    }
    out: list[dict] = []
    cursor: str | None = None
    pages = 0
    while pages < page_cap:
        body = dict(body_base)
        if cursor:
            body["cursor"] = cursor
        resp = _throttled("POST", "/v2/search/people", body)
        results = resp.get("results", []) or []
        for r in results:
            r["_tier"] = tier_label
        out.extend(results)
        pages += 1
        cursor = resp.get("cursor")
        sys.stderr.write(
            f"  [tier={tier_label}] page {pages}: +{len(results)} (total {len(out)}, cursor={'Y' if cursor else 'N'})\n"
        )
        if not cursor or not results:
            break
    return out


def dedupe_by_company(leads_by_tier: list[list[dict]], per_company_limit: int = 2) -> list[dict]:
    """Across tiers in priority order, keep up to `per_company_limit` leads per company.

    Earlier-tier leads win first slot; later tiers fill remaining slots.
    Within a tier, also dedupe by person LinkedIn URL.
    """
    counts: dict[str, int] = {}
    seen_persons: set[str] = set()
    out: list[dict] = []
    for tier_results in leads_by_tier:
        for r in tier_results:
            company_url = _extract_company_url(r)
            person_url = r.get("linkedin_url")
            if not company_url or not person_url:
                continue
            if person_url in seen_persons:
                continue
            if counts.get(company_url, 0) >= per_company_limit:
                continue
            counts[company_url] = counts.get(company_url, 0) + 1
            seen_persons.add(person_url)
            out.append(r)
    return out


def _extract_company_url(person: dict) -> str | None:
    # Find People response: company info nested in `experiences[0]` or top-level company field.
    # Defensive — try multiple shapes.
    for key in ("company_linkedin_url", "current_company_linkedin_url"):
        if person.get(key):
            return person[key]
    company = person.get("company") or person.get("current_company") or {}
    if isinstance(company, dict):
        for key in ("linkedin_url", "url", "linkedin"):
            if company.get(key):
                return company[key]
    exps = person.get("experiences") or []
    if exps and isinstance(exps, list):
        first = exps[0] or {}
        comp = first.get("company") or {}
        if isinstance(comp, dict):
            for key in ("linkedin_url", "url"):
                if comp.get(key):
                    return comp[key]
        for key in ("company_linkedin_url", "company_url"):
            if first.get(key):
                return first[key]
    return None


def enrich_email(linkedin_url: str) -> dict:
    return _throttled(
        "POST", "/v2/enrichment/email",
        {"person_linkedin_url": linkedin_url},
    )


FILTER_INDUSTRY_LABEL = "Software Development / IT Services and IT Consulting"
FILTER_SIZE_LABEL = f"{EMPLOYEE_MIN}-{EMPLOYEE_MAX}"


def normalize_for_csv(person: dict, email_resp: dict | None) -> dict:
    first = person.get("first_name") or ""
    last = person.get("last_name") or ""
    person_url = person.get("linkedin_url") or ""

    # Current job comes from experiences[0]; prefer job_is_current=True if present.
    exps = person.get("experiences") or []
    current = next((e for e in exps if e.get("job_is_current")), exps[0] if exps else {})
    job_title = (current or {}).get("job_title") or person.get("headline") or ""
    company_name = (current or {}).get("company_name") or ""

    email = ""
    if email_resp and email_resp.get("found"):
        email = email_resp.get("email") or ""

    return {
        "First Name": first,
        "Last Name": last,
        "Email": email,
        "Company Name": company_name,
        "Company Industry": FILTER_INDUSTRY_LABEL,
        "Company Employee Size": FILTER_SIZE_LABEL,
        "Job Title": job_title,
        "LinkedIn URL": person_url,
        "Tier Matched": person.get("_tier", ""),
    }


# ----------------------------- driver -----------------------------


def cmd_search(args: argparse.Namespace) -> None:
    """Search across tiers, persisting raw + deduped output after EVERY page.

    State files:
      <out>.raw.json         — raw results from every page, every tier (resumable)
      <out>                  — deduped leads (max `per_company_limit` per company)
    """
    out_path = Path(args.out)
    raw_path = out_path.with_suffix(out_path.suffix + ".raw")

    raw_by_tier: dict[str, list[dict]] = {label: [] for label, _ in TIERS}
    completed_tiers: set[str] = set()
    if raw_path.exists():
        try:
            saved = json.loads(raw_path.read_text())
            raw_by_tier.update(saved.get("by_tier", {}))
            completed_tiers = set(saved.get("completed_tiers", []))
            sys.stderr.write(
                f"Resuming search. completed tiers: {sorted(completed_tiers)}. "
                f"raw counts: { {k: len(v) for k, v in raw_by_tier.items()} }\n"
            )
        except Exception:
            pass

    info = get_credit_info()
    start_credits = info["remaining_credits"]
    sys.stderr.write(f"Credits before search: {start_credits}\n")

    def persist():
        raw_path.write_text(json.dumps(
            {"by_tier": raw_by_tier, "completed_tiers": sorted(completed_tiers)},
            indent=2,
        ))
        ordered_tier_lists = [raw_by_tier.get(label, []) for label, _ in TIERS]
        deduped = dedupe_by_company(ordered_tier_lists, per_company_limit=args.per_company)
        out_path.write_text(json.dumps(deduped, indent=2))
        return len(deduped)

    for label, titles in TIERS:
        if label in completed_tiers and len(raw_by_tier.get(label, [])) > 0:
            sys.stderr.write(f"== Tier {label}: already completed, skipping\n")
            continue
        sys.stderr.write(f"== Tier {label}: {titles}\n")
        body_base: dict[str, Any] = {
            "company": {
                "industry": {"include": INDUSTRIES},
                "employee_count": {"min": EMPLOYEE_MIN, "max": EMPLOYEE_MAX},
            },
            "people": {"job_title": {"include": titles}},
            "max_results": 50,
        }
        # Merge UI-supplied extra filters (country, function, level, etc).
        # Tier-supplied job_title.include wins; everything else from EXTRA_BODY.
        if EXTRA_BODY:
            saved_titles = body_base["people"]["job_title"]
            _deep_merge(body_base, {k: v for k, v in EXTRA_BODY.items()
                                     if k not in ("max_results", "cursor")})
            body_base["people"]["job_title"] = saved_titles
        cursor = None
        for page in range(1, args.pages_per_tier + 1):
            # Hard credit cap check
            if args.max_credits:
                spent = start_credits - get_credit_info()["remaining_credits"]
                if spent >= args.max_credits:
                    sys.stderr.write(f"Hit search credit cap at {spent}. Stopping.\n")
                    persist()
                    return
            body = dict(body_base)
            if cursor:
                body["cursor"] = cursor
            try:
                resp = _throttled("POST", "/v2/search/people", body)
            except Exception as e:
                sys.stderr.write(f"  page {page} failed: {e}\n")
                break
            results = resp.get("results", []) or []
            for r in results:
                r["_tier"] = label
            raw_by_tier[label].extend(results)
            cursor = resp.get("cursor")
            unique_after = persist()
            sys.stderr.write(
                f"  [tier={label}] page {page}: +{len(results)} "
                f"(tier total {len(raw_by_tier[label])}, unique-after-dedupe {unique_after}, "
                f"cursor={'Y' if cursor else 'N'})\n"
            )
            if not cursor or not results:
                break
            if unique_after >= args.target * 2:
                sys.stderr.write("  reached 2x target buffer; stopping tier walk\n")
                completed_tiers.add(label)
                persist()
                return
        completed_tiers.add(label)
        persist()

    info_after = get_credit_info()
    final_unique = persist()
    sys.stderr.write(
        f"Search done. unique leads: {final_unique}. "
        f"credits used: {start_credits - info_after['remaining_credits']}. "
        f"remaining: {info_after['remaining_credits']}\n"
    )


TIER_PRIORITY = {label: i for i, (label, _) in enumerate(TIERS)}


def cmd_enrich(args: argparse.Namespace) -> None:
    in_path = Path(args.in_)
    out_path = Path(args.out)
    deduped = json.loads(in_path.read_text())
    # Sort by tier priority (founder first), then by name for determinism.
    deduped.sort(key=lambda p: (TIER_PRIORITY.get(p.get("_tier", ""), 999), p.get("full_name") or ""))

    info = get_credit_info()
    start_credits = info["remaining_credits"]
    sys.stderr.write(f"Credits before enrichment: {start_credits}\n")
    if args.max_credits:
        sys.stderr.write(f"Hard cap: {args.max_credits} credits this stage\n")

    # Resume from previous output if it exists.
    enriched: list[dict] = []
    seen_urls: set[str] = set()
    if out_path.exists():
        try:
            enriched = json.loads(out_path.read_text())
            seen_urls = {e["person"].get("linkedin_url") for e in enriched if e.get("person")}
            sys.stderr.write(f"Resuming: {len(enriched)} previously enriched\n")
        except Exception:
            enriched = []

    found_count = sum(1 for e in enriched if (e.get("email_resp") or {}).get("found"))

    # Estimate cost locally (~3 credits/attempt observed); only ping account API every 25 to true up.
    EST_PER_ATTEMPT = 3
    last_true_spent = 0
    attempts_since_check = 0
    try:
        for i, person in enumerate(deduped, start=1):
            url = person.get("linkedin_url") or person.get("profile_url")
            if not url or url in seen_urls:
                continue
            est_spent = last_true_spent + attempts_since_check * EST_PER_ATTEMPT
            if args.max_credits and est_spent >= args.max_credits:
                # Confirm with real API before stopping.
                last_true_spent = start_credits - get_credit_info()["remaining_credits"]
                attempts_since_check = 0
                if last_true_spent >= args.max_credits:
                    sys.stderr.write(f"Hit credit cap at {last_true_spent}. Stopping.\n")
                    break
            if args.limit and len(enriched) >= args.limit:
                break
            try:
                email_resp = enrich_email(url)
            except Exception as e:
                sys.stderr.write(f"  [{i}] enrich failed: {e}\n")
                email_resp = None
            if email_resp and email_resp.get("found"):
                found_count += 1
            enriched.append({"person": person, "email_resp": email_resp})
            seen_urls.add(url)
            attempts_since_check += 1
            n = len(enriched)
            if n % 25 == 0 or n <= 5:
                last_true_spent = start_credits - get_credit_info()["remaining_credits"]
                attempts_since_check = 0
                sys.stderr.write(
                    f"  [{n}] tier={person.get('_tier')} hits={found_count} "
                    f"({100*found_count/n:.0f}%) credits_used={last_true_spent}\n"
                )
                # Persist incrementally to survive crashes.
                out_path.write_text(json.dumps(enriched, indent=2))
    finally:
        out_path.write_text(json.dumps(enriched, indent=2))
        end_credits = get_credit_info()["remaining_credits"]
        sys.stderr.write(
            f"Enrichment done. emails found: {found_count}/{len(enriched)}. "
            f"credits used: {start_credits - end_credits}. remaining: {end_credits}\n"
        )
        sys.stderr.write(f"Wrote {out_path}\n")


def cmd_csv(args: argparse.Namespace) -> None:
    in_path = Path(args.in_)
    out_path = Path(args.out)
    enriched = json.loads(in_path.read_text())
    rows = [normalize_for_csv(e["person"], e.get("email_resp")) for e in enriched]
    if args.email_only:
        rows = [r for r in rows if r["Email"]]
    if args.limit:
        rows = rows[: args.limit]
    fields = [
        "First Name", "Last Name", "Email",
        "Company Name", "Company Industry", "Company Employee Size",
        "Job Title", "LinkedIn URL", "Tier Matched",
    ]
    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    sys.stderr.write(f"Wrote {len(rows)} rows -> {out_path}\n")


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search")
    s.add_argument("--out", required=True)
    s.add_argument("--target", type=int, default=1000)
    s.add_argument("--pages-per-tier", type=int, default=20)
    s.add_argument("--per-company", type=int, default=2,
                   help="Max leads kept per company after dedupe")
    s.add_argument("--max-credits", type=int, default=0,
                   help="Hard cap on credits this stage")
    s.set_defaults(func=cmd_search)

    e = sub.add_parser("enrich")
    e.add_argument("--in", dest="in_", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--limit", type=int, default=0)
    e.add_argument("--max-credits", type=int, default=0,
                   help="Hard cap on credits to spend in this stage (0 = no cap)")
    e.set_defaults(func=cmd_enrich)

    c = sub.add_parser("csv")
    c.add_argument("--in", dest="in_", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--email-only", action="store_true")
    c.add_argument("--limit", type=int, default=0)
    c.set_defaults(func=cmd_csv)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
