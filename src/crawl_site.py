"""
Crawl www.mazabukacouncil.gov.zm: snapshot every HTML page reachable from the
homepage and download every linked document (PDF/DOC/XLS/CSV).

The site's TLS certificate is expired and issued for a different host
(shared hosting under mlgrd.gov.zm), so requests are made with verify=False.

Outputs (relative to repo root):
  raw/html/<slug>.html          - raw HTML snapshot of each crawled page
  raw/documents/<filename>      - every downloaded document, original filename kept
  raw/manifest_pages.csv        - url, status, saved_as for every page visited
  raw/manifest_documents.csv    - url, link_text, source_page, saved_as, status
"""
import csv
import re
import time
from collections import deque
from pathlib import Path
from typing import cast
from urllib.parse import urljoin, urlparse

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = "https://www.mazabukacouncil.gov.zm"
ALLOWED_HOST = "www.mazabukacouncil.gov.zm"
REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "raw"
HTML_DIR = RAW_DIR / "html"
DOC_DIR = RAW_DIR / "documents"
DOC_EXTS = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv")
MAX_PAGES = 300
DELAY_SECONDS = 0.5
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; CSC4792-Group16-ResearchScraper/1.0; "
        "+mailto:mainzabruce06@gmail.com)"
    )
}

session = requests.Session()
session.headers.update(HEADERS)
session.verify = False


def slugify(url: str) -> str:
    parsed = urlparse(url)
    name = (parsed.path.strip("/") or "home") + ("_" + parsed.query if parsed.query else "")
    name = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").lower()
    return name or "home"


def fetch(url: str):
    for attempt in range(3):
        try:
            resp = session.get(url, timeout=30)
            return resp
        except requests.RequestException as exc:
            if attempt == 2:
                print(f"  ! failed: {url} ({exc})")
                return None
            time.sleep(1)
    return None


def crawl():
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)

    seen_pages = set()
    seen_docs = set()
    queue = deque([BASE + "/"])
    page_rows = []
    doc_rows = []

    while queue and len(seen_pages) < MAX_PAGES:
        url = queue.popleft()
        if url in seen_pages:
            continue
        seen_pages.add(url)

        resp = fetch(url)
        time.sleep(DELAY_SECONDS)
        if resp is None:
            page_rows.append({"url": url, "status": "error", "saved_as": ""})
            continue
        if resp.status_code != 200:
            page_rows.append({"url": url, "status": resp.status_code, "saved_as": ""})
            continue

        content_type = resp.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            continue

        slug = slugify(url)
        html_path = HTML_DIR / f"{slug}.html"
        html_path.write_bytes(resp.content)
        page_rows.append(
            {"url": url, "status": resp.status_code, "saved_as": str(html_path.relative_to(REPO_ROOT))}
        )
        print(f"[page] {url} -> {html_path.name}")

        soup = BeautifulSoup(resp.text, "lxml")
        for a in soup.find_all("a", href=True):
            # bs4 types attribute values as str | AttributeValueList since some
            # attributes (e.g. class) can be multi-valued; href never is.
            href = cast(str, a["href"]).strip()
            if not href or href.startswith("#") or href.startswith(("mailto:", "tel:", "javascript:")):
                continue
            full = urljoin(url, href).split("#")[0]
            parsed = urlparse(full)
            if parsed.netloc and parsed.netloc != ALLOWED_HOST:
                continue

            if full.lower().endswith(DOC_EXTS):
                if full in seen_docs:
                    continue
                seen_docs.add(full)
                doc_rows.append({"url": full, "link_text": a.get_text(strip=True), "source_page": url})
            elif full not in seen_pages and full.startswith(BASE):
                queue.append(full)

    with open(RAW_DIR / "manifest_pages.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["url", "status", "saved_as"])
        writer.writeheader()
        writer.writerows(page_rows)

    print(f"\nDiscovered {len(doc_rows)} unique documents. Downloading...\n")

    for row in doc_rows:
        url = row["url"]
        filename = Path(urlparse(url).path).name
        dest = DOC_DIR / filename
        if dest.exists():
            row["saved_as"] = str(dest.relative_to(REPO_ROOT))
            row["status"] = "cached"
            continue
        resp = fetch(url)
        time.sleep(DELAY_SECONDS)
        if resp is None or resp.status_code != 200:
            row["saved_as"] = ""
            row["status"] = resp.status_code if resp else "error"
            print(f"  ! doc failed ({row['status']}): {url}")
            continue
        dest.write_bytes(resp.content)
        row["saved_as"] = str(dest.relative_to(REPO_ROOT))
        row["status"] = resp.status_code
        print(f"[doc] {filename}")

    with open(RAW_DIR / "manifest_documents.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["url", "link_text", "source_page", "saved_as", "status"])
        writer.writeheader()
        writer.writerows(doc_rows)

    print(f"\nDone. Pages visited: {len(page_rows)}. Documents downloaded: {len(doc_rows)}.")


if __name__ == "__main__":
    crawl()
