#!/usr/bin/env python3
"""Write the merged catalogs as JSON snapshots next to each base catalog.

    services/.venv/bin/python db/export.py

Produces services/<svc>/data/catalog.merged.json. Services read Postgres when
HEXASTRA_DATABASE_URL is set; otherwise this snapshot (tests, Pages, offline);
otherwise the base catalog. Only the orchestrator runs this when integrating.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from build import BASES, MERGED_NAME, build  # noqa: E402


def main() -> int:
    merged, report = build()
    for svc, cat in merged.items():
        path = BASES[svc].with_name(MERGED_NAME)
        path.write_text(json.dumps(cat, ensure_ascii=False, indent=2), encoding="utf-8")
        print("wrote", path.relative_to(HERE.parent))
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
