"""Stage 2b: find and fix problems in the raw sales CSV.

Input : data/raw/sales_raw.csv       (never changed)
Output: data/processed/sales_clean.csv      good rows
        data/processed/sales_rejected.csv   removed rows + the reason
        data/processed/cleaning_report.json numbers for the presentation
"""
import argparse
import json
import logging
from collections import Counter
from pathlib import Path

import pandas as pd

from config import (
    CLEAN_SALES_CSV,
    CLEANING_REPORT_JSON,
    PRODUCTS_PARQUET,
    RAW_SALES_CSV,
    REJECTED_SALES_CSV,
    VALIDATION_REPORT_CSV,
    setup_logging,
)
from schemas import validate_sales

log = logging.getLogger(__name__)

# These values must exist, otherwise the row is useless.
REQUIRED_COLUMNS = [
    "order_id",
    "order_date",
    "customer_name",
    "customer_email",
    "product_id",
    "quantity",
]
# These values are the same for every line of one order.
ORDER_LEVEL_COLUMNS = ["order_date", "customer_name", "customer_email", "city"]
NUMBER_WORDS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5"}


def parse_dates(series):
    """Accept two known formats: 2026-10-25 and 25.10.2026."""
    text = series.str.strip()
    iso = pd.to_datetime(text, format="%Y-%m-%d", errors="coerce")
    dotted = pd.to_datetime(text, format="%d.%m.%Y", errors="coerce")
    return iso.fillna(dotted)


def clean_sales(raw, products):
    """Return (clean rows, rejected rows, report). `raw` must contain only text."""
    df = raw.copy()
    rejected = {}  # row number in raw file -> reason

    def reject(frame, mask, reason):
        """Move rows to the rejected list and return the remaining rows."""
        mask = mask.to_numpy()
        for index in frame.index[mask]:
            rejected[index] = reason
        return frame[~mask].copy()

    report = {
        "rows_raw": len(raw),
        "missing_values_raw": {c: int(v) for c, v in raw.isna().sum().items()},
        "prices_with_decimal_comma": int(df["unit_price"].str.contains(",", na=False).sum()),
        "quantities_written_as_words": int(
            df["quantity"].str.strip().str.lower().isin(NUMBER_WORDS).sum()
        ),
        "dates_in_dd_mm_yyyy_format": int(df["order_date"].str.contains(".", regex=False, na=False).sum()),
    }

    # 1. Exact duplicates: every value is the same as in an earlier row.
    df = reject(df, df.duplicated(), "exact duplicate row")

    # 2. Text: remove extra spaces and make the format consistent.
    for column in ["customer_name", "customer_email", "city"]:
        df[column] = df[column].str.strip()
    df["customer_name"] = df["customer_name"].str.title()
    df["customer_email"] = df["customer_email"].str.lower()
    df["city"] = df["city"].str.title()

    # 3. Data types: text -> numbers and dates. Impossible values become NaN.
    typed_columns = ["order_id", "product_id", "quantity", "unit_price", "order_date"]
    before = df[typed_columns].copy()
    df["order_id"] = pd.to_numeric(df["order_id"], errors="coerce")
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce")
    quantity_text = df["quantity"].str.strip().str.lower().replace(NUMBER_WORDS)
    df["quantity"] = pd.to_numeric(quantity_text, errors="coerce")
    price_text = df["unit_price"].str.strip().str.replace(",", ".", regex=False)
    df["unit_price"] = pd.to_numeric(price_text, errors="coerce")
    df["order_date"] = parse_dates(df["order_date"])
    report["values_that_could_not_be_converted"] = {
        c: int((before[c].notna() & df[c].isna()).sum()) for c in typed_columns
    }

    # 4. Missing order details: copy them from another line of the same order.
    filled = 0
    for column in ORDER_LEVEL_COLUMNS:
        missing_before = int(df[column].isna().sum())
        df[column] = df[column].fillna(df.groupby("order_id")[column].transform("first"))
        filled += missing_before - int(df[column].isna().sum())
    report["order_details_filled_from_same_order"] = filled

    # 5. Rows that still miss a required value cannot be repaired: remove them.
    df = reject(df, df[REQUIRED_COLUMNS].isna().any(axis=1), "missing required value")

    # 6. Product must exist in the API data (it will be a foreign key in PostgreSQL).
    catalog_price = products.set_index("product_id")["price"]
    df = reject(df, ~df["product_id"].isin(catalog_price.index), "unknown product_id")

    # 7. Missing price: use the current catalogue price of this product.
    missing_before = int(df["unit_price"].isna().sum())
    df["unit_price"] = df["unit_price"].fillna(df["product_id"].map(catalog_price))
    report["prices_filled_from_catalogue"] = missing_before - int(df["unit_price"].isna().sum())

    # 8. Business rules.
    bad_quantity = (df["quantity"] <= 0) | (df["quantity"] % 1 != 0)
    df = reject(df, bad_quantity, "quantity must be a positive whole number")
    df = reject(df, df["unit_price"].isna() | (df["unit_price"] <= 0), "unit_price must be positive")

    # 9. Consistency: one order = one customer and one date; one product once per order.
    conflict = (df.groupby("order_id")["customer_email"].transform("nunique") > 1) | (
        df.groupby("order_id")["order_date"].transform("nunique") > 1
    )
    df = reject(df, conflict, "order has several customers or dates")
    df = reject(
        df,
        df.duplicated(subset=["order_id", "product_id"]),
        "same product twice in one order",
    )

    # 10. Final types.
    df["order_id"] = df["order_id"].astype("int64")
    df["product_id"] = df["product_id"].astype("int64")
    df["quantity"] = df["quantity"].astype("int64")
    df["unit_price"] = df["unit_price"].astype("float64").round(2)
    df["order_date"] = df["order_date"].dt.strftime("%Y-%m-%d")
    df = df.sort_values(["order_id", "product_id"]).reset_index(drop=True)

    rejected_rows = raw.loc[list(rejected)].copy()
    rejected_rows["reject_reason"] = list(rejected.values())

    report["rows_clean"] = len(df)
    report["rows_rejected"] = len(rejected_rows)
    report["rejected_by_reason"] = dict(Counter(rejected.values()))
    return df, rejected_rows, report


def run(input_path=RAW_SALES_CSV, output_path=CLEAN_SALES_CSV):
    log.info("Reading %s", input_path)
    raw = pd.read_csv(input_path, dtype=str)  # read everything as text first
    products = pd.read_parquet(PRODUCTS_PARQUET)

    clean, rejected, report = clean_sales(raw, products)
    validate_sales(clean, products["product_id"], VALIDATION_REPORT_CSV)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(output_path, index=False)
    rejected.to_csv(REJECTED_SALES_CSV, index=False)
    CLEANING_REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    log.info("Raw rows: %s | clean rows: %s | rejected rows: %s",
             report["rows_raw"], report["rows_clean"], report["rows_rejected"])
    for reason, count in report["rejected_by_reason"].items():
        log.info("  rejected (%s): %s", reason, count)
    log.info("Saved %s", output_path)
    return clean


def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="Clean the raw sales CSV")
    parser.add_argument("--input", type=Path, default=RAW_SALES_CSV)
    parser.add_argument("--output", type=Path, default=CLEAN_SALES_CSV)
    args = parser.parse_args()
    run(args.input, args.output)


if __name__ == "__main__":
    main()
