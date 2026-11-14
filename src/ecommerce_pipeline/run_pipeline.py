"""Run the whole pipeline: API -> Parquet -> sales CSV -> cleaning -> PostgreSQL."""
import argparse
import logging
import sys

import psycopg2

import clean_sales
import ingest_api
import load_db
import make_sales_csv
from config import setup_logging

log = logging.getLogger(__name__)


def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="E-commerce data pipeline")
    parser.add_argument("--skip-load", action="store_true", help="stop before PostgreSQL")
    args = parser.parse_args()

    log.info("STEP 1/4: products from the REST API -> Parquet")
    ingest_api.run()

    log.info("STEP 2/4: sample sales CSV (created only if it does not exist)")
    make_sales_csv.run()

    log.info("STEP 3/4: clean sales data")
    clean_sales.run()

    if args.skip_load:
        log.info("STEP 4/4 skipped (--skip-load)")
        return

    log.info("STEP 4/4: load into PostgreSQL")
    try:
        load_db.run()
    except psycopg2.OperationalError as error:
        log.error("Cannot connect to PostgreSQL. Check the .env file and that the server is running.")
        log.error(error)
        sys.exit(1)
    log.info("Pipeline finished successfully")


if __name__ == "__main__":
    main()
