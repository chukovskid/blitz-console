"""Real-network integration tests for the Blitz API.

Two layers:

- `test_key_info_*` runs whenever a real BLITZ_API_KEY is in the env. The
  /v2/account/key-info endpoint is free (0 credits), so this is a safe
  always-on healthcheck.

- `test_count_*` only runs when BLITZ_RUN_LIVE_COUNT_TESTS=1. Each call
  costs 1 credit. Off by default to avoid burning credits on every push.

Skip rules: tests are skipped when the API key in the environment looks
like the dummy key conftest sets (`blitz-test-…`).
"""

from __future__ import annotations

import os

import pytest

from app.lib.blitz_client import BlitzError, count_people, get_key_info


def _is_real_key() -> bool:
    key = os.environ.get("BLITZ_API_KEY", "")
    return key.startswith("blitz-") and not key.startswith("blitz-test-")


pytestmark = pytest.mark.skipif(
    not _is_real_key(),
    reason="No real BLITZ_API_KEY in env — set one to run integration tests.",
)


# -------------------- free --------------------


def test_key_info_returns_expected_fields():
    info = get_key_info()
    assert info.get("valid") is True
    assert isinstance(info.get("remaining_credits"), int)
    assert info["remaining_credits"] >= 0
    assert isinstance(info.get("max_requests_per_seconds"), int)
    # Must include the search endpoint we actually use.
    assert "/search/people" in info.get("allowed_apis", [])


def test_key_info_credit_balance_positive_for_active_account():
    info = get_key_info()
    if info["remaining_credits"] == 0:
        pytest.skip("Account has 0 credits — can't differentiate from a dead key.")
    assert info["remaining_credits"] > 0


# -------------------- opt-in (1 credit each) --------------------


_RUN_COUNT_TESTS = os.environ.get("BLITZ_RUN_LIVE_COUNT_TESTS") == "1"


@pytest.mark.skipif(
    not _RUN_COUNT_TESTS,
    reason="Set BLITZ_RUN_LIVE_COUNT_TESTS=1 to run (each call costs 1 credit).",
)
def test_count_people_returns_total_results_for_known_filter():
    # Known filter: Software Development companies, 20-100 employees, founders.
    # On the day of writing this returned ~1,694. We just assert the shape
    # and a generous range so the test is robust over time.
    body = {
        "company": {
            "industry": {"include": ["Software Development"]},
            "employee_count": {"min": 20, "max": 100},
        },
        "people": {"job_title": {"include": ["[Founder]"]}},
    }
    resp = count_people(body)
    assert isinstance(resp, dict)
    assert "total_results" in resp
    assert isinstance(resp["total_results"], int)
    assert resp["total_results"] > 100, (
        f"Expected at least 100 founders matching but got {resp['total_results']}"
    )


@pytest.mark.skipif(
    not _RUN_COUNT_TESTS,
    reason="Set BLITZ_RUN_LIVE_COUNT_TESTS=1 to run.",
)
def test_count_people_invalid_industry_returns_zero_or_errors():
    """A bogus industry string should either return 0 or raise — never silently match."""
    body = {
        "company": {"industry": {"include": ["This Is Not A Real Industry XYZ123"]}},
    }
    try:
        resp = count_people(body)
        assert resp.get("total_results", 0) == 0
    except BlitzError:
        pass  # API rejection is also acceptable
