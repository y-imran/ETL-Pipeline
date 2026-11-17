# E-commerce ETL Pipeline

A small ETL pipeline that takes raw CSV files, cleans them with pandas, and loads the result into a local MySQL database.

Three stages, one command:

```
data/raw/*.csv  ->  extract  ->  transform (pandas)  ->  load (MySQL)
```

Every dataset is written into two tables:

| Table          | Content                                                        |
| -------------- | -------------------------------------------------------------- |
| `raw_<name>`   | the source values, exactly as the CSVs delivered them          |
| `staging_<name>` | the transformed data: trimmed text, proper casing, real dates, calculated `total_price` |

Two load modes: **full** (every row) and **incremental** (only orders whose `updated_at` is newer than the last saved bookmark). All loading is an *upsert*: new rows are inserted, existing rows are updated - never duplicated. Rows that disappear from the source get `is_deleted = TRUE` (soft deletion).

---

## Clone the repository

```bash
git clone https://github.com/y-imran/ETL-Pipeline.git
cd ETL-Pipeline
```

---

## Setup

### Option A - with uv (recommended, fastest)

[uv](https://docs.astral.sh/uv/) installs Python packages and creates the virtual environment automatically from the lock file in this repository.

```bash
# 1. Install uv (one time):     pip install uv
# 2. Install the dependencies:
uv sync
```

Run the pipeline with `uv run`:

```bash
uv run python scripts/main.py
```

### Option B - with pip

```bash
# 1. Create a virtual environment
python -m venv .venv

# 2. Activate it
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (CMD):
.venv\Scripts\activate.bat
# macOS / Linux:
source .venv/bin/activate

# 3. Install the dependencies
pip install -r requirements.txt
```

Run the pipeline with Python:

```bash
python scripts/main.py
```

---

## MySQL setup

1. Install [MySQL 8](https://dev.mysql.com/downloads/) locally.
2. Create the database and tables:

```bash
mysql -u root -p < scripts/schema.sql
```

3. Create `config/.env` with your own credentials (this file is **not** in the repository, it is ignored by git):

```ini
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DB=ecommerce_etl
```

---

## Run the pipeline

```bash
# Full load: every row of every table
python scripts/main.py

# Incremental load: only orders changed since the last bookmark
python scripts/main.py incremental
```

With uv, prefix both commands with `uv run`.

The console shows the progress of every table, and `logs/pipeline.log` records each run.

---

## Project structure

```
├── data/
│   └── raw/              # the CSV files the pipeline reads
├── scripts/
│   ├── extract.py        # stage 1: read the CSV files
│   ├── transform.py      # stage 2: clean the data (raw + staging versions)
│   ├── load.py           # stage 3: upsert, watermark, soft deletion
│   ├── main.py           # the pipeline entry point
│   ├── db_connection.py  # the MySQL engine (reads config/.env)
│   └── schema.sql        # creates the database tables + watermark
├── logs/                 # pipeline.log is written here
├── requirements.txt      # dependencies for pip users
└── pyproject.toml        # dependencies for uv users
```

---

## How the loading works

| Mechanism       | Where                                             | What it does                                                        |
| --------------- | ------------------------------------------------- | -------------------------------------------------------------------- |
| Upsert          | `load.py` -> `upsert()`                           | `INSERT ... ON DUPLICATE KEY UPDATE`: new key = insert, existing key = update |
| Bookmark        | `etl_watermarks` table                            | Stores the `MAX(updated_at)` already loaded for orders               |
| Incremental     | `load.py` -> `load_incremental()`                 | Loads only orders with `updated_at` newer than the bookmark          |
| Soft deletion   | `load.py` -> `reconcile_deletions()`              | `is_deleted = TRUE` for rows that left the source, `FALSE` when back |

---

## Requirements

- Python 3.12+
- MySQL 8 (local)
