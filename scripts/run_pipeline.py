"""
Autonomous End-to-End Pipeline Runner.
Executes all stages of the School Grades data pipeline sequentially:
1. Ensure Database & Schemas Exist (raw, staging, silver, gold)
2. Generate Synthetic Data (seed fixed, with controlled anomalies)
3. Validate Raw Data (quarantine invalid records into data/errors/)
4. Load Raw into PostgreSQL
5. Transform Raw -> Staging (type casting, whitespace stripping, filters)
6. Transform Staging -> Silver (relational schema, PK, FK, NOT NULL, CHECK constraints)
7. Transform Silver -> Gold (star schema dimensions, facts, analytical business marts)
8. Run Quality Assurance Pytest Suite

Usage:
    python scripts/run_pipeline.py
"""
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.db import ensure_database_exists, ensure_schemas_exist
from src.utils.logger import get_logger
from src.ingestion.generate_data import main as run_generation
from src.validation.validate_data import run_validation
from src.loading.load_raw import load_all_raw
from src.transformation.transform_staging import run_staging_transformations
from src.transformation.transform_silver import run_silver_transformations
from src.transformation.transform_gold import run_gold_transformations

logger = get_logger("pipeline_runner")


def execute_pipeline(generate_data: bool = False) -> bool:
    start_time = time.time()
    logger.info("============================================================================")
    logger.info("   INICIANDO EJECUCIÓN END-TO-END DEL PIPELINE DE CALIFICACIONES ESCOLARES   ")
    logger.info("============================================================================")

    stages = [
        ("0. Verificación de BD y Esquemas Medallion", lambda: (ensure_database_exists(), ensure_schemas_exist())),
    ]

    if generate_data:
        stages.append(("1. Ingesta y Generación de Datos Sintéticos", run_generation))

    stages.extend([
        ("2. Validación de Calidad y Cuarentena de Errores", run_validation),
        ("3. Carga Idempotente a PostgreSQL Raw", load_all_raw),
        ("4. Transformación y Limpieza a Staging", run_staging_transformations),
        ("5. Construcción de Capa Relacional Silver", run_silver_transformations),
        ("6. Construcción de Modelo Estrella y Marts Gold", run_gold_transformations),
    ])

    for stage_name, stage_fn in stages:
        logger.info(f"\n>>> INICIANDO ETAPA: {stage_name}")
        stage_start = time.time()
        try:
            stage_fn()
            duration = round(time.time() - stage_start, 2)
            logger.info(f">>> [OK] Etapa completada exitosamente en {duration}s: {stage_name}")
        except Exception as e:
            logger.error(f">>> [ERROR] Falló la etapa '{stage_name}': {e}", exc_info=True)
            return False

    # Etapa 7: Pruebas automatizadas de calidad con pytest
    logger.info("\n>>> INICIANDO ETAPA: 7. Ejecución de Suite de Pruebas Pytest")
    import pytest
    tests_path = str(Path(__file__).resolve().parent.parent / "tests")
    test_exit_code = pytest.main(["-v", tests_path])

    if test_exit_code != 0:
        logger.error(f">>> [ERROR] Pruebas de calidad fallaron con código {test_exit_code}")
        return False

    total_duration = round(time.time() - start_time, 2)
    logger.info("============================================================================")
    logger.info(f"   PIPELINE END-TO-END FINALIZADO CON ÉXITO TOTAL EN {total_duration}s   ")
    logger.info("============================================================================")
    return True


if __name__ == "__main__":
    success = execute_pipeline()
    sys.exit(0 if success else 1)
