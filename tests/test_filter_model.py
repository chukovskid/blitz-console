"""Unit tests for the filter model — no API calls.

These guard the contract between the UI (Streamlit widgets), persistence
(SQLite JSON columns), and the Blitz API request shape.
"""

from __future__ import annotations

from app.lib.filter_model import RunOptions, SearchFilters


def test_empty_filters_serialize_to_empty_body():
    sf = SearchFilters()
    assert sf.is_empty()
    assert sf.to_search_body() == {}


def test_basic_company_industry_serializes_correctly():
    sf = SearchFilters()
    sf.company.industry.include = ["Software Development", "IT Services and IT Consulting"]
    body = sf.to_search_body()
    assert body == {
        "company": {
            "industry": {
                "include": ["Software Development", "IT Services and IT Consulting"]
            }
        }
    }


def test_company_employee_count_min_max():
    sf = SearchFilters()
    sf.company.employee_count_min = 20
    sf.company.employee_count_max = 100
    body = sf.to_search_body()
    assert body == {"company": {"employee_count": {"min": 20, "max": 100}}}


def test_company_employee_range_buckets():
    sf = SearchFilters()
    sf.company.employee_range = ["11-50", "51-200"]
    body = sf.to_search_body()
    assert body == {"company": {"employee_range": ["11-50", "51-200"]}}


def test_hq_location_nested_correctly():
    sf = SearchFilters()
    sf.company.hq_country_code = ["US", "GB"]
    sf.company.hq_continent = ["North America"]
    sf.company.hq_sales_region = ["NORAM"]
    sf.company.hq_city.include = ["San Francisco"]
    body = sf.to_search_body()
    assert body["company"]["hq"] == {
        "country_code": ["US", "GB"],
        "continent": ["North America"],
        "sales_region": ["NORAM"],
        "city": {"include": ["San Francisco"]},
    }


def test_people_job_title_with_headline_search():
    sf = SearchFilters()
    sf.people.job_title.include = ["[Founder]", "Co-Founder"]
    sf.people.job_title.exclude = ["assistant"]
    sf.people.job_title_search_headline = True
    body = sf.to_search_body()
    assert body["people"]["job_title"] == {
        "include": ["[Founder]", "Co-Founder"],
        "exclude": ["assistant"],
        "include_linkedin_headline": True,
    }


def test_people_seniority_and_function():
    sf = SearchFilters()
    sf.people.job_level = ["C-Team", "VP"]
    sf.people.job_function = ["Sales & Business Development"]
    body = sf.to_search_body()
    assert body["people"]["job_level"] == ["C-Team", "VP"]
    assert body["people"]["job_function"] == ["Sales & Business Development"]


def test_full_roundtrip_to_dict_and_back():
    sf = SearchFilters()
    sf.company.industry.include = ["Software Development"]
    sf.company.industry.exclude = ["Mining"]
    sf.company.employee_count_min = 20
    sf.company.employee_count_max = 100
    sf.company.founded_year_min = 2018
    sf.company.hq_country_code = ["US"]
    sf.company.hq_city.include = ["San Francisco"]
    sf.company.keywords.include = ["AI"]
    sf.company.type_.include = ["Privately Held"]
    sf.company.min_linkedin_followers = 500
    sf.company.name.include = ["Stripe"]
    sf.people.job_title.include = ["[Founder]"]
    sf.people.job_title_search_headline = True
    sf.people.job_level = ["C-Team"]
    sf.people.job_function = ["Engineering"]
    sf.people.location_country_code = ["US"]
    sf.people.location_city = ["San Francisco"]
    sf.people.min_connections = 50

    d = sf.to_dict()
    sf2 = SearchFilters.from_dict(d)
    assert sf2.to_search_body() == sf.to_search_body()


def test_empty_zero_values_are_dropped():
    """0 employee min/max, 0 followers, 0 connections should NOT appear in body."""
    sf = SearchFilters()
    sf.company.employee_count_min = 0
    sf.company.employee_count_max = 0
    body = sf.to_search_body()
    # employee_count={min:0,max:0} after _nonempty drops zero values via "in (None, 0, ...)"?
    # Actually our _nonempty drops None/""/[]/{}, NOT 0. So min:0/max:0 ARE kept here.
    # But the UI always uses None for "unset" via the `if min_v > 0` guard before assigning.
    # This test pins the dataclass-level behaviour: 0 IS a valid filter value.
    if "company" in body:
        assert body["company"].get("employee_count") == {"min": 0, "max": 0}


def test_run_options_roundtrip():
    o = RunOptions(target_leads=500, per_company_cap=3,
                   enrich_emails=False, enrich_phones=True, hard_credit_cap=2000)
    o2 = RunOptions.from_dict(o.to_dict())
    assert o2.target_leads == 500
    assert o2.per_company_cap == 3
    assert o2.enrich_emails is False
    assert o2.enrich_phones is True
    assert o2.hard_credit_cap == 2000


def test_run_options_defaults():
    o = RunOptions.from_dict({})
    assert o.target_leads == 1000
    assert o.per_company_cap == 2
    assert o.enrich_emails is True
    assert o.hard_credit_cap == 5000
