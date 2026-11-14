import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "ecommerce_pipeline"))

from clean_sales import clean_sales  # noqa: E402
from load_db import build_tables  # noqa: E402


@pytest.fixture
def products():
    return pd.DataFrame({"product_id": [1, 2, 3], "price": [10.0, 20.0, 30.0]})


def make_raw(*rows):
    defaults = {
        "order_id": "1",
        "order_date": "2026-10-01",
        "customer_name": "Ali Hasanov",
        "customer_email": "ali@example.com",
        "city": "Baku",
        "product_id": "1",
        "quantity": "2",
        "unit_price": "10.00",
    }
    return pd.DataFrame([{**defaults, **row} for row in rows], dtype=str)


def test_exact_duplicates_are_removed(products):
    raw = make_raw({}, {})
    clean, rejected, report = clean_sales(raw, products)
    assert len(clean) == 1
    assert report["rejected_by_reason"] == {"exact duplicate row": 1}


def test_types_are_fixed(products):
    raw = make_raw({"quantity": "two", "unit_price": "10,50", "order_date": "01.10.2026"})
    clean, _, _ = clean_sales(raw, products)
    row = clean.iloc[0]
    assert row["quantity"] == 2
    assert row["unit_price"] == 10.5
    assert row["order_date"] == "2026-10-01"


def test_missing_price_is_filled_from_catalogue(products):
    raw = make_raw({"product_id": "2", "unit_price": None})
    clean, _, report = clean_sales(raw, products)
    assert clean.iloc[0]["unit_price"] == 20.0
    assert report["prices_filled_from_catalogue"] == 1


def test_invalid_rows_are_rejected(products):
    raw = make_raw(
        {"order_id": "1", "product_id": "999"},
        {"order_id": "2", "quantity": "-1"},
        {"order_id": "3", "quantity": None},
    )
    clean, rejected, _ = clean_sales(raw, products)
    assert clean.empty
    assert set(rejected["reject_reason"]) == {
        "unknown product_id",
        "quantity must be a positive whole number",
        "missing required value",
    }


def test_missing_email_is_filled_from_same_order(products):
    raw = make_raw(
        {"order_id": "5", "product_id": "1", "customer_email": None},
        {"order_id": "5", "product_id": "2"},
        {"order_id": "6", "product_id": "3", "customer_email": None},  # single line
    )
    clean, rejected, _ = clean_sales(raw, products)
    assert set(clean["order_id"]) == {5}
    assert (clean["customer_email"] == "ali@example.com").all()
    assert list(rejected["reject_reason"]) == ["missing required value"]


def test_build_tables_links_orders_to_customers(products):
    raw = make_raw(
        {"order_id": "1", "product_id": "1"},
        {"order_id": "1", "product_id": "2"},
        {"order_id": "2", "customer_email": "leyla@example.com", "customer_name": "Leyla"},
    )
    clean, _, _ = clean_sales(raw, products)
    customers, orders, items = build_tables(clean)
    assert len(customers) == 2
    assert len(orders) == 2
    assert len(items) == 3
    assert set(orders["customer_id"]) <= set(customers["customer_id"])
