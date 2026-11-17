import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Load private settings from config/.env.
load_dotenv(PROJECT_ROOT / "config" / ".env")

# engine is the connection pool used by every load function.
engine = create_engine(
    URL.create(
        "mysql+pymysql",
        username=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT")),
        database=os.getenv("MYSQL_DB"),
    ),
    pool_pre_ping=True,
)

# engine is lazy; connect() proves the database is reachable.
with engine.connect():
    print("Successfully connected to MySQL!")
