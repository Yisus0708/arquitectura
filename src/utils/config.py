"""
Configuration module for the School Grades Data Pipeline.
Loads environment variables from .env and defines standard project paths.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Base Project Directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env file
dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=dotenv_path)

# Database Configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "school_dw")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

# Reproducibility & Pipeline Parameters
RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))

# Project Paths
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = BASE_DIR / os.getenv("RAW_DATA_DIR", "data/raw")
PROCESSED_DATA_DIR = BASE_DIR / os.getenv("PROCESSED_DATA_DIR", "data/processed")
ERRORS_DATA_DIR = BASE_DIR / os.getenv("ERRORS_DATA_DIR", "data/errors")
LOGS_DIR = BASE_DIR / "logs"
SQL_DIR = BASE_DIR / "sql"
DOCS_DIR = BASE_DIR / "docs"

# Logging Level
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
