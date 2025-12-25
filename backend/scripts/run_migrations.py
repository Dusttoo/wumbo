#!/usr/bin/env python3
"""Run database migrations using Alembic

This script is designed to be run in ECS tasks or CI/CD pipelines
to automatically apply database migrations.

Usage:
    python scripts/run_migrations.py [--check-only]

Options:
    --check-only    Check if migrations are pending without applying them
    --downgrade N   Downgrade N migrations (use with caution!)

Environment Variables:
    DATABASE_URL    PostgreSQL connection string (required)
"""

import argparse
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.core.logging import logger


def wait_for_database(max_retries: int = 30, retry_interval: int = 2) -> bool:
    """
    Wait for database to be available

    Args:
        max_retries: Maximum number of connection attempts
        retry_interval: Seconds between retries

    Returns:
        True if database is available, False otherwise
    """
    logger.info("Waiting for database to be available...")

    engine = create_engine(str(settings.DATABASE_URL))

    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✓ Database is available")
            return True
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"Failed to connect to database after {max_retries} attempts: {e}")
                return False
            logger.warning(f"Database not ready (attempt {attempt}/{max_retries}), retrying in {retry_interval}s...")
            time.sleep(retry_interval)

    return False


def get_alembic_config() -> Config:
    """Get Alembic configuration"""
    # Get path to alembic.ini
    backend_dir = Path(__file__).parent.parent
    alembic_ini = backend_dir / "alembic.ini"

    if not alembic_ini.exists():
        raise FileNotFoundError(f"alembic.ini not found at {alembic_ini}")

    config = Config(str(alembic_ini))

    # Override sqlalchemy.url with DATABASE_URL from environment
    config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))

    return config


def get_current_revision() -> str:
    """Get current database revision"""
    engine = create_engine(str(settings.DATABASE_URL))

    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current_rev = context.get_current_revision()

    return current_rev or "None"


def get_head_revision(config: Config) -> str:
    """Get latest migration revision"""
    script = ScriptDirectory.from_config(config)
    head = script.get_current_head()
    return head or "None"


def check_pending_migrations(config: Config) -> bool:
    """
    Check if there are pending migrations

    Returns:
        True if migrations are pending, False otherwise
    """
    current = get_current_revision()
    head = get_head_revision(config)

    logger.info(f"Current database revision: {current}")
    logger.info(f"Latest migration revision: {head}")

    if current == head:
        logger.info("✓ Database is up to date")
        return False
    else:
        logger.warning("⚠ Pending migrations detected")
        return True


def run_migrations(config: Config, check_only: bool = False) -> int:
    """
    Run database migrations

    Args:
        config: Alembic configuration
        check_only: If True, only check for pending migrations

    Returns:
        0 if successful, non-zero error code otherwise
    """
    try:
        # Check if migrations are pending
        has_pending = check_pending_migrations(config)

        if check_only:
            # Exit with code 1 if migrations are pending (for CI checks)
            return 1 if has_pending else 0

        if not has_pending:
            logger.info("No migrations to apply")
            return 0

        # Apply migrations
        logger.info("=" * 80)
        logger.info("APPLYING DATABASE MIGRATIONS")
        logger.info("=" * 80)

        command.upgrade(config, "head")

        logger.info("=" * 80)
        logger.info("✓ Migrations applied successfully")
        logger.info("=" * 80)

        # Verify migrations were applied
        current = get_current_revision()
        head = get_head_revision(config)

        if current == head:
            logger.info(f"✓ Database is now at revision: {current}")
            return 0
        else:
            logger.error(f"✗ Migration verification failed: current={current}, expected={head}")
            return 1

    except Exception as e:
        logger.error(f"✗ Migration failed: {e}", exc_info=True)
        return 1


def downgrade_migrations(config: Config, steps: int = 1) -> int:
    """
    Downgrade database migrations

    Args:
        config: Alembic configuration
        steps: Number of migrations to downgrade

    Returns:
        0 if successful, non-zero error code otherwise
    """
    try:
        logger.warning("=" * 80)
        logger.warning("⚠ DOWNGRADING DATABASE MIGRATIONS")
        logger.warning(f"⚠ This will roll back {steps} migration(s)")
        logger.warning("=" * 80)

        # Downgrade
        if steps == 1:
            command.downgrade(config, "-1")
        else:
            command.downgrade(config, f"-{steps}")

        logger.info("=" * 80)
        logger.info(f"✓ Downgraded {steps} migration(s)")
        logger.info("=" * 80)

        return 0

    except Exception as e:
        logger.error(f"✗ Downgrade failed: {e}", exc_info=True)
        return 1


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Check if migrations are pending without applying them"
    )
    parser.add_argument(
        "--downgrade",
        type=int,
        metavar="N",
        help="Downgrade N migrations (use with caution!)"
    )
    parser.add_argument(
        "--skip-wait",
        action="store_true",
        help="Skip waiting for database (use if DB is already available)"
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("DATABASE MIGRATION RUNNER")
    logger.info("=" * 80)
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Database: {settings.DATABASE_URL.host}:{settings.DATABASE_URL.port}/{settings.DATABASE_URL.path}")
    logger.info("=" * 80)

    # Wait for database
    if not args.skip_wait:
        if not wait_for_database():
            logger.error("✗ Database is not available")
            sys.exit(1)

    # Get Alembic config
    config = get_alembic_config()

    # Run migrations
    if args.downgrade:
        exit_code = downgrade_migrations(config, args.downgrade)
    else:
        exit_code = run_migrations(config, check_only=args.check_only)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
