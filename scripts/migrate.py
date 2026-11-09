#!/usr/bin/env python3
"""Lightweight, atomic raw SQL database migration runner for PostgreSQL.

Features:
- Idempotent execution of ordered SQL scripts in `migrations/`.
- Atomic transaction per migration: rolls back cleanly if any script fails.
- Tracking table `schema_migrations` storing executed versions and SHA-256 checksums.
- Detection of modified/tampered migration files.
"""

import asyncio 
import hashlib
import os
import sys
from pathlib import Path
import asyncpg

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
DEFAULT_DB_URL = "postgresql://postgres:postgres@localhost:5432/expense_tracker"
 

def get_db_url() -> str:
    """Retrieve database URL and format for asyncpg."""
    url = os.getenv("DATABASE_URL", DEFAULT_DB_URL)
    # asyncpg expects postgresql:// or postgres:// without +driver
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "")
    elif "+psycopg" in url:
        url = url.replace("+psycopg", "")
    return url


def calculate_checksum(content: str) -> str:
    """Compute SHA-256 hash of migration file content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def init_tracking_table(conn: asyncpg.Connection) -> None:
    """Ensure schema_migrations table exists."""
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(255) PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            checksum VARCHAR(64) NOT NULL
        );
        """
    )


async def get_applied_migrations(conn: asyncpg.Connection) -> dict[str, str]:
    """Return dictionary of version -> checksum for applied migrations."""
    rows = await conn.fetch("SELECT version, checksum FROM schema_migrations ORDER BY version")
    return {r["version"]: r["checksum"] for r in rows}


async def show_status(conn: asyncpg.Connection) -> None:
    """Display status of all migration files."""
    await init_tracking_table(conn)
    applied = await get_applied_migrations(conn)
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    print("\n--- Migration Status ---")
    print(f"{'Version':<45} | {'Status':<12} | Checksum Match")
    print("-" * 75)

    for file_path in migration_files:
        version = file_path.name
        content = file_path.read_text(encoding="utf-8")
        current_checksum = calculate_checksum(content)

        if version in applied:
            match = "OK" if applied[version] == current_checksum else "MODIFIED!"
            print(f"{version:<45} | APPLIED      | {match}")
        else:
            print(f"{version:<45} | PENDING      | -")
    print("-" * 75 + "\n")


async def apply_migrations(conn: asyncpg.Connection) -> None:
    """Execute pending migrations in sorted order."""
    await init_tracking_table(conn)
    applied = await get_applied_migrations(conn)
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    pending_count = 0

    for file_path in migration_files:
        version = file_path.name
        content = file_path.read_text(encoding="utf-8")
        current_checksum = calculate_checksum(content)

        if version in applied:
            # Verify integrity
            if applied[version] != current_checksum:
                print(
                    f"WARNING: Previously applied migration '{version}' has been modified locally!\n"
                    f"  Applied SHA: {applied[version][:12]}...\n"
                    f"  Current SHA: {current_checksum[:12]}..."
                )
            continue

        print(f"Applying migration: {version} ...", end=" ", flush=True)

        # Atomic execution in transaction
        async with conn.transaction():
            await conn.execute(content)
            await conn.execute(
                "INSERT INTO schema_migrations (version, checksum) VALUES ($1, $2)",
                version,
                current_checksum,
            )

        print("[OK]")
        pending_count += 1

    if pending_count == 0:
        print("Database schema is up to date. No pending migrations.")
    else:
        print(f"Successfully applied {pending_count} migration(s).")


async def main() -> None:
    db_url = get_db_url()
    try:
        conn = await asyncpg.connect(db_url)
    except Exception as exc:
        print(f"Failed to connect to PostgreSQL at {db_url}: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        if len(sys.argv) > 1 and sys.argv[1].lower() == "status":
            await show_status(conn)
        else:
            await apply_migrations(conn)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
