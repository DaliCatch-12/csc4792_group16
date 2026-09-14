"""
Extract structured line-item data from Mazabuka Municipal Council's
"Output Based Annual Budget" PDFs (native, born-digital text; not scanned).

Produces two tidy (long-format) CSVs in data/interim/:
  budget_revenue_items.csv        - revenue line items by code/category/period
  budget_economic_classification.csv - top-level expenditure summary by economic class

Each row is one (item, period) observation so the same schema covers every
budget year regardless of which forward years a given document reports.
"""
import csv
import re
from pathlib import Path

import pdfplumber

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC_DIR = REPO_ROOT / "raw" / "documents"
OUT_DIR = REPO_ROOT / "data" / "interim"

BUDGET_FILES = {
    "Mazabuka-Municipal-Council-2024-Budget.pdf": 2024,
    "Mazabuka-Municipal-Council-2025-Budget.pdf": 2025,
    "MAZABUKA-MUNICIPAL-COUNCIL-2026-BUDGET.pdf": 2026,
}

AMOUNT = r"(?:\(0\)|[\d,]+(?:\.\d+)?)"
CATEGORY_RE = re.compile(r"^(\d{2})\s+([A-Za-z][A-Za-z /&,\-\.\(\)']+)$")
ITEM_RE = re.compile(rf"^(\d{{3}})\s+(.+?)\s+({AMOUNT})\s+({AMOUNT})\s+({AMOUNT})$")
ECON_RE = re.compile(rf"^(\d{{2}})\s+([A-Za-z][A-Za-z /&,\-\.\(\)']+?)\s+({AMOUNT})\s+({AMOUNT})(?:\s+({AMOUNT}))?$")
YEAR_RE = re.compile(r"20\d{2}")


def clean_amount(raw: str):
    if raw == "(0)":
        return 0
    return int(raw.replace(",", ""))


def extract_revenue(pdf, source_file: str, budget_year: int):
    rows = []
    category_code, category_name = None, None
    for page in pdf.pages:
        text = page.extract_text() or ""
        if "CODE REVENUE DESCRIPTION" not in text:
            continue
        lines = text.split("\n")
        # a page commonly holds several revenue category tables, each with its
        # own repeated "CODE REVENUE DESCRIPTION ..." header, so segment on
        # every occurrence instead of stopping at the second one.
        header_positions = [i for i, l in enumerate(lines) if l.startswith("CODE REVENUE DESCRIPTION")]
        header_positions.append(len(lines))

        for seg in range(len(header_positions) - 1):
            start, end = header_positions[seg], header_positions[seg + 1]
            # the year header can wrap across 1-3 lines depending on the document
            # (e.g. "BUDGET 2025 BUDGET 2026 ESTIMATE 2027" vs "APPROVED" / "BUDGET 2026" /
            # "BUDGET 2027 ESTIMATE 2028"), so search a window rather than a fixed offset.
            header_years = YEAR_RE.findall(" ".join(lines[start + 1 : start + 4]))[:3]
            if len(header_years) != 3:
                continue

            for line in lines[start + 1 : end]:
                m_cat = CATEGORY_RE.match(line)
                if m_cat:
                    category_code, category_name = m_cat.group(1), m_cat.group(2).strip()
                    continue
                m_item = ITEM_RE.match(line)
                if m_item:
                    item_code, description, *amounts = m_item.groups()
                    for period_label, amount in zip(header_years, amounts):
                        rows.append(
                            {
                                "source_file": source_file,
                                "budget_document_year": budget_year,
                                "category_code": category_code,
                                "category_name": category_name,
                                "item_code": item_code,
                                "item_description": description.strip(),
                                "period_year": period_label,
                                "amount_kwacha": clean_amount(amount),
                            }
                        )
    return rows


def extract_economic_classification(pdf, source_file: str, budget_year: int):
    rows = []
    for page in pdf.pages:
        text = page.extract_text() or ""
        if "Economic Classification" not in text:
            continue
        lines = text.split("\n")
        header_idx = next(
            (i for i, l in enumerate(lines) if YEAR_RE.search(l) and "BUDGET" in l.upper()), None
        )
        if header_idx is None:
            continue
        header_years = YEAR_RE.findall(" ".join(lines[max(0, header_idx - 1) : header_idx + 1]))[:3]

        for line in lines:
            m = ECON_RE.match(line)
            if not m:
                continue
            code, description, *amounts = m.groups()
            amounts = [a for a in amounts if a is not None]
            years = header_years[-len(amounts):] if header_years else [None] * len(amounts)
            for period_label, amount in zip(years, amounts):
                rows.append(
                    {
                        "source_file": source_file,
                        "budget_document_year": budget_year,
                        "economic_class_code": code,
                        "economic_class_description": description.strip(),
                        "period_year": period_label,
                        "amount_kwacha": clean_amount(amount),
                    }
                )
        break  # only one Economic Classification table per document
    return rows


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    revenue_rows, econ_rows = [], []

    for filename, budget_year in BUDGET_FILES.items():
        path = DOC_DIR / filename
        print(f"Processing {filename} ...")
        with pdfplumber.open(path) as pdf:
            revenue_rows.extend(extract_revenue(pdf, filename, budget_year))
            econ_rows.extend(extract_economic_classification(pdf, filename, budget_year))

    with open(OUT_DIR / "budget_revenue_items.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "source_file",
                "budget_document_year",
                "category_code",
                "category_name",
                "item_code",
                "item_description",
                "period_year",
                "amount_kwacha",
            ],
        )
        w.writeheader()
        w.writerows(revenue_rows)

    with open(OUT_DIR / "budget_economic_classification.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "source_file",
                "budget_document_year",
                "economic_class_code",
                "economic_class_description",
                "period_year",
                "amount_kwacha",
            ],
        )
        w.writeheader()
        w.writerows(econ_rows)

    print(f"Revenue line items: {len(revenue_rows)} rows")
    print(f"Economic classification rows: {len(econ_rows)} rows")


if __name__ == "__main__":
    main()
