"""Loader: writes the transformed DataFrames into MySQL.

Tables per dataset (see schema.sql):
    raw_<name>      the source values, exactly as the CSVs delivered them
                    (only order dates are converted so MySQL can read them)
    staging_<name>  the transformed data: cleaned text and calculated columns

Two entry points:
    load_all(clean_data)          full load: every row of every table
    load_incremental(clean_data)  everything for the other tables, but
                                  only orders whose updated_at is newer
                                  than the saved bookmark

Both modes end with a deletion check: rows that disappeared from the source
get is_deleted = TRUE (soft deletion), rows that come back get it cleared.
"""

import pandas as pd
from sqlalchemy import text

from db_connection import engine

# The primary key of each table, used to compare database rows with the source.
KEYS = {
    "customers": "customer_id",
    "products": "product_id",
    "orders": "order_id",
    "order_items": "order_item_id",
}


# --------------------------------------------------
# 1. Upsert: Insert new rows or update existing rows
# --------------------------------------------------
def upsert(connection, table_name, df, key_column):
    """Insert rows that are new, update rows whose primary key already exists."""

    if df.empty:
        print(f"{table_name}: No records to load.")
        return

    # Convert missing values (NaN/NaT) to None (SQL NULL).
    records = df.astype(object).where(df.notna(), None).to_dict("records")

    columns = ", ".join(df.columns)
    placeholders = ", ".join(f":{col}" for col in df.columns)

    # Update all columns except the primary key.
    update_columns = [
        col for col in df.columns if col != key_column
    ]

    update_clause = ", ".join(
        f"{col} = new_values.{col}" for col in update_columns
    )

    query = text(f"""
        INSERT INTO {table_name} ({columns})
        VALUES ({placeholders}) AS new_values
        ON DUPLICATE KEY UPDATE {update_clause}
    """)

    connection.execute(query, records)

    print(f"{table_name}: {len(df)} rows loaded.")


# --------------------------------------------------
# 2. Watermark: Get the last loaded updated_at value
# --------------------------------------------------
def get_watermark(connection):
    """Return the newest updated_at already loaded for orders."""

    result = connection.execute(text("""
        SELECT last_watermark
        FROM etl_watermarks
        WHERE pipeline_name = 'orders'
    """)).scalar()

    # No bookmark yet (fresh database): start from 1970 so the first
    # incremental run loads every order.
    return pd.Timestamp(result) if result else pd.Timestamp("1970-01-01")


# --------------------------------------------------
# 3. Save the latest watermark
# --------------------------------------------------
def save_watermark(connection, watermark):
    """Move the bookmark forward to the newest loaded updated_at."""

    connection.execute(text("""
        INSERT INTO etl_watermarks (pipeline_name, last_watermark)
        VALUES ('orders', :watermark)
        ON DUPLICATE KEY UPDATE last_watermark = :watermark
    """), {
        "watermark": watermark.to_pydatetime()
    })


# --------------------------------------------------
# 4. Soft deletion: rows that leave the source keep existing
# --------------------------------------------------
def reconcile_deletions(connection, clean_data):
    """is_deleted = TRUE for rows missing from the source; FALSE if they are back.

    Uses the FULL source of every table, not the incremental batch, so an old
    order can be flagged even when its updated_at has not changed.
    """
    print("\n----- DELETION CHECK -----")

    for name, df in clean_data.items():

        if df.empty:
            print(f"{name}: source is empty, flag check skipped.")
            continue

        # Temporary table holding the keys that are currently in the source.
        connection.execute(text("DROP TEMPORARY TABLE IF EXISTS current_keys"))
        connection.execute(text(
            "CREATE TEMPORARY TABLE current_keys ("
            "key_value VARCHAR(255) NOT NULL PRIMARY KEY)"
        ))
        connection.execute(
            text("INSERT INTO current_keys (key_value) VALUES (:key_value)"),
            [{"key_value": str(key)} for key in df[KEYS[name]].drop_duplicates()],
        )

        for table_name in (f"raw_{name}", f"staging_{name}"):
            # A row that is back in the source: remove the flag.
            connection.execute(text(f"""
                UPDATE {table_name} t
                JOIN current_keys c ON t.{KEYS[name]} = c.key_value
                SET t.is_deleted = FALSE
                WHERE t.is_deleted = TRUE OR t.is_deleted IS NULL
            """))
            # A row that is gone from the source: set the flag.
            connection.execute(text(f"""
                UPDATE {table_name} t
                LEFT JOIN current_keys c ON t.{KEYS[name]} = c.key_value
                SET t.is_deleted = TRUE
                WHERE c.key_value IS NULL
                  AND (t.is_deleted = FALSE OR t.is_deleted IS NULL)
            """))

        connection.execute(text("DROP TEMPORARY TABLE IF EXISTS current_keys"))
        print(f"{name}: is_deleted flags updated.")


# --------------------------------------------------
# 5. Load individual tables
# --------------------------------------------------
def load_customers(connection, raw_df, staging_df):
    """Customers: raw keeps the source values, staging the cleaned text."""

    upsert(connection, "raw_customers", raw_df, "customer_id")
    upsert(connection, "staging_customers", staging_df, "customer_id")


def load_products(connection, raw_df, staging_df):
    """Products: raw keeps the source values, staging the cleaned values."""

    upsert(connection, "raw_products", raw_df, "product_id")
    upsert(connection, "staging_products", staging_df, "product_id")


def load_orders(connection, raw_df, staging_df):
    """Orders: rows without updated_at are skipped (they cannot be tracked)."""

    staging_df = staging_df[staging_df["updated_at"].notna()]

    # Keep exactly the same rows from the raw copy.
    raw_df = raw_df.loc[staging_df.index]

    upsert(connection, "raw_orders", raw_df, "order_id")
    upsert(connection, "staging_orders", staging_df, "order_id")


def load_order_items(connection, raw_df, staging_df):
    """Order items: raw keeps source values, staging adds total_price."""

    upsert(connection, "raw_order_items", raw_df, "order_item_id")
    upsert(connection, "staging_order_items", staging_df, "order_item_id")


# --------------------------------------------------
# 6. Full load: Load all available records
# --------------------------------------------------
def load_all(raw_tables, staging_tables):
    """Load raw_tables into raw_<name>, staging_tables into staging_<name>."""

    print("\n========== FULL LOAD STARTED ==========")

    with engine.begin() as connection:

        load_customers(connection, raw_tables["customers"], staging_tables["customers"])
        load_products(connection, raw_tables["products"], staging_tables["products"])
        load_orders(connection, raw_tables["orders"], staging_tables["orders"])
        load_order_items(connection, raw_tables["order_items"], staging_tables["order_items"])

        # Flag rows that disappeared from the source (soft deletion).
        reconcile_deletions(connection, staging_tables)

    print("\n========== FULL LOAD COMPLETED ==========")


# --------------------------------------------------
# 7. Incremental load: Load new and modified orders
# --------------------------------------------------
def load_incremental(raw_tables, staging_tables):
    """Load everything in full, then only orders changed after the bookmark."""

    print("\n========== INCREMENTAL LOAD STARTED ==========")

    with engine.begin() as connection:

        # Other tables are loaded in full.
        load_customers(connection, raw_tables["customers"], staging_tables["customers"])
        load_products(connection, raw_tables["products"], staging_tables["products"])

        # Get the last saved watermark.
        last_watermark = get_watermark(connection)

        # Keep only orders modified after the last watermark.
        orders = staging_tables["orders"]
        orders = orders[
            orders["updated_at"].notna()
            & (orders["updated_at"] > last_watermark)
        ]

        print(f"New or modified orders: {len(orders)}")

        # Load only the selected orders.
        if not orders.empty:

            load_orders(connection, raw_tables["orders"], orders)

            # Save the newest updated_at after successful loading.
            new_watermark = orders["updated_at"].max()
            save_watermark(connection, new_watermark)

            print(f"Watermark updated: {new_watermark}")

        # Order items load last, so their orders already exist.
        load_order_items(connection, raw_tables["order_items"], staging_tables["order_items"])

        # Flag rows that disappeared from the source (soft deletion).
        reconcile_deletions(connection, staging_tables)

    print("\n========== INCREMENTAL LOAD COMPLETED ==========")
