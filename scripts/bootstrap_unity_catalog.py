#!/usr/bin/env python3
"""Run the Unity Catalog bootstrap SQL before bundle deployment.

The Lakeflow Connect pipeline cannot be created until its destination catalog
and schemas already exist. In workspaces that use Databricks Default Storage,
creating a catalog through the catalog REST resource can require a storage
location, while `CREATE CATALOG IF NOT EXISTS` can use Default Storage from a
serverless SQL warehouse.

This script is intentionally simple and sequential for project readability:

1. Read Databricks authentication values from environment variables.
2. Read the SQL warehouse ID from the environment or `databricks.yml`.
3. Split the setup SQL file into individual statements.
4. Execute each statement through the SQL Statement Execution API.
5. Poll until each statement succeeds or fails.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SQL_FILE = PROJECT_ROOT / "setup" / "00_create_catalog_and_schemas.sql"
DEFAULT_BUNDLE_FILE = PROJECT_ROOT / "databricks.yml"


def read_required_env(name: str) -> str:
    """Return a required environment variable or stop with a useful message."""
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def read_sql_warehouse_id() -> str:
    """Read the SQL warehouse ID from env first, then from databricks.yml."""
    env_value = os.getenv("DATABRICKS_SQL_WAREHOUSE_ID", "").strip()
    if env_value:
        return env_value

    bundle_text = DEFAULT_BUNDLE_FILE.read_text(encoding="utf-8")
    match = re.search(
        r"sql_warehouse_id:\s*\n\s+description:.*\n\s+default:\s*([^\s#]+)",
        bundle_text,
    )
    if not match:
        raise SystemExit(
            "Could not find sql_warehouse_id.default in databricks.yml. "
            "Set DATABRICKS_SQL_WAREHOUSE_ID or update databricks.yml."
        )

    warehouse_id = match.group(1).strip()
    if warehouse_id.startswith("REPLACE_WITH_"):
        raise SystemExit(
            "sql_warehouse_id.default is still a placeholder. "
            "Set it to the SQL warehouse ID before deploying."
        )
    return warehouse_id


def split_sql_statements(sql_text: str) -> list[str]:
    """Split the simple setup SQL file into executable statements."""
    uncommented_lines = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--") or not stripped:
            continue
        uncommented_lines.append(line)

    statements = []
    for chunk in "\n".join(uncommented_lines).split(";"):
        statement = chunk.strip()
        if statement:
            statements.append(statement)
    return statements


def request_json(host: str, token: str, method: str, path: str, payload: dict | None = None) -> dict:
    """Send an authenticated Databricks REST request and return parsed JSON."""
    url = f"{host.rstrip('/')}{path}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url=url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Databricks API request failed: {exc.code} {error_body}") from exc

    return json.loads(response_body) if response_body else {}


def execute_statement(host: str, token: str, warehouse_id: str, statement: str) -> None:
    """Execute one SQL statement and wait for a terminal state."""
    print(f"Running SQL: {statement.splitlines()[0]}")
    response = request_json(
        host=host,
        token=token,
        method="POST",
        path="/api/2.0/sql/statements",
        payload={
            "warehouse_id": warehouse_id,
            "statement": statement,
            "wait_timeout": "30s",
            "on_wait_timeout": "CONTINUE",
        },
    )

    statement_id = response.get("statement_id")
    if not statement_id:
        raise SystemExit(f"Statement response did not include statement_id: {response}")

    while True:
        result = request_json(
            host=host,
            token=token,
            method="GET",
            path=f"/api/2.0/sql/statements/{statement_id}",
        )
        status = result.get("status", {})
        state = status.get("state")

        if state in {"SUCCEEDED", "CLOSED"}:
            print(f"Statement succeeded: {statement_id}")
            return

        if state in {"FAILED", "CANCELED"}:
            error = status.get("error", {})
            message = error.get("message", "No Databricks error message returned.")
            raise SystemExit(f"Statement {state.lower()}: {message}")

        time.sleep(2)


def main() -> None:
    """Run every bootstrap statement in order."""
    sql_file = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SQL_FILE
    host = read_required_env("DATABRICKS_HOST")
    token = read_required_env("DATABRICKS_TOKEN")
    warehouse_id = read_sql_warehouse_id()

    sql_text = sql_file.read_text(encoding="utf-8")
    statements = split_sql_statements(sql_text)
    if not statements:
        raise SystemExit(f"No SQL statements found in {sql_file}")

    print(f"Using SQL warehouse: {warehouse_id}")
    for statement in statements:
        execute_statement(host, token, warehouse_id, statement)

    print("Unity Catalog bootstrap completed.")


if __name__ == "__main__":
    main()
