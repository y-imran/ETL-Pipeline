
import pandas as pd

# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
def transform_customers(df):
    df = df.copy() 

    # Capitalize the first letter of each word.
    for column in ("customer_name", "city"):
        df[column] = df[column].str.strip().str.title()

    # Convert emails to lowercase.
    df["email"] = df["email"].str.strip().str.lower()

    return df

# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------
def transform_products(df):
    df = df.copy()

    # Clean product name and category.
    for column in ("product_name", "category"):
        df[column] = df[column].str.strip().str.title()

    # Convert price to numeric.
    df["price"] = pd.to_numeric(df["price"], errors="coerce")

    # Flag negative prices.
    df["price"] = df["price"].clip(lower=0)

    return df


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
def parse_dates(df):
    """Convert the order date columns to real datetimes (day-first CSV format)."""
    df = df.copy()

    # Every order column is written in the same day-first format "with time",
    # e.g. 01-10-2026 09:15:00 -> 1 October 2026 at 09:15. Giving the exact
    # format keeps every value readable
    for column in ("order_date", "created_at", "updated_at"):
        df[column] = pd.to_datetime(df[column], format="%d-%m-%Y %H:%M:%S", errors="coerce")

    return df


def transform_orders(df):
    """Orders: dates are converted so every value can reach a MySQL DATETIME."""
    return parse_dates(df)


# ---------------------------------------------------------------------------
# Order Items
# ---------------------------------------------------------------------------
def transform_order_items(df):
    df = df.copy()

    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")

    # Replace negative values with zero.
    df["quantity"] = df["quantity"].clip(lower=0)
    df["price"] = df["price"].clip(lower=0)

    # Calculate total price.
    df["total_price"] = df["quantity"] * df["price"]

    return df

# ---------------------------------------------------------------------------
# Main transformation function
# ---------------------------------------------------------------------------
def transform_data(raw_data):
    """Prepare the extracted tables for loading.

    Returns two dictionaries:

        raw_tables     the values exactly as the CSVs delivered them.
                       Only the order dates are converted, because the
                       MySQL DATE/DATETIME columns cannot read "01-10-2026".

        staging_tables cleaned tables: trimmed text, proper casing, clipped
                       numbers and the calculated total_price.

    The load functions write raw_tables into raw_<name> and
    staging_tables into staging_<name>.
    """
    raw_tables = {
        "customers": raw_data["customers"].copy(),
        "products": raw_data["products"].copy(),
        "orders": parse_dates(raw_data["orders"]),
        "order_items": raw_data["order_items"].copy(),
    }

    staging_tables = {
        "customers": transform_customers(raw_data["customers"]),
        "products": transform_products(raw_data["products"]),
        "orders": transform_orders(raw_data["orders"]),
        "order_items": transform_order_items(raw_data["order_items"]),
    }

    return raw_tables, staging_tables


if __name__ == "__main__":
    from extract import extract_data

    raw, staging = transform_data(extract_data())

    for name, table in staging.items():
        print(f"{name}: {len(raw[name])} raw rows, {len(table)} staging rows")
