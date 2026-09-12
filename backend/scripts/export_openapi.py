"""Write contracts/openapi.json from the live FastAPI schema.

Run this after any change to app/api/schemas.py or a route signature, then tell
B exactly what changed. B alone updates the frontend types, client and mocks.

    python scripts/export_openapi.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import REPO_ROOT  # noqa: E402
from app.main import app  # noqa: E402

OUTPUT = REPO_ROOT / "contracts" / "openapi.json"


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    schema = app.openapi()

    schemas = schema["components"]["schemas"]

    # A public response model must never declare a private field. Cheap to
    # check here, and it fails the export rather than shipping a leak.
    #
    # "Requirement" may legitimately be absent: no route returns the public
    # variant, because a requirement is only ever shown to its own buyer.
    forbidden = {
        "Listing": "seller_floor_paise_per_tonne",
        "Requirement": "buyer_max_total_paise",
    }
    for name, field in forbidden.items():
        properties = schemas.get(name, {}).get("properties", {})
        if field in properties:
            raise SystemExit(f"Public schema '{name}' leaks the private field '{field}'.")

    # ...and the owner variants must still carry them, or the owner's own UI
    # cannot show them their settings.
    required = {
        "OwnerListing": "seller_floor_paise_per_tonne",
        "OwnerRequirement": "buyer_max_total_paise",
    }
    for name, field in required.items():
        if field not in schemas.get(name, {}).get("properties", {}):
            raise SystemExit(f"Owner schema '{name}' is missing '{field}'.")

    OUTPUT.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(REPO_ROOT)} ({len(schema['paths'])} paths).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
