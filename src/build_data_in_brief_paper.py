"""
Generates the Data in Brief manuscript (docx) for the Mazabuka Municipal
Council dataset, following the section structure of Elsevier's official
Data in Brief article template (data article template v.19, Dec 2024):
Article Information (title/authors/affiliations/keywords/abstract),
Specifications Table, Value of the Data, Background, Data Description,
Experimental Design/Materials/Methods, Limitations, Ethics Statement,
CRediT Author Statement, Acknowledgements, Declaration of Competing
Interests, References.

Dataset row/column counts are pulled live from dataset/*.csv so the paper
never drifts out of sync with the actual exported data.

Output: paper/data_in_brief_mazabuka_council.docx
(export to PDF manually via Word/Google Docs before submission, and fill
in the [ADD ...] placeholders for co-author names/affiliations/roles.)
"""
from pathlib import Path
from typing import cast

import pandas as pd
from docx import Document
from docx.shared import Pt
from docx.styles.style import CharacterStyle

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = REPO_ROOT / "dataset"
OUT_DIR = REPO_ROOT / "paper"

KAGGLE_PROFILE = "https://www.kaggle.com/dalitsozulu101"
KAGGLE_DATASET_URL = "https://www.kaggle.com/datasets/dalitsozulu101/mazabuka-municipal-council-group-16"
GITHUB_URL = "https://github.com/brucemainza/csc4792-group16"
CORRESPONDING_EMAIL = "zdalitso123@gmail.com"
LICENSE_NAME = "CC0 1.0 (Public Domain Dedication)"


def load_stats():
    files = {
        "projects": "db-unza26-csc4792-mazabuka_cdf_projects.csv",
        "beneficiaries": "db-unza26-csc4792-mazabuka_cdf_beneficiaries.csv",
        "notices": "db-unza26-csc4792-mazabuka_cdf_notices.csv",
        "revenue": "db-unza26-csc4792-mazabuka_council_budget_revenue_items.csv",
        "econ": "db-unza26-csc4792-mazabuka_council_budget_economic_classification.csv",
        "catalog": "db-unza26-csc4792-mazabuka_council_document_catalog.csv",
    }
    stats = {}
    for key, filename in files.items():
        path = DATASET_DIR / filename
        df = pd.read_csv(path, sep="|")
        stats[key] = {"df": df, "filename": filename, "rows": len(df), "cols": list(df.columns)}
    return stats


def add_heading(doc, text):
    h = doc.add_heading(text, level=1)
    return h


def add_body(doc, text, italic=False):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.italic = italic
    return p


def add_bullets(doc, items):
    for item in items:
        doc.add_paragraph(item, style="List Bullet")


def add_spec_table(doc, rows):
    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    for label, value in rows:
        row = table.add_row().cells
        row[0].text = label
        row[1].text = value
        row[0].paragraphs[0].runs[0].bold = True
    return table


def build(stats):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = Document()
    style = cast(CharacterStyle, doc.styles["Normal"])
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    total_cdf = stats["projects"]["rows"] + stats["beneficiaries"]["rows"] + stats["notices"]["rows"]

    # --- Article information ---
    doc.add_heading(
        "Dataset on Constituency Development Fund Projects, Council Budgets, and "
        "Administrative Records of Mazabuka Municipal Council, Zambia",
        level=0,
    )

    add_body(
        doc,
        "Authors: Dalitso Zulu*, Bruce Mainza, Chintu Lungu, Frackson Banda, Innocent Tembo "
        "(*corresponding author)",
    )
    add_body(
        doc,
        "Affiliation: University of Zambia (UNZA), School of Natural Sciences, "
        "Department of Computer Science, Great East Road Campus, Lusaka, Zambia.",
    )
    add_body(doc, f"Corresponding author's email address: {CORRESPONDING_EMAIL}")
    add_body(
        doc,
        "Keywords: Constituency Development Fund; local government finance; Zambia; "
        "municipal budget; web scraping; optical character recognition; open government data",
    )

    add_heading(doc, "Abstract")
    add_body(
        doc,
        "This article presents a curated dataset describing the fiscal and administrative "
        "operations of Mazabuka Municipal Council, a local authority in Southern Province, "
        f"Zambia. The dataset comprises {len(stats)} tables covering {total_cdf} Constituency "
        "Development Fund (CDF) records (approved/unapproved/proposed community projects and "
        f"beneficiary lists for bursaries, skills-development sponsorships, and youth/women/"
        f"community empowerment grants and loans across the Mazabuka Central and Magoye "
        f"constituencies, 2024-2026), {stats['revenue']['rows']} approved-budget revenue line "
        f"items and {stats['econ']['rows']} economic-classification summary rows spanning the "
        f"council's 2024, 2025 and 2026 annual budgets, and a catalogue of {stats['catalog']['rows']} "
        "further administrative and governance documents (the Integrated Development Plan, "
        "council meeting minutes, audit reports, financial statements, and legal Acts). Data "
        "were collected by crawling the council's official website and downloading every linked "
        "document, then extracted from PDF sources using a combination of native text parsing "
        "and optical character recognition (OCR) for scanned or corrupted-text documents, "
        "before being cleaned and exported as pipe-separated CSV files. The dataset supports "
        "research on fiscal decentralisation, CDF utilisation, and local government "
        "transparency in Zambia, and is reusable as a template for comparable extraction "
        "pipelines across Zambia's other City, Municipal and Town Councils.",
    )

    # --- Specifications table ---
    add_heading(doc, "Specifications Table")
    add_spec_table(
        doc,
        [
            ("Subject", "Computer Science; Public Administration and Local Government"),
            (
                "Specific subject area",
                "Web-scraped and OCR-extracted local government fiscal (budgets, revenue, "
                "Constituency Development Fund) and administrative open data for a Zambian "
                "municipal council.",
            ),
            ("Type of data", "Table (CSV, pipe-separated)"),
            (
                "Data collection",
                "Documents and HTML pages were crawled from the official Mazabuka Municipal "
                "Council website (all internal pages reachable from the homepage, plus every "
                "linked PDF/DOC/XLS document). PDF tables were extracted directly with "
                "pdfplumber where the document had a usable native text layer; where the "
                "document was a scanned image or had a corrupted embedded text layer, pages "
                "were rendered with pypdfium2 and read with the EasyOCR engine, then "
                "reconstructed into table rows by clustering detected text on vertical "
                "position. All extraction and cleaning code is provided in the accompanying "
                "GitHub repository and Jupyter notebook.",
            ),
            (
                "Data source location",
                "Institution: Mazabuka Municipal Council. City/Region: Mazabuka, Southern "
                "Province, Zambia. Source website: https://www.mazabukacouncil.gov.zm "
                "(catalogued by the Zambian Ministry of Local Government and Rural "
                "Development, https://www.mlgrd.gov.zm).",
            ),
            (
                "Data accessibility",
                f"Repository name: Kaggle. Data identification number/URL: {KAGGLE_DATASET_URL} "
                f"(account: {KAGGLE_PROFILE}). License: {LICENSE_NAME}. "
                f"Direct URL to extraction code and reproducible notebook: {GITHUB_URL}",
            ),
            ("Related research article", "Not applicable."),
        ],
    )

    # --- Value of the data ---
    add_heading(doc, "Value of the Data")
    add_bullets(
        doc,
        [
            "These data provide one of the few machine-readable, structured records of "
            "Constituency Development Fund (CDF) project approvals and beneficiary "
            "allocations for a Zambian municipal council, enabling quantitative tracking of "
            "CDF utilisation against the Local Government (Amendment) Acts of 2023 and 2026.",
            "Researchers in public finance, decentralisation studies, and civic technology "
            "can reuse the budget revenue and economic-classification tables to analyse "
            "locally generated revenue composition (market fees, levies, licenses, local "
            "taxes) and central government grant dependency (LGEF, CDF) over time.",
            "The dataset demonstrates a reusable, documented extraction methodology "
            "(web crawling + native/OCR PDF extraction) that other groups auditing the "
            "remaining 49 Zambian City/Municipal/Town Councils catalogued by the Ministry of "
            "Local Government and Rural Development can adapt directly.",
            "The document catalogue table enables discovery and citation of primary-source "
            "council governance documents (IDP, council minutes, audit reports) that are not "
            "otherwise centrally indexed.",
            "The full raw HTML/PDF corpus and page-level OCR audit trail are retained "
            "alongside the cleaned tables, allowing other researchers to verify, re-extract, "
            "or re-parse any record against its original source document.",
        ],
    )

    # --- Background ---
    add_heading(doc, "Background")
    add_body(
        doc,
        "This dataset was produced as a mini-project for the course CSC 4792: Data Mining "
        "and Warehousing at the University of Zambia. Groups were pre-assigned specific "
        "Zambian City, Municipal, or Town Councils and tasked with extracting, cleaning, and "
        "curating a dataset from each council's official digital footprint. Mazabuka "
        "Municipal Council was assigned to this project team (Team #16). Local authorities "
        "in Zambia play a central role in decentralised service delivery under the Local "
        "Government Act No. 2 of 2019, and recent amendments (Act No. 28 of 2023 and Act No. "
        "76 of 2026) substantially reformed the Local Government Equalisation Fund and "
        "increased Constituency Development Fund allocations. This dataset was compiled to "
        "make the resulting fiscal and administrative footprint of one council empirically "
        "examinable.",
    )

    # --- Data description ---
    add_heading(doc, "Data Description")
    add_body(
        doc,
        "All files use the naming convention db-unza26-csc4792-[description].csv, are UTF-8 "
        "encoded, and use the pipe character '|' as the column separator. Six files are "
        "provided:",
    )
    descriptions = {
        "projects": (
            "CDF community project records (approved, unapproved, proposed, and status "
            "updates) for Mazabuka Central and Magoye constituencies, 2024-2026."
        ),
        "beneficiaries": (
            "CDF beneficiary records: successful applicants for secondary-school bursaries, "
            "skills-development sponsorships, and youth/women/community empowerment grants "
            "and loans, 2024-2026."
        ),
        "notices": (
            "Other CDF-related public notices, including the ward development committee "
            "election notice and the main valuation roll notice."
        ),
        "revenue": (
            "Line-item revenue budget entries (local taxes/rates, fees and charges, "
            "licenses, levies, permits, charges, other income, national/donor support "
            "grants including the Local Government Equalisation Fund and Constituency "
            "Development Fund allocation) from the council's approved 2024, 2025 and 2026 "
            "annual budgets, in tidy long format (one row per item per reported period year)."
        ),
        "econ": (
            "Top-level budget allocation by economic classification (Personal Emoluments, "
            "Goods and Services, Grants and Other Payments, Non-Financial Assets, etc.)."
        ),
        "catalog": (
            "Metadata catalogue of every further document retrieved from the council "
            "website (Integrated Development Plan, council meeting minutes, audit reports, "
            "financial statements, stakeholder engagement plans, legal Act references, "
            "application forms, newsletters), with category, year, constituency (where "
            "applicable), title, source URL, page count, file size, and whether the source "
            "PDF had a usable native text layer."
        ),
    }
    for key in ["projects", "beneficiaries", "notices", "revenue", "econ", "catalog"]:
        s = stats[key]
        p = doc.add_paragraph()
        p.add_run(f"{s['filename']} ").bold = True
        p.add_run(f"({s['rows']} rows; columns: {', '.join(s['cols'])}). ")
        p.add_run(descriptions[key])

    # --- Experimental design, materials and methods ---
    add_heading(doc, "Experimental Design, Materials and Methods")
    add_body(
        doc,
        "Data collection proceeded in five stages, implemented in Python and fully scripted "
        "in the accompanying repository (src/) and documented step-by-step, with executed "
        "outputs, in the accompanying Jupyter notebook "
        "(notebooks/mazabuka_council_data_pipeline.ipynb).",
    )
    add_body(
        doc,
        "1. Web crawling. A breadth-first crawler (src/crawl_site.py) traversed every "
        "internal page reachable from the council homepage (https://www.mazabukacouncil.gov.zm), "
        "using the requests and BeautifulSoup libraries, and downloaded every linked PDF/DOC/"
        "XLS document. The site's TLS certificate was found to be expired and issued for a "
        "different host (shared Ministry of Local Government hosting), so requests were made "
        "with certificate verification explicitly disabled for this single, identified host. "
        "146 pages and 100 unique documents (~376 MB) were retrieved; a full manifest "
        "(source URL, source page, HTTP status, saved path) is retained for provenance.",
    )
    add_body(
        doc,
        "2. Text-layer audit. Every downloaded PDF was opened with pdfplumber to determine "
        "whether it carried a usable native text layer. Manual spot-checking further revealed "
        "that several PDFs nominally containing text layer actually contained corrupted, "
        "unreadable text due to broken font ToUnicode mappings (a common artifact of PDFs "
        "produced by certain office-to-PDF export tools with subsetted fonts) -  these were "
        "reclassified as requiring OCR.",
    )
    add_body(
        doc,
        "3. Budget extraction. The three native, born-digital annual budget PDFs (2024, "
        "2025, 2026) were parsed with a line-pattern extractor (src/extract_budgets.py) that "
        "identifies revenue category headers, item rows, and their associated reporting "
        "years from pdfplumber's extracted text, handling documents where a page contains "
        "multiple revenue category tables and where the column-year header wraps across a "
        "variable number of lines.",
    )
    add_body(
        doc,
        "4. CDF extraction (native + OCR). CDF project and beneficiary list PDFs were "
        "classified as native-clean or requiring OCR. For OCR documents, pages were rendered "
        "to images with pypdfium2 (scale factor 3.0) and read with EasyOCR (English model); "
        "detected word boxes were clustered into rows by vertical centre (src/ocr_utils.py) "
        "to approximate the source table layout. Because column layouts are inconsistent "
        "across documents (varying combinations of ward, zone, sector, type of venture, sex, "
        "NRC number, etc.), each numbered record was retained as a single free-text field "
        "(record_text) rather than being force-split into unreliable columns; a full "
        "page-level OCR row audit trail is retained for verification against source images.",
    )
    add_body(
        doc,
        "5. Document cataloguing and finalisation. Remaining documents (IDP, minutes, audit "
        "reports, legal Acts, etc.) were catalogued by filename-pattern classification "
        "(src/build_document_catalog.py). All interim tables were then cleaned with pandas "
        "(src/finalize_datasets.py): explicit string typing was applied to budget "
        "category/item codes to preserve leading zeros (pandas' automatic type inference "
        "otherwise silently strips them, e.g. '01' -> 1), duplicate rows were removed, and "
        "all tables were exported as pipe-separated CSV files following the "
        "db-unza26-csc4792-[description].csv naming convention.",
    )
    add_body(
        doc,
        "Software: Python 3.14; requests, BeautifulSoup4, lxml (crawling); pdfplumber, "
        "pypdfium2 (PDF parsing/rendering); EasyOCR, PyTorch (OCR); pandas (cleaning); "
        "Jupyter (documentation/reproducibility).",
    )

    # --- Limitations ---
    add_heading(doc, "Limitations")
    add_bullets(
        doc,
        [
            "CDF project and beneficiary records are retained as free-text entries per "
            "numbered record rather than fully split into individual fields (e.g. a "
            "dedicated ward column), because source column layouts are inconsistent across "
            "documents and OCR text is noisy; further structured splitting would require "
            "manual review or a verified reference ward list.",
            "Older (2020-2023) financial statements and some audit reports are lengthy "
            "scanned, multi-page financial tables; these are catalogued but not fully "
            "tabulated in this release, as full OCR of dense financial tables was judged "
            "unreliable without manual verification within the one-week project timeframe.",
            "OCR output (~16 documents, ~80 pages) was not manually verified line-by-line "
            "against source images; users requiring high-precision individual records should "
            "cross-check against the retained raw OCR audit trail and/or the original PDF.",
            "The economic-classification budget summary table was reliably extractable for "
            "the 2025 budget document only, due to inconsistent page layout in the other two "
            "years; the more detailed revenue line-item table covers all three years.",
        ],
    )

    # --- Ethics statement ---
    add_heading(doc, "Ethics Statement")
    add_body(
        doc,
        "This work did not involve human subjects research, animal experiments, or data "
        "collected from social media platforms. All data were extracted from documents "
        "already published in full by Mazabuka Municipal Council on its official public "
        "website as part of its statutory transparency and public-notice obligations under "
        "the Local Government Act No. 2 of 2019, including individually named beneficiaries "
        "of CDF bursaries, grants, and loans, whose names the Council itself published as "
        "successful-applicant notices. No additional personal data beyond what the Council "
        "already disclosed publicly was collected, inferred, or added. The authors have read "
        "and followed the ethical requirements for publication in Data in Brief.",
    )

    # --- CRediT ---
    add_heading(doc, "CRediT Author Statement")
    add_body(
        doc,
        "Dalitso Zulu: Conceptualization, Methodology, Software, Data curation, Writing - "
        "Original Draft. Bruce Mainza: Software, Validation, Writing - Review & Editing. "
        "Chintu Lungu: Data curation, Investigation. Frackson Banda: Investigation, Writing "
        "- Review & Editing. Innocent Tembo: Validation, Writing - Review & Editing. "
        "(Role assignment drafted for completeness - adjust to reflect each member's actual "
        "contribution before submission.)",
    )

    # --- Acknowledgements ---
    add_heading(doc, "Acknowledgements")
    add_body(
        doc,
        "The authors thank the CSC 4792: Data Mining and Warehousing teaching team at the "
        "University of Zambia for guidance on the exemplar dataset structure and the "
        "Constituency Development Fund reporting context. This research did not receive any "
        "specific grant from funding agencies in the public, commercial, or not-for-profit "
        "sectors.",
    )

    # --- Competing interests ---
    add_heading(doc, "Declaration of Competing Interests")
    add_body(
        doc,
        "The authors declare that they have no known competing financial interests or "
        "personal relationships that could have appeared to influence the work reported in "
        "this paper.",
    )

    # --- References ---
    add_heading(doc, "References")
    references = [
        "Republic of Zambia. Ministry of Local Government and Rural Development. "
        "https://www.mlgrd.gov.zm (accessed 2026).",
        "Local Government Act, 2019 (Act No. 2 of 2019). "
        "https://zambialii.org/akn/zm/act/2019/2/eng@2019-04-11",
        "Local Government (Amendment) Act, 2023 (Act No. 28 of 2023). "
        "https://zambialii.org/akn/zm/act/2023/28/eng@2023-12-26",
        "Local Government (Amendment) Act, 2026 (Act No. 76 of 2026). "
        "https://zambialii.org/akn/zm/act/2026/76/eng@2026-06-12",
        "Phiri, L. (2026). A Multi-Source Dataset for CS1 Failure Prediction [Dataset]. "
        "Kaggle. https://www.kaggle.com/datasets/lightonphiri/a-multisource-dataset-for-cs1-failure-prediction",
        "Mazabuka Municipal Council. https://www.mazabukacouncil.gov.zm (accessed 2026).",
    ]
    for i, ref in enumerate(references, 1):
        doc.add_paragraph(f"[{i}] {ref}")

    out_path = OUT_DIR / "data_in_brief_mazabuka_council.docx"
    doc.save(str(out_path))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    build(load_stats())
