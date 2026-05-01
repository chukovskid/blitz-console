"""Unit tests for blitz_pipeline helpers — no API calls."""

from __future__ import annotations

import os

# Make sure import doesn't crash on missing key (it requires it at module level).
os.environ.setdefault("BLITZ_API_KEY", "blitz-test-00000000-0000-0000-0000-000000000000")

import blitz_pipeline as bp  # noqa: E402


def test_deep_merge_replaces_scalars():
    dst = {"a": 1, "b": "old"}
    bp._deep_merge(dst, {"b": "new", "c": 3})
    assert dst == {"a": 1, "b": "new", "c": 3}


def test_deep_merge_recurses_dicts():
    dst = {"company": {"industry": {"include": ["A"]}}}
    bp._deep_merge(dst, {"company": {"hq": {"country_code": ["US"]}}})
    assert dst == {
        "company": {
            "industry": {"include": ["A"]},
            "hq": {"country_code": ["US"]},
        }
    }


def test_deep_merge_lists_replace_not_concat():
    """Lists are replaced wholesale, not concatenated — pinning current behaviour."""
    dst = {"company": {"industry": {"include": ["A", "B"]}}}
    bp._deep_merge(dst, {"company": {"industry": {"include": ["C"]}}})
    assert dst["company"]["industry"]["include"] == ["C"]


def test_dedupe_by_company_per_limit_2():
    p1 = {"linkedin_url": "p1", "experiences": [{"company_linkedin_url": "co/A"}]}
    p2 = {"linkedin_url": "p2", "experiences": [{"company_linkedin_url": "co/A"}]}
    p3 = {"linkedin_url": "p3", "experiences": [{"company_linkedin_url": "co/A"}]}
    p4 = {"linkedin_url": "p4", "experiences": [{"company_linkedin_url": "co/B"}]}

    out = bp.dedupe_by_company([[p1, p2, p3, p4]], per_company_limit=2)
    urls = [p["linkedin_url"] for p in out]
    # Two from co/A (p1, p2), one from co/B (p4) — p3 dropped because cap=2.
    assert urls == ["p1", "p2", "p4"]


def test_dedupe_drops_records_without_company_url():
    p1 = {"linkedin_url": "p1"}  # no experiences
    p2 = {"linkedin_url": "p2", "experiences": [{"company_linkedin_url": "co/A"}]}
    out = bp.dedupe_by_company([[p1, p2]], per_company_limit=2)
    assert [p["linkedin_url"] for p in out] == ["p2"]


def test_dedupe_priority_across_tiers():
    """Tier 0 leads should be picked before tier 1 leads from the same company."""
    tier0 = [{"linkedin_url": "founder", "_tier": "founder",
              "experiences": [{"company_linkedin_url": "co/A"}]}]
    tier1 = [{"linkedin_url": "manager", "_tier": "manager",
              "experiences": [{"company_linkedin_url": "co/A"}]},
             {"linkedin_url": "manager_b", "_tier": "manager",
              "experiences": [{"company_linkedin_url": "co/B"}]}]
    out = bp.dedupe_by_company([tier0, tier1], per_company_limit=1)
    urls = [p["linkedin_url"] for p in out]
    assert urls == ["founder", "manager_b"]  # founder wins co/A; co/B falls to manager
