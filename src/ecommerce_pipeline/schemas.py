"""Quality rules (schema) for the cleaned sales table, written with pandera."""
import pandera.pandas as pa


def build_sales_schema(valid_product_ids):
    """Rules every cleaned row must follow."""
    return pa.DataFrameSchema(
        {
            "order_id": pa.Column(int, pa.Check.gt(0)),
            "order_date": pa.Column(str, pa.Check.str_matches(r"^\d{4}-\d{2}-\d{2}$")),
            "customer_name": pa.Column(str),
            "customer_email": pa.Column(str, pa.Check.str_contains("@")),
            "city": pa.Column(str, nullable=True),
            "product_id": pa.Column(int, pa.Check.isin(list(valid_product_ids))),
            "quantity": pa.Column(int, pa.Check.gt(0)),
            "unit_price": pa.Column(float, pa.Check.gt(0)),
        },
        unique=["order_id", "product_id"],  # same rule as the composite primary key
    )


def validate_sales(df, valid_product_ids, report_path=None):
    """Check the table. Save all rule violations to a CSV if something is wrong."""
    schema = build_sales_schema(valid_product_ids)
    try:
        schema.validate(df, lazy=True)  # lazy=True collects all errors in one run
    except pa.errors.SchemaErrors as error:
        if report_path is not None:
            error.failure_cases.to_csv(report_path, index=False)
        raise
