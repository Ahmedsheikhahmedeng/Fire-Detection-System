#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import sys


sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.core.json_loader import normalized_json_sha256_payload  # noqa: E402


DEFAULT_MODEL_DIR = Path("app/ml/final_models_v3")
MANIFEST_FILE_NAME = "model_artifacts_manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate required V3 model artifact files, sizes, and SHA-256 checksums."
    )
    parser.add_argument(
        "--model-dir",
        default=str(DEFAULT_MODEL_DIR),
        help="Directory containing the V3 model package.",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help="Manifest JSON file with expected artifact metadata.",
    )
    parser.add_argument(
        "--skip-checksum",
        action="store_true",
        help="Only check file presence and sizes.",
    )
    args = parser.parse_args()

    model_dir = Path(args.model_dir)
    manifest_path = Path(args.manifest) if args.manifest else model_dir / MANIFEST_FILE_NAME

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = []

    print(f"Model dir: {model_dir.resolve()}")
    print(f"Manifest:  {manifest_path.resolve()}")

    for item in manifest["files"]:
        path = model_dir / item["path"]
        if not path.exists():
            failures.append(f"MISS {item['path']}")
            print(f"MISS - {item['path']}")
            continue

        if item.get("allow_json_comments"):
            actual_sha = hashlib.sha256(normalized_json_sha256_payload(path)).hexdigest()
            if actual_sha != item["normalized_sha256"]:
                failures.append(f"NORMALIZED_SHA256 {item['path']}: expected {item['normalized_sha256']}, got {actual_sha}")
                print(f"HASH - {item['path']}")
                continue

            print(f"OK   - {item['path']}")
            continue

        size = path.stat().st_size
        if size != item["size_bytes"]:
            failures.append(f"SIZE {item['path']}: expected {item['size_bytes']}, got {size}")
            print(f"SIZE - {item['path']} expected={item['size_bytes']} got={size}")
            continue

        if not args.skip_checksum:
            actual_sha = sha256_file(path)
            if actual_sha != item["sha256"]:
                failures.append(f"SHA256 {item['path']}: expected {item['sha256']}, got {actual_sha}")
                print(f"HASH - {item['path']}")
                continue

        print(f"OK   - {item['path']}")

    if failures:
        print("\nModel artifact check FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nModel artifact check PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
