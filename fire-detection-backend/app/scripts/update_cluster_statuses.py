import argparse
import json

from app.core.database import SessionLocal
from app.services.cluster_status_service import update_cluster_statuses


def main() -> None:
    parser = argparse.ArgumentParser(description="Update fire_cluster status values from last_seen_at.")
    parser.add_argument("--dry-run", action="store_true", help="Calculate statuses without persisting changes.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        report = update_cluster_statuses(db, commit=not args.dry_run)
        if args.dry_run:
            db.rollback()
            report["dry_run"] = True
        else:
            report["dry_run"] = False
        print(json.dumps(report, indent=2, ensure_ascii=False))
    finally:
        db.close()


if __name__ == "__main__":
    main()
