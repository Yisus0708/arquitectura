"""
Database helper module for PostgreSQL connectivity and schema management.
"""
from pathlib import Path
from typing import Optional, List, Dict, Any
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import RealDictCursor

from src.utils.config import (
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_DB,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
)
from src.utils.logger import get_logger

logger = get_logger("db_utils")

def get_connection(dbname: Optional[str] = None):
    """
    Establishes and returns a connection to PostgreSQL.
    Defaults to configured POSTGRES_DB.
    """
    database = dbname or POSTGRES_DB
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=database,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            connect_timeout=10,
        )
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database '{database}': {e}")
        raise

def ensure_database_exists() -> None:
    """
    Connects to the default 'postgres' database and creates POSTGRES_DB if it does not exist.
    """
    conn = get_connection(dbname="postgres")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (POSTGRES_DB,))
        if not cur.fetchone():
            logger.info(f"Database '{POSTGRES_DB}' does not exist. Creating it...")
            cur.execute(f'CREATE DATABASE "{POSTGRES_DB}";')
            logger.info(f"Database '{POSTGRES_DB}' created successfully.")
        else:
            logger.info(f"Database '{POSTGRES_DB}' already exists.")
    finally:
        cur.close()
        conn.close()

def ensure_schemas_exist() -> None:
    """
    Ensures that the 4 medallion schemas exist: raw, staging, silver, gold.
    """
    schemas = ["raw", "staging", "silver", "gold"]
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for schema in schemas:
                cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}";')
        conn.commit()
        logger.info(f"Medallion schemas verified: {', '.join(schemas)}")
    finally:
        conn.close()

def execute_sql_file(file_path: Path) -> None:
    """
    Executes all SQL commands from a .sql file inside an isolated transaction.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"SQL file not found: {file_path}")

    logger.info(f"Executing SQL file: {file_path.name}")
    with open(file_path, "r", encoding="utf-8") as f:
        sql = f.read()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        logger.info(f"Executed successfully: {file_path.name}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error executing {file_path.name}: {e}")
        raise
    finally:
        conn.close()

def execute_query(sql: str, params: Optional[tuple] = None) -> None:
    """
    Executes a single DDL or DML query with optional parameters.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Query execution error: {e}")
        raise
    finally:
        conn.close()

def fetch_query(sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    """
    Executes a query and returns results as a list of dictionaries.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()
