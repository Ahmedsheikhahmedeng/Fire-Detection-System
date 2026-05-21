import argparse
import json

from app.core.database import SessionLocal
from app.services.cluster_backfill_service import backfill_fire_clusters


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill fire_clusters for existing hotspots.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Simulate without writing changes.")
    mode.add_argument("--all", action="store_true", help="Process all unclustered hotspots.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum hotspot count to process.")
    args = parser.parse_args()

    if not args.dry_run and not args.all and args.limit is None:
        parser.error("Use --dry-run, --limit N, or --all.")

    with SessionLocal() as db:
        report = backfill_fire_clusters(
            db,
            dry_run=args.dry_run,
            limit=None if args.all else args.limit,
        )

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
