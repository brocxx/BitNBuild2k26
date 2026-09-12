"""End-to-end walkthrough against a running server.

    python -m app.data.cli reset
    uvicorn app.main:app --port 8000
    python scripts/smoke.py

Runs the demo path a judge would see: matches, negotiation, agreement, stock
reservation, delivery status - then the low-budget no-deal case.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/api/v1"
BUYER_EMAIL = "buyer1@demo.bitnbuild.local"
DEMO_PASSWORD = "BitNBuild-demo-2026!"


def rupees(paise: int) -> str:
    return f"INR {paise / 100:,.2f}"


def buyer_token() -> str:
    """A dev token, or a real Supabase access token when AUTH_MODE=supabase."""
    settings = get_settings()
    if settings.auth_mode != "supabase":
        return f"dev:{BUYER_EMAIL}"

    base = settings.supabase_url.rstrip("/")
    response = httpx.post(
        f"{base}/auth/v1/token",
        params={"grant_type": "password"},
        headers={"apikey": settings.supabase_secret_key},
        json={"email": BUYER_EMAIL, "password": DEMO_PASSWORD},
        timeout=30,
    )
    response.raise_for_status()
    print(f"Signed in to Supabase as {BUYER_EMAIL}")
    return response.json()["access_token"]


def main() -> int:
    settings = get_settings()
    print(
        f"auth_mode={settings.auth_mode}  agent_mode={settings.agent_mode}  "
        f"db_target={settings.db_target}"
    )
    client = httpx.Client(
        base_url=BASE, headers={"Authorization": f"Bearer {buyer_token()}"}, timeout=120
    )

    assert client.get("/health").json() == {"status": "ok"}
    me = client.get("/me").json()
    print(f"Buyer: {me['business']['name']} ({me['business']['location']['district']})")

    requirements = client.get("/me/requirements").json()["items"]
    feasible = max(requirements, key=lambda r: r["buyer_max_total_paise"])
    infeasible = min(requirements, key=lambda r: r["buyer_max_total_paise"])

    for label, requirement in (("AGREEMENT", feasible), ("NO DEAL", infeasible)):
        print(f"\n=== {label} case ===")
        print(
            f"Requirement {requirement['quantity_kg']} kg {requirement['material_id']} "
            f"into {requirement['receiving_process_id']}, "
            f"budget {rupees(requirement['buyer_max_total_paise'])}"
        )

        matches = client.get(f"/requirements/{requirement['id']}/matches").json()
        for candidate in matches["candidates"]:
            listing = candidate["listing"]
            print(
                f"  {listing['seller']['name'][:40]:<42} {listing['location']['district']:<14} "
                f"ask {rupees(listing['asking_price_paise_per_tonne'])}/t  "
                f"freight {rupees(candidate['initial_best_cost']['freight_paise'])}  "
                f"delivered {rupees(candidate['initial_best_cost']['buyer_total_paise'])}"
            )
        for excluded in matches["excluded"]:
            print(f"  excluded {excluded['listing_id'][:8]}: {', '.join(excluded['reason_codes'])}")

        listing_ids = [c["listing"]["id"] for c in matches["candidates"]][:3]
        started = client.post(
            "/negotiations",
            json={"requirement_id": requirement["id"], "listing_ids": listing_ids},
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )
        negotiation_id = started.json()["id"]

        negotiation = client.get(f"/negotiations/{negotiation_id}").json()
        while negotiation["status"] in ("queued", "running"):
            negotiation = client.get(f"/negotiations/{negotiation_id}").json()

        print(f"  status: {negotiation['status']}  failure: {negotiation['failure_code']}")
        for offer in negotiation["offers"]:
            print(
                f"    {offer['author']:<7}{offer['action']:<9}"
                f"{rupees(offer['unit_price_paise_per_tonne']):>16}/t  "
                f"delivered {rupees(offer['costs']['buyer_total_paise']):>16}  "
                f"{offer['explanation'][:58]}"
            )

        events = client.get(f"/negotiations/{negotiation_id}/events").json()
        print(f"  events: {len(events['items'])}, last_seq={events['last_seq']}")

        if not negotiation["deal_id"]:
            continue

        deal = client.get(f"/deals/{negotiation['deal_id']}").json()
        print(
            f"  DEAL {deal['id'][:8]}: {deal['quantity_kg']} kg from "
            f"{deal['seller']['name'][:36]} at "
            f"{rupees(deal['unit_price_paise_per_tonne'])}/t, "
            f"delivered {rupees(deal['costs']['buyer_total_paise'])} "
            f"(within budget {rupees(requirement['buyer_max_total_paise'])})"
        )
        print(f"  transport: {deal['transport_option']['label']} [{deal['transport_option']['source']}]")
        print(f"  intended use: {deal['intended_use'][:80]}")

        listing = client.get(f"/listings/{deal['listing_id']}").json()
        print(f"  remaining stock on that listing: {listing['available_quantity_kg']} kg")
        assert "seller_floor_paise_per_tonne" not in listing

        delivered = client.patch(f"/deals/{deal['id']}/status", json={"status": "delivered"})
        print(f"  skipping to delivered -> {delivered.status_code} "
              f"{delivered.json().get('error', {}).get('code', '')}")

    print("\nSmoke walkthrough complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
