"""Stage 3: create the PostgreSQL tables and load products and cleaned sales."""
import logging

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

from config import (
    CLEAN_SALES_CSV,
    PRODUCTS_PARQUET,
    SQL_DIR,
    get_db_params,
    setup_logging,
)

log = logging.getLogger(__name__)

PRODUCT_COLUMNS = ["product_id", "title", "category", "price", "description", "rating_rate", "rating_count"]
CUSTOMER_COLUMNS = ["customer_id", "full_name", "email", "city"]
ORDER_COLUMNS = ["order_id", "customer_id", "order_date"]
ORDER_ITEM_COLUMNS = ["order_id", "product_id", "quantity", "unit_price"]


def build_tables(sales):
    """Split the flat sales table into customers, orders and order_items."""
    customers = (
        sales[["customer_email", "customer_name", "city"]]
        .drop_duplicates(subset="customer_email")
        .sort_values("customer_email")
        .reset_index(drop=True)
    )
    customers.insert(0, "customer_id", range(1, len(customers) + 1))
    customers = customers.rename(columns={"customer_name": "full_name", "customer_email": "email"})

    email_to_id = dict(zip(customers["email"], customers["customer_id"]))
    orders = sales[["order_id", "customer_email", "order_date"]].drop_duplicates(subset="order_id").copy()
    orders["customer_id"] = orders["customer_email"].map(email_to_id)
    orders = orders[ORDER_COLUMNS].sort_values("order_id").reset_index(drop=True)

    order_items = sales[ORDER_ITEM_COLUMNS].copy()
    return customers[CUSTOMER_COLUMNS], orders, order_items


def to_rows(df):
    """Convert a DataFrame to a list of plain Python tuples (NaN -> None)."""
    rows = []
    for row in df.itertuples(index=False, name=None):
        rows.append(tuple(None if pd.isna(v) else (v.item() if hasattr(v, "item") else v) for v in row))
    return rows


def insert(cursor, table, columns, df):
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES %s"
    execute_values(cursor, sql, to_rows(df[columns]))
    log.info("Inserted %s rows into %s", len(df), table)


def create_schema(cursor):
    cursor.execute((SQL_DIR / "schema.sql").read_text(encoding="utf-8"))
    log.info("Tables created from sql/schema.sql")


def show_total_sales_by_product(cursor):
    """Run the first query from sql/queries.sql and print the result."""
    text = (SQL_DIR / "queries.sql").read_text(encoding="utf-8")
    first_query = [part.strip() for part in text.split(";") if part.strip()][0]
    cursor.execute(first_query)
    result = pd.DataFrame(cursor.fetchall(), columns=[d[0] for d in cursor.description])
    print("\nTotal sales by product:")
    print(result.to_string(index=False))


def run():
    products = pd.read_parquet(PRODUCTS_PARQUET)
    sales = pd.read_csv(CLEAN_SALES_CSV)
    customers, orders, order_items = build_tables(sales)

    connection = psycopg2.connect(**get_db_params())
    try:
        with connection.cursor() as cursor:  # one transaction: all or nothing
            create_schema(cursor)
            insert(cursor, "products", PRODUCT_COLUMNS, products)
            insert(cursor, "customers", CUSTOMER_COLUMNS, customers)
            insert(cursor, "orders", ORDER_COLUMNS, orders)
            insert(cursor, "order_items", ORDER_ITEM_COLUMNS, order_items)
            show_total_sales_by_product(cursor)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    setup_logging()
    run()
