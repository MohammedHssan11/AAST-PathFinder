import argparse
import json
import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.application.services.ingestion_service import IngestionService
from app.config.settings import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI College Decision System - Management CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Ingest Command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest a fully normalized JSON file into the database.")
    ingest_parser.add_argument("file", type=str, help="Path to the JSON file to ingest (e.g. data.json)")
    ingest_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run a pre-flight schema check but do NOT save to the database",
    )

    args = parser.parse_args()

    if args.command == "ingest":
        target_path = Path(args.file)
        if not target_path.exists():
            logger.error(f"File not found: {args.file}")
            return

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON file: {e}")
            return

        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        with SessionLocal() as db:
            service = IngestionService(db)

            if args.dry_run:
                logger.info(f"Running DRY RUN on {target_path.name}...")
                report = service.pre_flight_check(raw_data)
                print("\n" + report.summary() + "\n")
                if report.validation_errors:
                    logger.error("Dry run failed due to schema validation errors.")
                else:
                    logger.info("Dry run succeeded. Ready for DB ingestion.")
            else:
                try:
                    service.process_and_save(raw_data)
                    logger.info("Data committed to the database.")
                except Exception as e:
                    logger.error(f"Ingestion failed: {e}")
                    db.rollback()


if __name__ == "__main__":
    main()
