import logging
import sys
from datetime import datetime
from pathlib import Path

from extract import extract_data
from load import load_all, load_incremental
from transform import transform_data

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
    force=True,
)
logger = logging.getLogger(__name__)


def run_pipeline(load_mode):
    """Run the pipeline: extract -> transform -> load.

    load_mode="full":        every row of every table is loaded.
    load_mode="incremental": everything for the other tables, but only
                             orders changed since the last bookmark.
    """
    started = datetime.now()

    logger.info("=" * 50)
    logger.info("E-COMMERCE ETL PIPELINE STARTED (load mode: %s)", load_mode)
    logger.info("=" * 50)

    try:
        logger.info("Starting extraction...")
        raw_data = extract_data()
        logger.info("Extraction completed successfully.")

        logger.info("Starting transformation...")
        raw_tables, staging_tables = transform_data(raw_data)
        logger.info("Transformation completed successfully.")

        if load_mode == "incremental":
            logger.info("Starting incremental loading...")
            load_incremental(raw_tables, staging_tables)
        else:
            logger.info("Starting full loading...")
            load_all(raw_tables, staging_tables)
        logger.info("Loading completed successfully.")

        duration = (datetime.now() - started).total_seconds()
        logger.info("=" * 50)
        logger.info("ETL PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("Execution time: %.2f seconds", duration)
        logger.info("=" * 50)
    except Exception:
        logger.exception("ETL PIPELINE FAILED")
        raise


if __name__ == "__main__":
    # Usage:  python main.py [full | incremental]  (default: full)
    requested_mode = sys.argv[1] if len(sys.argv) > 1 else "full"

    if requested_mode not in ("full", "incremental"):
        logger.error("Unknown load mode '%s' (use 'full' or 'incremental')", requested_mode)
        raise SystemExit(1)

    run_pipeline(requested_mode)
