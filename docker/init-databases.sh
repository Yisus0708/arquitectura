#!/bin/bash
set -e

# Creates both databases if not existing in PostgreSQL container
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE school_dw;
    CREATE DATABASE airflow_db;
    GRANT ALL PRIVILEGES ON DATABASE school_dw TO postgres;
    GRANT ALL PRIVILEGES ON DATABASE airflow_db TO postgres;
EOSQL
