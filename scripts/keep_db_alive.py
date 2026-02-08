#!/usr/bin/env python3
"""
Keep database alive by performing a lightweight query.

This script makes a simple database query to prevent Supabase
from pausing the project due to inactivity.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from sqlalchemy import create_engine, text


def ping_database(database_url: str) -> bool:
    """Perform a lightweight database query.

    Args:
        database_url: PostgreSQL connection string

    Returns:
        True if successful, False otherwise
    """
    try:
        # Create engine with short timeout
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 10},
        )

        # Simple query that doesn't require any tables
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as keepalive"))
            row = result.fetchone()

            if row and row[0] == 1:
                print(f"✓ Database ping successful at {datetime.now(timezone.utc).isoformat()}")
                return True
            else:
                print(f"✗ Unexpected result: {row}")
                return False

    except Exception as e:
        print(f"✗ Database ping failed: {e}")
        return False
    finally:
        engine.dispose()


def main() -> int:
    """Main entry point."""
    database_url = os.getenv("DS_DATABASE_URL")

    if not database_url:
        print("Error: DS_DATABASE_URL environment variable not set")
        return 1

    # Mask password in output
    safe_url = database_url.split("@")[1] if "@" in database_url else "unknown"
    print(f"Pinging database at {safe_url}...")

    success = ping_database(database_url)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
