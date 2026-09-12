"""HTTP surface: auth, error envelope, CRUD, ownership, pagination."""

from __future__ import annotations

from datetime import timedelta

from tests.conftest import auth

BASE = "/api/v1"


def _window(now, start_days, end_days):
    return {
        "start": (now + timedelta(days=start_days)).isoformat(),
        "end": (now + timedelta(days=end_days)).isoformat(),
    }


def test_health_needs_no_token_and_exposes_nothing_else(client):
    response = client.get(f"{BASE}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_every_other_route_requires_a_token(client, scenario):
    for path in ("/me", "/reference", "/listings", "/me/listings", "/me/deals"):
        response = client.get(f"{BASE}{path}")
        assert response.status_code == 401, path
        assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_malformed_and_unknown_tokens_are_rejected(client, scenario):
    for header in (
        {"Authorization": "Basic abc"},
        {"Authorization": "Bearer"},
        {"Authorization": "Bearer not-a-dev-token"},
        {"Authorization": "Bearer dev:nobody@nowhere.local"},
    ):
        assert client.get(f"{BASE}/me", headers=header).status_code == 401


def test_me_returns_the_callers_own_business(client, scenario):
    body = client.get(f"{BASE}/me", headers=auth(scenario.buyer_email)).json()
    assert body["business"]["id"] == scenario.buyer.id
    assert body["business"]["roles"] == ["buyer"]
    assert body["business"]["receiving_processes"] == ["brick_kiln_fuel"]
    assert body["business"]["location"]["precision"] == "district"


def test_reference_lists_materials_districts_and_processes(client, scenario):
    body = client.get(f"{BASE}/reference", headers=auth(scenario.buyer_email)).json()
    assert {"id": "rice_husk", "name": "Rice Husk"} in body["materials"]
    assert any(d["name"] == "MYSURU" for d in body["districts"])
    kiln = next(p for p in body["receiving_processes"] if p["id"] == "brick_kiln_fuel")
    assert "rice_husk" in kiln["material_ids"]


def test_create_listing_takes_its_owner_from_the_token_not_the_body(client, scenario):
    response = client.post(
        f"{BASE}/listings",
        json={
            "material_id": "rice_husk",
            "available_quantity_kg": 30_000,
            "asking_price_paise_per_tonne": 280_000,
            "seller_floor_paise_per_tonne": 250_000,
            "moisture_pct": 9.0,
            "contamination_notes": "",
            "pickup_window": _window(scenario.now, 2, 12),
            # A hostile client trying to create a listing for someone else:
            "seller_business_id": scenario.sellers[1].id,
        },
        headers=auth(scenario.seller_emails[0]),
    )
    assert response.status_code == 201
    assert response.json()["seller"]["id"] == scenario.sellers[0].id
    assert response.json()["status"] == "open"


def test_listing_validation_rejects_a_floor_above_the_asking_price(client, scenario):
    response = client.post(
        f"{BASE}/listings",
        json={
            "material_id": "rice_husk",
            "available_quantity_kg": 30_000,
            "asking_price_paise_per_tonne": 200_000,
            "seller_floor_paise_per_tonne": 250_000,
            "moisture_pct": 9.0,
            "pickup_window": _window(scenario.now, 2, 12),
        },
        headers=auth(scenario.seller_emails[0]),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_INPUT"


def test_listing_validation_rejects_a_backwards_window_and_zero_quantity(client, scenario):
    base = {
        "material_id": "rice_husk",
        "available_quantity_kg": 30_000,
        "asking_price_paise_per_tonne": 280_000,
        "seller_floor_paise_per_tonne": 250_000,
        "moisture_pct": 9.0,
        "pickup_window": _window(scenario.now, 12, 2),
    }
    assert (
        client.post(f"{BASE}/listings", json=base, headers=auth(scenario.seller_emails[0])).status_code
        == 422
    )

    base["pickup_window"] = _window(scenario.now, 2, 12)
    base["available_quantity_kg"] = 0
    assert (
        client.post(f"{BASE}/listings", json=base, headers=auth(scenario.seller_emails[0])).status_code
        == 422
    )


def test_unknown_material_is_rejected(client, scenario):
    response = client.post(
        f"{BASE}/listings",
        json={
            "material_id": "unobtainium",
            "available_quantity_kg": 1_000,
            "asking_price_paise_per_tonne": 100,
            "seller_floor_paise_per_tonne": 100,
            "moisture_pct": 1.0,
            "pickup_window": _window(scenario.now, 2, 12),
        },
        headers=auth(scenario.seller_emails[0]),
    )
    assert response.status_code == 422


def test_only_the_seller_can_patch_a_listing(client, scenario):
    listing_id = scenario.listings[0].id
    forbidden = client.patch(
        f"{BASE}/listings/{listing_id}",
        json={"status": "closed"},
        headers=auth(scenario.seller_emails[1]),
    )
    assert forbidden.status_code == 403

    allowed = client.patch(
        f"{BASE}/listings/{listing_id}",
        json={"status": "closed", "asking_price_paise_per_tonne": 299_000},
        headers=auth(scenario.seller_emails[0]),
    )
    assert allowed.status_code == 200
    assert allowed.json()["status"] == "closed"
    assert allowed.json()["asking_price_paise_per_tonne"] == 299_000


def test_closed_listings_are_hidden_from_the_public_list(client, scenario):
    client.patch(
        f"{BASE}/listings/{scenario.listings[0].id}",
        json={"status": "closed"},
        headers=auth(scenario.seller_emails[0]),
    )
    body = client.get(f"{BASE}/listings", headers=auth(scenario.buyer_email)).json()
    assert scenario.listings[0].id not in {item["id"] for item in body["items"]}


def test_listing_filters_and_pagination(client, scenario):
    filtered = client.get(
        f"{BASE}/listings?material_id=rice_husk&district=DAVANGERE",
        headers=auth(scenario.buyer_email),
    ).json()
    assert len(filtered["items"]) == 3

    assert (
        client.get(f"{BASE}/listings?district=KODAGU", headers=auth(scenario.buyer_email)).json()[
            "items"
        ]
        == []
    )

    first = client.get(f"{BASE}/listings?limit=2", headers=auth(scenario.buyer_email)).json()
    assert len(first["items"]) == 2
    assert first["next_cursor"]

    second = client.get(
        f"{BASE}/listings?limit=2&cursor={first['next_cursor']}",
        headers=auth(scenario.buyer_email),
    ).json()
    assert len(second["items"]) == 1
    assert second["next_cursor"] is None
    ids = {item["id"] for item in first["items"]} | {item["id"] for item in second["items"]}
    assert len(ids) == 3, "pagination repeated or dropped a row"


def test_bad_limit_and_cursor_are_rejected(client, scenario):
    assert client.get(f"{BASE}/listings?limit=0", headers=auth(scenario.buyer_email)).status_code == 422
    assert client.get(f"{BASE}/listings?limit=500", headers=auth(scenario.buyer_email)).status_code == 422
    assert (
        client.get(f"{BASE}/listings?cursor=!!!", headers=auth(scenario.buyer_email)).status_code
        == 422
    )


def test_create_requirement_requires_a_confirmed_receiving_process(client, scenario):
    payload = {
        "material_id": "rice_husk",
        "receiving_process_id": "timber_drying_boiler_fuel",
        "quantity_kg": 20_000,
        "max_moisture_pct": 15,
        "delivery_window": _window(scenario.now, 4, 16),
        "buyer_max_total_paise": 7_000_000,
    }
    response = client.post(
        f"{BASE}/requirements", json=payload, headers=auth(scenario.buyer_email)
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PROCESS_UNCONFIRMED"

    payload["receiving_process_id"] = "brick_kiln_fuel"
    created = client.post(
        f"{BASE}/requirements", json=payload, headers=auth(scenario.buyer_email)
    )
    assert created.status_code == 201
    assert created.json()["buyer"]["id"] == scenario.buyer.id
    assert created.json()["buyer_max_total_paise"] == 7_000_000
    # Location defaults to the business's own location when omitted.
    assert created.json()["location"]["district"] == scenario.buyer.district


def test_transport_options_can_only_be_entered_by_the_pair(client, scenario):
    payload = {
        "listing_id": scenario.listings[0].id,
        "requirement_id": scenario.requirement.id,
        "label": "Third-party flatbed",
        "freight_paise": 1_400_000,
        "capacity_kg": 25_000,
        "pickup_at": (scenario.now + timedelta(days=4)).isoformat(),
        "delivery_at": (scenario.now + timedelta(days=6)).isoformat(),
        "expires_at": (scenario.now + timedelta(days=7)).isoformat(),
        "source": "entered_quote",
        "distance_m": 180_000,
        "distance_basis": "district_straight_line",
    }

    # The seller of this listing may.
    assert (
        client.post(
            f"{BASE}/transport-options", json=payload, headers=auth(scenario.seller_emails[0])
        ).status_code
        == 201
    )
    # The buyer of this requirement may.
    assert (
        client.post(
            f"{BASE}/transport-options", json=payload, headers=auth(scenario.buyer_email)
        ).status_code
        == 201
    )
    # An unrelated seller may not.
    assert (
        client.post(
            f"{BASE}/transport-options", json=payload, headers=auth(scenario.seller_emails[1])
        ).status_code
        == 403
    )


def test_transport_option_schedule_must_be_ordered(client, scenario):
    response = client.post(
        f"{BASE}/transport-options",
        json={
            "listing_id": scenario.listings[0].id,
            "requirement_id": scenario.requirement.id,
            "label": "Backwards",
            "freight_paise": 1_000,
            "capacity_kg": 25_000,
            "pickup_at": (scenario.now + timedelta(days=6)).isoformat(),
            "delivery_at": (scenario.now + timedelta(days=4)).isoformat(),
            "expires_at": (scenario.now + timedelta(days=7)).isoformat(),
            "source": "entered_quote",
        },
        headers=auth(scenario.buyer_email),
    )
    assert response.status_code == 422


def test_unknown_ids_return_404(client, scenario):
    headers = auth(scenario.buyer_email)
    assert client.get(f"{BASE}/listings/nope", headers=headers).status_code == 404
    assert client.get(f"{BASE}/requirements/nope", headers=headers).status_code == 404
    assert client.get(f"{BASE}/negotiations/nope", headers=headers).status_code == 404
    assert client.get(f"{BASE}/deals/nope", headers=headers).status_code == 404


def test_every_error_uses_the_same_envelope(client, scenario):
    for response in (
        client.get(f"{BASE}/me"),
        client.get(f"{BASE}/listings/nope", headers=auth(scenario.buyer_email)),
        client.get(
            f"{BASE}/requirements/{scenario.requirement.id}",
            headers=auth(scenario.seller_emails[0]),
        ),
        client.post(f"{BASE}/listings", json={}, headers=auth(scenario.seller_emails[0])),
    ):
        body = response.json()
        assert set(body) == {"error"}
        assert set(body["error"]) == {"code", "message", "details"}
        assert isinstance(body["error"]["code"], str)


def test_openapi_document_builds(client):
    schema = client.get("/openapi.json").json()
    assert f"{BASE}/requirements/{{requirement_id}}/matches" in schema["paths"]
    assert "OwnerListing" in schema["components"]["schemas"]
    # The public Listing schema must not even declare a floor field.
    assert "seller_floor_paise_per_tonne" not in schema["components"]["schemas"]["Listing"][
        "properties"
    ]
