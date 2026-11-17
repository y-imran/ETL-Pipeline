from pathlib import Path

import pandas as pd

# PROJECT_ROOT is the main ecommerce_etl folder.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

CSV_FILES = {
    "customers": "customers.csv",
    "products": "products.csv",
    "orders": "orders.csv",
    "order_items": "order_items.csv",
}


def extract_data():
    raw_data = {}

    # Read all CSV files from the raw data folder and store them in a dictionary.
    for key, filename in CSV_FILES.items():
        raw_data[key] = pd.read_csv(PROJECT_ROOT / "data" / "raw" / filename)

    return raw_data


if __name__ == "__main__":
    extract_data()
