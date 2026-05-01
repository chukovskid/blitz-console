"""Filter state ↔ Blitz API request body.

Single source of truth for what filters exist, default values, and how they
serialize into a `/v2/search/people` POST body. The UI reads/writes this
dataclass; the API client takes the dict produced by `to_search_body()`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


# ---- Helpers --------------------------------------------------------------


def _nonempty(d: dict[str, Any]) -> dict[str, Any]:
    """Drop keys whose values are None / [] / "" / {} (recursively)."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, dict):
            sub = _nonempty(v)
            if sub:
                out[k] = sub
        elif v not in (None, "", [], {}):
            out[k] = v
    return out


# ---- Sub-blocks -----------------------------------------------------------


@dataclass
class IncludeExclude:
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)

    def serialize(self) -> dict:
        return _nonempty({"include": list(self.include), "exclude": list(self.exclude)})


@dataclass
class CompanyFilters:
    industry: IncludeExclude = field(default_factory=IncludeExclude)
    name: IncludeExclude = field(default_factory=IncludeExclude)
    keywords: IncludeExclude = field(default_factory=IncludeExclude)  # description keywords
    type_: IncludeExclude = field(default_factory=IncludeExclude)     # company.type
    employee_range: list[str] = field(default_factory=list)
    employee_count_min: int | None = None
    employee_count_max: int | None = None
    founded_year_min: int | None = None
    founded_year_max: int | None = None
    min_linkedin_followers: int | None = None
    hq_country_code: list[str] = field(default_factory=list)
    hq_city: IncludeExclude = field(default_factory=IncludeExclude)
    hq_continent: list[str] = field(default_factory=list)
    hq_sales_region: list[str] = field(default_factory=list)
    linkedin_url: list[str] = field(default_factory=list)

    def serialize(self) -> dict:
        out: dict[str, Any] = {}
        if self.industry.include or self.industry.exclude:
            out["industry"] = self.industry.serialize()
        if self.name.include or self.name.exclude:
            out["name"] = self.name.serialize()
        if self.keywords.include or self.keywords.exclude:
            out["keywords"] = self.keywords.serialize()
        if self.type_.include or self.type_.exclude:
            out["type"] = self.type_.serialize()
        if self.employee_range:
            out["employee_range"] = list(self.employee_range)
        if self.employee_count_min is not None or self.employee_count_max is not None:
            out["employee_count"] = _nonempty(
                {"min": self.employee_count_min, "max": self.employee_count_max}
            )
        if self.founded_year_min is not None or self.founded_year_max is not None:
            out["founded_year"] = _nonempty(
                {"min": self.founded_year_min, "max": self.founded_year_max}
            )
        if self.min_linkedin_followers is not None:
            out["min_linkedin_followers"] = self.min_linkedin_followers
        hq: dict[str, Any] = {}
        if self.hq_country_code:
            hq["country_code"] = list(self.hq_country_code)
        if self.hq_city.include or self.hq_city.exclude:
            hq["city"] = self.hq_city.serialize()
        if self.hq_continent:
            hq["continent"] = list(self.hq_continent)
        if self.hq_sales_region:
            hq["sales_region"] = list(self.hq_sales_region)
        if hq:
            out["hq"] = hq
        if self.linkedin_url:
            out["linkedin_url"] = list(self.linkedin_url)
        return out


@dataclass
class PeopleFilters:
    job_title: IncludeExclude = field(default_factory=IncludeExclude)
    job_title_search_headline: bool = False
    job_level: list[str] = field(default_factory=list)
    job_function: list[str] = field(default_factory=list)
    location_country_code: list[str] = field(default_factory=list)
    location_city: list[str] = field(default_factory=list)
    location_continent: list[str] = field(default_factory=list)
    location_sales_region: list[str] = field(default_factory=list)
    min_connections: int | None = None

    def serialize(self) -> dict:
        out: dict[str, Any] = {}
        title_block: dict[str, Any] = {}
        if self.job_title.include:
            title_block["include"] = list(self.job_title.include)
        if self.job_title.exclude:
            title_block["exclude"] = list(self.job_title.exclude)
        if self.job_title_search_headline:
            title_block["include_linkedin_headline"] = True
        if title_block:
            out["job_title"] = title_block
        if self.job_level:
            out["job_level"] = list(self.job_level)
        if self.job_function:
            out["job_function"] = list(self.job_function)
        loc: dict[str, Any] = {}
        if self.location_country_code:
            loc["country_code"] = list(self.location_country_code)
        if self.location_city:
            loc["city"] = list(self.location_city)
        if self.location_continent:
            loc["continent"] = list(self.location_continent)
        if self.location_sales_region:
            loc["sales_region"] = list(self.location_sales_region)
        if loc:
            out["location"] = loc
        if self.min_connections is not None:
            out["min_connections"] = self.min_connections
        return out


@dataclass
class SearchFilters:
    company: CompanyFilters = field(default_factory=CompanyFilters)
    people: PeopleFilters = field(default_factory=PeopleFilters)

    def to_search_body(self) -> dict:
        body: dict[str, Any] = {}
        c = self.company.serialize()
        if c:
            body["company"] = c
        p = self.people.serialize()
        if p:
            body["people"] = p
        return body

    def is_empty(self) -> bool:
        return not self.to_search_body()

    # ---- (de)serialization for SQLite / JSON view ----

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SearchFilters":
        sf = cls()
        cd = d.get("company") or {}
        cf = sf.company
        for ie_field in ("industry", "name", "keywords", "type_"):
            v = cd.get(ie_field) or {}
            if isinstance(v, dict):
                getattr(cf, ie_field).include = list(v.get("include") or [])
                getattr(cf, ie_field).exclude = list(v.get("exclude") or [])
        cf.employee_range = list(cd.get("employee_range") or [])
        cf.employee_count_min = cd.get("employee_count_min")
        cf.employee_count_max = cd.get("employee_count_max")
        cf.founded_year_min = cd.get("founded_year_min")
        cf.founded_year_max = cd.get("founded_year_max")
        cf.min_linkedin_followers = cd.get("min_linkedin_followers")
        cf.hq_country_code = list(cd.get("hq_country_code") or [])
        hq_city = cd.get("hq_city") or {}
        cf.hq_city.include = list(hq_city.get("include") or [])
        cf.hq_city.exclude = list(hq_city.get("exclude") or [])
        cf.hq_continent = list(cd.get("hq_continent") or [])
        cf.hq_sales_region = list(cd.get("hq_sales_region") or [])
        cf.linkedin_url = list(cd.get("linkedin_url") or [])

        pd_ = d.get("people") or {}
        pf = sf.people
        jt = pd_.get("job_title") or {}
        pf.job_title.include = list(jt.get("include") or [])
        pf.job_title.exclude = list(jt.get("exclude") or [])
        pf.job_title_search_headline = bool(pd_.get("job_title_search_headline"))
        pf.job_level = list(pd_.get("job_level") or [])
        pf.job_function = list(pd_.get("job_function") or [])
        pf.location_country_code = list(pd_.get("location_country_code") or [])
        pf.location_city = list(pd_.get("location_city") or [])
        pf.location_continent = list(pd_.get("location_continent") or [])
        pf.location_sales_region = list(pd_.get("location_sales_region") or [])
        pf.min_connections = pd_.get("min_connections")
        return sf


# ---- Run options (not part of search body, but persisted with ICP) --------


@dataclass
class RunOptions:
    target_leads: int = 1000
    per_company_cap: int = 2
    enrich_emails: bool = True
    enrich_phones: bool = False
    hard_credit_cap: int = 5000

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "RunOptions":
        return cls(
            target_leads=int(d.get("target_leads", 1000)),
            per_company_cap=int(d.get("per_company_cap", 2)),
            enrich_emails=bool(d.get("enrich_emails", True)),
            enrich_phones=bool(d.get("enrich_phones", False)),
            hard_credit_cap=int(d.get("hard_credit_cap", 5000)),
        )


EMPLOYEE_RANGE_BUCKETS = [
    "1-10", "11-50", "51-200", "201-500", "501-1000",
    "1001-5000", "5001-10000", "10001+",
]
