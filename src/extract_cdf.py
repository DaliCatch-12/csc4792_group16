"""
Extract CDF (Constituency Development Fund) project lists and beneficiary
lists for Mazabuka Central and Magoye constituencies.

These council-published PDFs come in two forms:
  - "native_clean": born-digital text that extracts cleanly with pdfplumber.
  - "ocr": scanned images, or PDFs with a corrupted/garbled embedded text
    layer (broken font ToUnicode maps -> ligature soup like "ffi", "TOANS"
    for "LOANS"). These are rendered to images and re-read with EasyOCR.

Every source list is a numbered record list (serial number + free-text
description covering project/beneficiary name, ward, sector, etc., laid
out inconsistently across documents). Rather than force an unreliable
column split from noisy OCR text, each record is kept as one structured
row: (source metadata) + serial number + the full record text. This is
honest about what can and cannot be reliably separated from these scans.

Outputs:
  data/interim/cdf_projects.csv
  data/interim/cdf_beneficiaries.csv
  data/interim/cdf_notices.csv
  data/interim/ocr_raw_rows.csv   (full OCR audit trail, all pages)
"""
import csv
import re
from pathlib import Path

import pdfplumber

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC_DIR = REPO_ROOT / "raw" / "documents"
OUT_DIR = REPO_ROOT / "data" / "interim"

SN_RE = re.compile(r"^(\d{1,3})[.\)]?\s*(.+)$")

# (filename, year, constituency, dataset, category, extraction_method)
FILES = [
    # --- native, clean text ---
    ("APPROVED-COMMUNITY-PROJECTS-2025-MAGOYE1.pdf", 2025, "Magoye", "projects", "approved", "native"),
    ("LIST-OF-PROPOSED-PROJECTS-MAGOYE.pdf", 2025, "Magoye", "projects", "proposed", "native"),
    ("PROPOSED-PROJECTS-MAZ-CENTRAL..pdf", 2025, "Mazabuka Central", "projects", "approved", "native"),
    ("CDF-2025-UNAPPROVED-COMMUNITY-PROJECT-MAZ-CENTRAL.pdf", 2025, "Mazabuka Central", "projects", "unapproved", "native"),
    ("CDF-2026-SUCCESSFUL-APPLICANTS-FOR-YOUTH-WOMEN-AND-COMMUNITY-GRANTS-MAZABUKA-CENTRAL.pdf", 2026, "Mazabuka Central", "beneficiaries", "youth_women_community_grant", "native"),
    ("CDF-2026-UNAPPROVED-LIST-OF-COMMUNITY-PROJECTS-MAZABUKA-CENTRAL-CONSTITUENCY.pdf", 2026, "Mazabuka Central", "projects", "unapproved", "native"),
    ("SECOND-BATCH-OF-SUCCESSFUL-NAMES-OF-SECONDARY-SCHOOL-LEARNERS-UNDER-SPONSORSHIP-FOR-2026-CDF-MAZ-CENTRAL.pdf", 2026, "Mazabuka Central", "beneficiaries", "secondary_school_bursary", "native"),
    ("SUCCESSFUL-APPLICANT-FOR-CDF-2026-EMPOWERMENT-LOANS-UNDER-REVOLVING-FUD-FOR-MAGOYE-CONSTITUENCY.pdf", 2026, "Magoye", "beneficiaries", "empowerment_loan", "native"),
    ("SUCCESSFUL-APPLICANTS-FOR-THE-CDF-2026-CDF-EMPOWERMENT-LOANS-–-REVOLVING-ACCOUNT-–-MAZABUKA-CENTRAL-CONSTITUENCY.pdf", 2026, "Mazabuka Central", "beneficiaries", "empowerment_loan", "native"),
    ("SUCCESSFUL-NAMES-OF-SECONDARY-SCHOOL-LEARNERS-UDER-SPONSORSHIP-FOR-CDF-2026-BURSARIES-MAZ-CENTRAL.pdf", 2026, "Mazabuka Central", "beneficiaries", "secondary_school_bursary", "native"),
    ("SUCCESSFUL-NAMES-OF-SKILLS-DEVELOPMENT-STUDENTS-UNDER-SPONSORSHIP-FOR-2026-CDF-MAZABUKA-CENTRAL-CONSTITUENCY.pdf", 2026, "Mazabuka Central", "beneficiaries", "skills_development_bursary", "native"),
    # --- needs OCR (scanned image or corrupted font layer) ---
    ("CDF-2024-APPROVED-LIST-OF-COMMUNITY-PROJECTS-MAGOYE-1.pdf", 2024, "Magoye", "projects", "approved", "ocr"),
    ("CDF-2024-APPROVED-LIST-OF-COMMUNITY-PROJECTS-MAZ-CENTRAL-1.pdf", 2024, "Mazabuka Central", "projects", "approved", "ocr"),
    ("CDF-2024-SUCCESSFUL-APPLICANTS-FOR-GRANTS-MAGOYE-CONSTITUENCY.pdf", 2024, "Magoye", "beneficiaries", "youth_women_community_grant", "ocr"),
    ("CDF-2024-SUCCESSFUL-APPLICANTS-FOR-SKLLS-DEVELOPMENT-BURSARIES-MAGOYE-CONSTITUENCY-1.pdf", 2024, "Magoye", "beneficiaries", "skills_development_bursary", "ocr"),
    ("CDF-2024-SUCCESSFUL-APPLICANTS-FOR-YOUTH-WOMEN-AND-COMMUNITY-EMPOWERMENT-GRANTS-MAZABUKA-CENTRAL.pdf", 2024, "Mazabuka Central", "beneficiaries", "youth_women_community_grant", "ocr"),
    ("CDF-2024-SUCCESSFUL-APPLICANTS-FOR-YOUTH-WOMEN-COMMUNITY-EMPOWERMENT-LOANS-MAZABUKA-CENTRAL-CONSTITUENCY.pdf", 2024, "Mazabuka Central", "beneficiaries", "empowerment_loan", "ocr"),
    ("CDF-2024-SUCCESSFUL-SECONDARY-SCHOOL-BURSARY-APPLICANTS-MAGOYE-CONSTITUENCY.pdf", 2024, "Magoye", "beneficiaries", "secondary_school_bursary", "ocr"),
    ("CDF-2024-SUCCESSFUL-YOUTH-WOMEN-COMMUNITY-EMPOWERMENT-LOAN-APPLICANTS-MAGOYE-CONSTITUENCY.pdf", 2024, "Magoye", "beneficiaries", "empowerment_loan", "ocr"),
    ("CDF-2024-SUCCESSFUL-APPLICANTS-FOR-SECONDARYSCHOOL-BURSARIES-MAZABUKA-CENTRAL.pdf", 2024, "Mazabuka Central", "beneficiaries", "secondary_school_bursary", "ocr"),
    ("CDF-2024-SUCCESSFULAPPLICANTSFORSKILLSDEVELOPMENT-BURSARIES-MAZABUKA-CENTRAL.pdf", 2024, "Mazabuka Central", "beneficiaries", "skills_development_bursary", "ocr"),
    ("CDF-2025-APPROVED-COMMUNITY-PROJECT-MAZABUKA-CENTRAL.pdf", 2025, "Mazabuka Central", "projects", "approved", "ocr"),
    ("CDF-2025-UNAPPROVED-COMMUNITY-PROJECTS-MAGOYE.pdf", 2025, "Magoye", "projects", "unapproved", "ocr"),
    ("CDF-2025-UNAPPROVED-PROJECTS-MAZABUKA-CENTRAL-CONSTITUENCY.pdf", 2025, "Mazabuka Central", "projects", "unapproved", "ocr"),
    ("CDF-Updates-Mazabuka-Central.pdf", 2024, "Mazabuka Central", "projects", "status_update", "ocr"),
    ("CDF-Updates-Magoye.pdf", 2024, "Magoye", "projects", "status_update", "native"),
    ("PUBLIC-NOTICE-WARD-DEVELOPMENT-COMMITTEE-ELECTIONS.pdf", 2024, None, "notices", "ward_development_committee_elections", "ocr"),
    ("main-valuation-roll-2024-notice.pdf", 2024, None, "notices", "valuation_roll", "ocr"),
]


def native_lines(path: Path):
    lines = []
    with pdfplumber.open(path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            for line in (page.extract_text() or "").split("\n"):
                lines.append((page_idx, line.strip()))
    return lines


def parse_records(lines_with_pages):
    """lines_with_pages: iterable of (page_idx, text). Groups wrapped lines
    into records keyed by a monotonically increasing leading serial number."""
    records = []
    current = None
    last_sn = 0
    for page_idx, line in lines_with_pages:
        if not line:
            continue
        m = SN_RE.match(line)
        if m and int(m.group(1)) >= last_sn:
            sn = int(m.group(1))
            if sn == last_sn and current is not None:
                current["text"] += " " + line
                continue
            if current:
                records.append(current)
            current = {"sn": sn, "text": m.group(2).strip(), "page": page_idx}
            last_sn = sn
        elif current:
            current["text"] += " " + line
    if current:
        records.append(current)
    return records


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    projects, beneficiaries, notices = [], [], []
    ocr_audit_rows = []

    # Reuse a previous run's OCR output if present (OCR is the slow step, ~1hr
    # for the full batch; re-parsing text is seconds). Delete
    # data/interim/ocr_raw_rows.csv to force a fresh OCR pass.
    cache_path = OUT_DIR / "ocr_raw_rows.csv"
    ocr_cache: dict[str, list[tuple[int, str]]] = {}
    if cache_path.exists():
        with open(cache_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                ocr_cache.setdefault(row["source_file"], []).append((int(row["page"]), row["row_text"]))

    reader = None  # lazily created only if an OCR file is encountered and not cached

    for filename, year, constituency, dataset, category, method in FILES:
        path = DOC_DIR / filename
        if not path.exists():
            print(f"MISSING: {filename}")
            continue

        if method == "native":
            print(f"[native] {filename}")
            lines = native_lines(path)
            records = parse_records(lines)
        elif filename in ocr_cache:
            print(f"[ocr-cached] {filename}")
            row_texts = ocr_cache[filename]
            for page_idx, row_text in row_texts:
                ocr_audit_rows.append(
                    {"source_file": filename, "page": page_idx, "row_text": row_text, "min_confidence": ""}
                )
            records = parse_records(row_texts)
        else:
            print(f"[ocr] {filename}")
            import ocr_utils
            import easyocr

            if reader is None:
                reader = easyocr.Reader(["en"], gpu=False, verbose=False)

            row_texts = []
            for page_idx, row in ocr_utils.ocr_document_rows(reader, path):
                row_texts.append((page_idx, row["row_text"]))
                ocr_audit_rows.append(
                    {
                        "source_file": filename,
                        "page": page_idx,
                        "row_text": row["row_text"],
                        "min_confidence": row["min_confidence"],
                    }
                )
            records = parse_records(row_texts)
            # attach approx confidence by matching back to audit rows on this file/page
            for r in records:
                r["confidence"] = ""

        for r in records:
            row = {
                "source_file": filename,
                "year": year,
                "constituency": constituency,
                "category": category,
                "sn": r["sn"],
                "record_text": re.sub(r"\s+", " ", r["text"]).strip(),
                "page": r["page"],
                "extraction_method": method,
            }
            if dataset == "projects":
                projects.append(row)
            elif dataset == "beneficiaries":
                beneficiaries.append(row)
            else:
                notices.append(row)

    def write_csv(name, rows, fieldnames):
        with open(OUT_DIR / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)

    fields = ["source_file", "year", "constituency", "category", "sn", "record_text", "page", "extraction_method"]
    write_csv("cdf_projects.csv", projects, fields)
    write_csv("cdf_beneficiaries.csv", beneficiaries, fields)
    write_csv("cdf_notices.csv", notices, fields)
    write_csv(
        "ocr_raw_rows.csv",
        ocr_audit_rows,
        ["source_file", "page", "row_text", "min_confidence"],
    )

    print(f"projects={len(projects)} beneficiaries={len(beneficiaries)} notices={len(notices)} ocr_rows={len(ocr_audit_rows)}")


if __name__ == "__main__":
    main()
