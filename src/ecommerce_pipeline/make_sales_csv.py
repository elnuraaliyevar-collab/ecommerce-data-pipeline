"""Stage 2a: create a small DIRTY sales CSV that uses real product IDs from the API.

The data is generated with a fixed seed, so every team member gets the same file.
Problems added on purpose: duplicate rows, missing values, wrong data types,
mixed date formats, messy text, a negative quantity and an unknown product ID.
"""
import argparse
import logging
import random
from datetime import date, timedelta

import pandas as pd

from config import PRODUCTS_PARQUET, RAW_DIR, RAW_SALES_CSV, setup_logging

log = logging.getLogger(__name__)

SEED = 42

CUSTOMERS = [
    ("Ali Hasanov", "ali@example.com", "Baku"),
    ("Leyla Mammadova", "leyla@example.com", "Ganja"),
    ("Murad Aliyev", "murad@example.com", "Sumqayit"),
    ("Aysel Karimova", "aysel@example.com", "Baku"),
    ("Nigar Huseynova", "nigar@example.com", "Sheki"),
    ("Elvin Sadigov", "elvin@example.com", "Sumqayit"),
    ("Samir Guliyev", "samir@example.com", "Baku"),
    ("Zara Ismayilova", "zara@example.com", "Ganja"),
]


def build_clean_sales(products, seed=SEED):
    """One row = one product line of one order. All values are correct here."""
    rng = random.Random(seed)
    product_ids = sorted(products["product_id"].tolist())
    catalog = dict(zip(products["product_id"], products["price"]))

    rows = []
    for order_id in range(1001, 1021):  # 20 orders
        name, email, city = rng.choice(CUSTOMERS)
        order_date = date(2026, 10, 1) + timedelta(days=rng.randint(0, 27))
        for product_id in rng.sample(product_ids, k=rng.randint(1, 3)):
            rows.append(
                {
                    "order_id": order_id,
                    "order_date": order_date.isoformat(),
                    "customer_name": name,
                    "customer_email": email,
                    "city": city,
                    "product_id": int(product_id),
                    "quantity": rng.randint(1, 4),
                    "unit_price": round(float(catalog[product_id]), 2),
                }
            )
    return pd.DataFrame(rows)


def inject_problems(clean, seed=SEED):
    """Break the clean table in a controlled way."""
    rng = random.Random(seed + 1)
    df = clean.astype(object)  # object columns can hold any text
    n = len(df)
    if n < 30:
        raise ValueError("Not enough rows to inject problems")

    pool = rng.sample(range(n), k=n)  # shuffled row numbers, each used once

    def take(k):
        return [pool.pop() for _ in range(k)]

    # Missing values
    for i in take(2):
        df.at[i, "quantity"] = None
    for i in take(2):
        df.at[i, "customer_email"] = None
    for i in take(3):
        df.at[i, "unit_price"] = None
    for i in take(1):
        df.at[i, "order_date"] = None

    # Incorrect data types
    for i, word in zip(take(2), ["two", "three"]):
        df.at[i, "quantity"] = word  # text instead of a number
    for i in take(3):
        price = float(df.at[i, "unit_price"])
        df.at[i, "unit_price"] = f"{price:.2f}".replace(".", ",")  # "25,50"
    for i in take(4):
        d = date.fromisoformat(df.at[i, "order_date"])
        df.at[i, "order_date"] = d.strftime("%d.%m.%Y")  # other date format

    # Invalid values
    for i in take(1):
        df.at[i, "quantity"] = -1
    for i in take(1):
        df.at[i, "product_id"] = 999  # product does not exist in the API

    # Messy text
    for i in take(2):
        df.at[i, "customer_name"] = f"  {df.at[i, 'customer_name'].lower()} "
        df.at[i, "customer_email"] = df.at[i, "customer_email"].upper()
    for i in take(2):
        df.at[i, "city"] = f" {df.at[i, 'city'].upper()}"

    # Exact duplicate rows (copies of rows that were not changed)
    duplicates = df.iloc[take(3)]
    df = pd.concat([df, duplicates], ignore_index=True)

    return df.sample(frac=1, random_state=seed).reset_index(drop=True)


def run(overwrite=False):
    if RAW_SALES_CSV.exists() and not overwrite:
        log.info("%s already exists. Use --overwrite to create it again.", RAW_SALES_CSV)
        return
    products = pd.read_parquet(PRODUCTS_PARQUET)
    dirty = inject_problems(build_clean_sales(products))
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    dirty.to_csv(RAW_SALES_CSV, index=False)
    log.info("Created %s with %s rows", RAW_SALES_CSV, len(dirty))


if __name__ == "__main__":
    setup_logging()
    parser = argparse.ArgumentParser(description="Create the dirty sample sales CSV")
    parser.add_argument("--overwrite", action="store_true")
    run(overwrite=parser.parse_args().overwrite)
