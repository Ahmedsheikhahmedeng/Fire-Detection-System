import argparse
import json

from app.core.database import SessionLocal
from app.services.cluster_backfill_service import recalculate_fire_clusters


def main() -> None:
    parser = argparse.ArgumentParser(description="Recalculate fire_clusters from linked hotspots.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without writing changes.")
    args = parser.parse_args()

    with SessionLocal() as db:
        report = recalculate_fire_clusters(db, dry_run=args.dry_run)

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
