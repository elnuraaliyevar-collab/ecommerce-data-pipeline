"""Stage 1: download products from a public REST API and save them as Parquet."""
import logging

import pandas as pd
import requests

from config import (
    API_URL,
    PROCESSED_DIR,
    PRODUCTS_PARQUET,
    RAW_DIR,
    RAW_PRODUCTS_JSON,
    setup_logging,
)

log = logging.getLogger(__name__)

PRODUCT_COLUMNS = [
    "product_id",
    "title",
    "category",
    "price",
    "description",
    "rating_rate",
    "rating_count",
]


def fetch_products(url=API_URL):
    """Send a GET request. Stop with an error if the request failed."""
    # Some servers reject requests without a User-Agent header.
    headers = {"User-Agent": "Mozilla/5.0 (student ecommerce pipeline)"}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    return response


def save_raw_json(response):
    """Keep the original API answer unchanged (raw data)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    RAW_PRODUCTS_JSON.write_bytes(response.content)


def products_to_dataframe(products):
    """Flatten the nested JSON (rating.rate, rating.count) into plain columns."""
    df = pd.json_normalize(products)
    df = df.rename(
        columns={
            "id": "product_id",
            "rating.rate": "rating_rate",
            "rating.count": "rating_count",
        }
    )
    df = df.reindex(columns=PRODUCT_COLUMNS)
    df["product_id"] = df["product_id"].astype("int64")
    return df


def save_parquet(df):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PRODUCTS_PARQUET, engine="pyarrow", index=False)


def run():
    log.info("Requesting products from %s", API_URL)
    response = fetch_products()
    save_raw_json(response)
    df = products_to_dataframe(response.json())
    save_parquet(df)
    log.info("Saved %s products to %s", len(df), PRODUCTS_PARQUET)
    return df


if __name__ == "__main__":
    setup_logging()
    run()
