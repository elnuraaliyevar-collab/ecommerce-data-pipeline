"""Project settings: file paths, API address and database connection."""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

API_URL = "https://fakestoreapi.com/products"

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
SQL_DIR = BASE_DIR / "sql"

RAW_PRODUCTS_JSON = RAW_DIR / "products.json"
RAW_SALES_CSV = RAW_DIR / "sales_raw.csv"
PRODUCTS_PARQUET = PROCESSED_DIR / "products.parquet"
CLEAN_SALES_CSV = PROCESSED_DIR / "sales_clean.csv"
REJECTED_SALES_CSV = PROCESSED_DIR / "sales_rejected.csv"
CLEANING_REPORT_JSON = PROCESSED_DIR / "cleaning_report.json"
VALIDATION_REPORT_CSV = PROCESSED_DIR / "validation_report.csv"


def get_db_params():
    """Read database settings from environment variables (.env file)."""
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "dbname": os.getenv("DB_NAME", "ecommerce"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", ""),
    }


def setup_logging():
    """Print log messages with a time and a level."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )
