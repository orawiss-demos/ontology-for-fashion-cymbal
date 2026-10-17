# DISCLAIMER — DEMONSTRATION CODE, NOT FOR PRODUCTION USE
#
# This project is a demonstration example, provided solely to illustrate
# concepts and for learning purposes. It is not an official Google product
# and is not supported by Google.
#
# The code is provided "as is", without warranty of any kind, express or
# implied. It has not been hardened, security-reviewed, or tested for
# production workloads, and it must not be relied upon to run production
# systems or to process business-critical data.
#
# The author accepts no responsibility or liability for any failure, defect,
# data loss, cost, or other damage arising from the use, adaptation, or
# deployment of this example in any environment, including customer
# environments. Anyone reusing any part of it does so at their own risk and
# should review, test, and adapt it thoroughly first.

"""
bq_execute — run a SQL query against BigQuery and return results.

Safety:
  - Only SELECT queries allowed (no DDL/DML)
  - Maximum 100 rows returned (truncated with warning)
  - Timeout: 30 seconds
"""

from google.cloud import bigquery
from config import GCP_PROJECT, BQ_DATASET

client = bigquery.Client(project=GCP_PROJECT)

MAX_ROWS = 100
TIMEOUT_SECONDS = 30


def bq_execute(sql: str) -> dict:
    """Execute a read-only SQL query against BigQuery.

    Args:
        sql: SELECT query to execute. DDL/DML is rejected.

    Returns:
        Dict with keys: columns (list of names), rows (list of dicts),
        total_rows, truncated (bool), sql (the query that ran).
    """
    # Safety: reject non-SELECT statements
    stripped = sql.strip().upper()
    if not stripped.startswith("SELECT") and not stripped.startswith("WITH"):
        return {
            "error": "Only SELECT queries are allowed. Got: " + stripped[:50],
            "sql": sql,
        }

    try:
        job_config = bigquery.QueryJobConfig(
            maximum_bytes_billed=1_000_000_000,  # 1 GB limit
        )
        query_job = client.query(sql, job_config=job_config, timeout=TIMEOUT_SECONDS)
        results = query_job.result(timeout=TIMEOUT_SECONDS)

        # Convert to list of dicts
        columns = [field.name for field in results.schema]
        rows = []
        for i, row in enumerate(results):
            if i >= MAX_ROWS:
                break
            rows.append({col: _serialize(row[col]) for col in columns})

        total_rows = results.total_rows or len(rows)
        truncated = total_rows > MAX_ROWS

        return {
            "columns": columns,
            "rows": rows,
            "total_rows": total_rows,
            "truncated": truncated,
            "sql": sql,
        }

    except Exception as e:
        return {
            "error": str(e),
            "sql": sql,
        }


def _serialize(value):
    """Make BQ values JSON-serializable."""
    import datetime
    import decimal
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
