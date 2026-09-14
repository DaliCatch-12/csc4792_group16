"""
Clean the interim extraction outputs and export the final, submission-ready
datasets: pipe ("|") separated CSVs named db-unza26-csc4792-[description].csv,
per the assignment's Kaggle formatting requirements.

Input:  data/interim/*.csv   (produced by extract_budgets.py, extract_cdf.py,
                               build_document_catalog.py)
Output: dataset/db-unza26-csc4792-*.csv
"""
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
INTERIM_DIR = REPO_ROOT / "data" / "interim"
DATASET_DIR = REPO_ROOT / "dataset"


def export(df: pd.DataFrame, name: str):
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATASET_DIR / f"db-unza26-csc4792-{name}.csv"
    df.to_csv(out_path, sep="|", index=False)
    print(f"{out_path.name}: {len(df)} rows, {len(df.columns)} columns")


def clean_budget_revenue():
    df = pd.read_csv(
        INTERIM_DIR / "budget_revenue_items.csv",
        dtype={"category_code": str, "item_code": str},
    )
    # pandas-stubs can't narrow the return type of a to_numeric().astype() chain,
    # so it falsely flags .astype()/.round() here as missing on the inferred type.
    df["amount_kwacha"] = pd.to_numeric(df["amount_kwacha"], errors="coerce").fillna(0).astype("int64")  # type: ignore
    df["period_year"] = pd.to_numeric(df["period_year"], errors="coerce").astype("Int64")  # type: ignore
    df["category_name"] = df["category_name"].str.strip()
    df["item_description"] = df["item_description"].str.strip()
    df = df.drop_duplicates()
    df = df.sort_values(["budget_document_year", "category_code", "item_code", "period_year"]).reset_index(drop=True)
    export(df, "mazabuka_council_budget_revenue_items")


def clean_budget_economic_classification():
    df = pd.read_csv(
        INTERIM_DIR / "budget_economic_classification.csv",
        dtype={"economic_class_code": str},
    )
    # pandas-stubs can't narrow the return type of a to_numeric().astype() chain,
    # so it falsely flags .astype()/.round() here as missing on the inferred type.
    df["amount_kwacha"] = pd.to_numeric(df["amount_kwacha"], errors="coerce").fillna(0).astype("int64")  # type: ignore
    df["period_year"] = pd.to_numeric(df["period_year"], errors="coerce").astype("Int64")  # type: ignore
    df["economic_class_description"] = df["economic_class_description"].str.strip()
    df = df.drop_duplicates().sort_values(["budget_document_year", "economic_class_code", "period_year"]).reset_index(drop=True)
    export(df, "mazabuka_council_budget_economic_classification")


def _title_from_filename(filename: str) -> str:
    stem = Path(filename).stem.replace("-", " ").replace("_", " ")
    return " ".join(stem.split()).title()


def clean_document_catalog():
    df = pd.read_csv(INTERIM_DIR / "document_catalog.csv")
    df["title"] = df["title"].fillna("").str.strip()
    too_short = df["title"].str.len() < 8
    df.loc[too_short, "title"] = df.loc[too_short, "filename"].apply(_title_from_filename)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")  # type: ignore
    df["pages"] = pd.to_numeric(df["pages"], errors="coerce").astype("Int64")  # type: ignore
    df["size_kb"] = pd.to_numeric(df["size_kb"], errors="coerce").round(1)  # type: ignore
    df = df.sort_values(["category", "year", "filename"]).reset_index(drop=True)
    export(df, "mazabuka_council_document_catalog")


def _clean_record_list(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["record_text"] = df["record_text"].str.strip()
    df = df[df["record_text"].str.len() > 0]
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")  # type: ignore
    df["sn"] = pd.to_numeric(df["sn"], errors="coerce").astype("Int64")  # type: ignore
    df = df.drop_duplicates(subset=["source_file", "sn", "record_text"])  # type: ignore
    df = df.sort_values(["year", "constituency", "category", "sn"]).reset_index(drop=True)
    return df


def clean_cdf_projects():
    path = INTERIM_DIR / "cdf_projects.csv"
    if not path.exists():
        print("SKIP cdf_projects.csv (not yet generated)")
        return
    export(_clean_record_list(path), "mazabuka_cdf_projects")


def clean_cdf_beneficiaries():
    path = INTERIM_DIR / "cdf_beneficiaries.csv"
    if not path.exists():
        print("SKIP cdf_beneficiaries.csv (not yet generated)")
        return
    export(_clean_record_list(path), "mazabuka_cdf_beneficiaries")


def clean_cdf_notices():
    path = INTERIM_DIR / "cdf_notices.csv"
    if not path.exists():
        print("SKIP cdf_notices.csv (not yet generated)")
        return
    export(_clean_record_list(path), "mazabuka_cdf_notices")


def main():
    clean_budget_revenue()
    clean_budget_economic_classification()
    clean_document_catalog()
    clean_cdf_projects()
    clean_cdf_beneficiaries()
    clean_cdf_notices()


if __name__ == "__main__":
    main()
