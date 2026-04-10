from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2 import OperationalError
from psycopg2.extras import RealDictCursor

from app.config import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)
from app.logger import logger


class DatabaseConnectionError(Exception):
    """Raised when the application cannot connect to PostgreSQL."""


class DatabaseQueryError(Exception):
    """Raised when a SQL query fails."""


def get_connection():
    try:
        return psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            connect_timeout=5,
        )
    except OperationalError as exc:
        logger.exception("Database connection failed")
        raise DatabaseConnectionError("Unable to connect to the PostgreSQL database.") from exc
    except Exception as exc:
        logger.exception("Unexpected database connection error")
        raise DatabaseConnectionError("Unexpected database connection failure.") from exc

def run_query(sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    params = params or ()
    conn = None

    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    except DatabaseConnectionError:
        raise
    except Exception as exc:
        logger.exception("Database query failed")
        raise DatabaseQueryError("Database query execution failed.") from exc
    finally:
        if conn is not None:
            conn.close()