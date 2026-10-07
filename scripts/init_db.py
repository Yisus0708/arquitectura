"""
Database initialization script.
Ensures that the analytical database 'school_dw' and the medallion schemas
(raw, staging, silver, gold) exist in PostgreSQL.
"""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.db import ensure_database_exists, ensure_schemas_exist
from src.utils.logger import get_logger

logger = get_logger("init_db")

def main():
    logger.info("Starting database and schema initialization...")
    ensure_database_exists()
    ensure_schemas_exist()
    logger.info("PostgreSQL database and schemas ready for ingestion and transformation.")

if __name__ == "__main__":
    main()
