"""Thin Blitz API client. Only the calls the UI needs directly.

Long-running search/enrich is delegated to blitz_pipeline.py via runner.py;
this module is for synchronous one-shot calls (count preview, key-info,
single-company lookups) that need to return inside one Streamlit rerun.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

API_BASE = "https://api.blitz-api.ai"


class BlitzError(RuntimeError):
    pass


def _api_key() -> str:
    key = os.environ.get("BLITZ_API_KEY", "").strip()
    if not key:
        raise BlitzError("BLITZ_API_KEY env var not set")
    return key


def _request(method: str, path: str, body: dict | None = None, timeout: int = 30) -> dict:
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "x-api-key": _api_key(),
            "accept": "application/json",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        raise BlitzError(f"{method} {path} -> {e.code}: {body_text[:300]}") from e
    except urllib.error.URLError as e:
        raise BlitzError(f"{method} {path} network error: {e}") from e


def get_key_info() -> dict:
    """Returns remaining_credits, max_requests_per_seconds, allowed_apis, active_plans."""
    return _request("GET", "/v2/account/key-info")


def count_people(filters: dict) -> dict:
    """Cheap count call (1 credit). Returns total_results from /v2/search/people.

    `filters` is the request body for /v2/search/people minus max_results/cursor.
    """
    body = dict(filters)
    body["max_results"] = 1
    return _request("POST", "/v2/search/people", body)


def preview_people(filters: dict, n: int = 5) -> dict:
    """Sample preview (n credits). Returns total_results + n example records.

    Used for "does my ICP look right?" sanity check before launching a full
    run. n must be 1–50 per Blitz's max_results limit.
    """
    body = dict(filters)
    body["max_results"] = max(1, min(50, n))
    return _request("POST", "/v2/search/people", body)


def count_companies(filters: dict) -> dict:
    """Cheap count for /v2/search/companies. 1 credit per call (1 result returned)."""
    body = dict(filters)
    body["max_results"] = 1
    return _request("POST", "/v2/search/companies", body)


def employee_finder(company_linkedin_url: str, **filters: Any) -> dict:
    body: dict[str, Any] = {"company_linkedin_url": company_linkedin_url}
    body.update({k: v for k, v in filters.items() if v not in (None, [], "")})
    return _request("POST", "/v2/search/employee-finder", body)


def enrich_email(person_linkedin_url: str) -> dict:
    return _request("POST", "/v2/enrichment/email", {"person_linkedin_url": person_linkedin_url})


def enrich_phone(person_linkedin_url: str) -> dict:
    return _request("POST", "/v2/enrichment/phone", {"person_linkedin_url": person_linkedin_url})


def enrich_company(company_linkedin_url: str) -> dict:
    return _request("POST", "/v2/enrichment/company", {"company_linkedin_url": company_linkedin_url})


def reverse_email(email: str) -> dict:
    return _request("POST", "/v2/enrichment/email-to-person", {"email": email})
