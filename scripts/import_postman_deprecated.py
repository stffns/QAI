#!/usr/bin/env python
"""CLI: Import a Postman collection into the QA Intelligence database.

Usage:
  python scripts/import_postman.py --collection path/to/collection.json \
      [--environment path/to/env.json] [--mapping-id 12] [--no-raw]

Returns JSON summary to stdout.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlmodel import create_engine, Session

from config.settings import get_settings
# DEPRECATED - PostmanImporter replaced by PostmanEndpointImporter
# from src.importers.postman_importer import PostmanImporter
from src.importers.postman_endpoint_importer import PostmanEndpointImporter


def parse_args():
    p = argparse.ArgumentParser(description="Import Postman collection")
    p.add_argument("--collection", required=True, help="Path to collection JSON")
    p.add_argument("--environment", help="Optional environment JSON")
    p.add_argument("--mapping-id", type=int, help="Optional mapping id for linkage")
    p.add_argument("--no-raw", action="store_true", help="Do not store raw collection JSON")
    return p.parse_args()


def main():
    args = parse_args()
    settings = get_settings()
    db_url = settings.database.url
    if not db_url:
        raise SystemExit("Database URL is not configured (settings.database.url is None)")
    engine = create_engine(db_url)
    with Session(engine) as session:
        importer = PostmanImporter(session)
        result = importer.import_collection(
            Path(args.collection),
            environment_path=Path(args.environment) if args.environment else None,
            mapping_id=args.mapping_id,
            store_raw=not args.no_raw,
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
