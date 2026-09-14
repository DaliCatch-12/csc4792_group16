"""
Build a catalog of every document downloaded from the council website:
filename, category, year, constituency, title, source URL, page count,
file size, and whether it had a usable native text layer.

This captures administrative/report-type sources (IDP, council minutes,
audit reports, legal Acts, stakeholder engagement plans, etc.) that were
not deep-parsed into their own line-item CSVs, so they remain traceable
and citable in the dataset per the assignment's documentation requirements.

Output: data/interim/document_catalog.csv
"""
import csv
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "raw"
DOC_DIR = RAW_DIR / "documents"
OUT_DIR = REPO_ROOT / "data" / "interim"

CATEGORY_RULES = [
    (r"CDF.*(APPROVED|UNAPPROVED|PROPOSED).*PROJECT|APPROVED-COMMUNITY-PROJECT|LIST-OF-PROPOSED-PROJECTS|PROPOSED-PROJECTS", "cdf_project_list"),
    (r"CDF-Updates", "cdf_project_status_update"),
    (r"BURSAR|SKILLS-DEVELOPMENT|SECONDARY-SCHOOL-LEARNERS|SECONDARY.SCHOOL", "cdf_bursary_beneficiary_list"),
    (r"EMPOWERMENT-LOAN|LOAN-APPLICANTS|EMPOWERMENT-GRANT|FOR-GRANTS|COMMUNITY-GRANT", "cdf_grant_loan_beneficiary_list"),
    (r"CDF-GUIDELINES|CONSTITUENCY-DEVELOPMENT-FUND", "cdf_policy_guideline"),
    (r"loan-agreement|loan-application|^grant\.pdf", "cdf_application_form_template"),
    (r"BUDGET-CONSULTATIVE|BUDGET-PRPARATION|BUDGET-PREPARATION|STAKEHOLDERS-ENGANGEMENT|STAKEHOLDERS-CONSULTATIVE|BUSINESS-STAKEHOLDERS", "budget_consultative_meeting"),
    (r"^Mazabuka-Municipal-Council-\d{4}-Budget|^MAZABUKA-MUNICIPAL-COUNCIL-\d{4}-BUDGET", "approved_annual_budget"),
    (r"FINANCIAL-STATEMENT|Financial-statement", "financial_statement"),
    (r"Auditors-Report|AUDITS-REPORT", "audit_report"),
    (r"BI-Annual|BI-ANNUAL", "bi_annual_performance_report"),
    (r"Council-Minutes|COUNCIL-MINUETS|Minutes-of-Council|COUNCIL-MINUTES", "council_minutes"),
    (r"COMMUNITY-ENGAGEMENT-MINUTES|SIGNED-MINUTES", "community_engagement_minutes"),
    (r"Intergrated-Development-Plan|Integrated-Development-Plan", "integrated_development_plan"),
    (r"WARD-DEVELOPMENT-COMMITTEE", "ward_development_committee_notice"),
    (r"valuation-roll", "valuation_roll_notice"),
    (r"STAKEHOLDER-ENGAGEMENT-PLAN|Citizen_Engagement_Strategy", "stakeholder_engagement_plan"),
    (r"Debt-Arrears", "debt_arrears_monitoring"),
    (r"National-Decentralisation-Policy", "national_policy_reference"),
    (r"TRIBUNAL-SITTING-ADVERT|Notice-Cash-for-Work|BUSINESS-STAKEHOLDERS-ENGANGEMENT", "public_notice"),
    (r"NEWSLETTER|NEWS-LETTER", "newsletter"),
    (r"INVESTMENT-PROFILE|ESTATES", "investment_profile"),
    (r"Act-No|-Act-\d{4}|-Act-\d{2}-of|ACT-No", "legal_act_reference"),
]

YEAR_RE = re.compile(r"(20\d{2})")


def categorize(filename: str) -> str:
    for pattern, category in CATEGORY_RULES:
        if re.search(pattern, filename, re.IGNORECASE):
            return category
    return "other"


def guess_constituency(filename: str):
    fname_upper = filename.upper()
    has_magoye = "MAGOYE" in fname_upper
    has_central = "MAZ-CENTRAL" in fname_upper or "MAZABUKA-CENTRAL" in fname_upper or "MAZ CENTRAL" in fname_upper
    if has_magoye and has_central:
        return "Both"
    if has_magoye:
        return "Magoye"
    if has_central:
        return "Mazabuka Central"
    return ""


def load_text_audit():
    audit = {}
    path = RAW_DIR / "pdf_text_audit.csv"
    if not path.exists():
        return audit
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            audit[row["file"]] = row
    return audit


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit = load_text_audit()

    best_by_file = {}
    with open(RAW_DIR / "manifest_documents.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not row["saved_as"]:
                continue
            filename = Path(row["saved_as"]).name
            existing = best_by_file.get(filename)
            if existing is None or (not existing["link_text"] and row["link_text"]):
                best_by_file[filename] = row

    catalog_rows = []
    for filename, row in sorted(best_by_file.items()):
        info = audit.get(filename, {})
        year_match = YEAR_RE.search(filename)
        catalog_rows.append(
            {
                "filename": filename,
                "category": categorize(filename),
                "year": year_match.group(1) if year_match else "",
                "constituency": guess_constituency(filename),
                "title": row["link_text"] or filename,
                "source_url": row["url"],
                "source_page": row["source_page"],
                "pages": info.get("pages", ""),
                "size_kb": info.get("size_kb", ""),
                "has_native_text_layer": info.get("has_text_layer", ""),
            }
        )

    with open(OUT_DIR / "document_catalog.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "filename",
                "category",
                "year",
                "constituency",
                "title",
                "source_url",
                "source_page",
                "pages",
                "size_kb",
                "has_native_text_layer",
            ],
        )
        w.writeheader()
        w.writerows(catalog_rows)

    print(f"catalog rows: {len(catalog_rows)}")
    from collections import Counter

    print(Counter(r["category"] for r in catalog_rows))


if __name__ == "__main__":
    main()
