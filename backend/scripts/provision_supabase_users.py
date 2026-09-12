"""Create the demo accounts in Supabase Auth and link them to businesses.

The seed creates rows in app_users, but those are just business mappings - no
Supabase account exists behind them. This script creates one Supabase Auth user
per seeded email and writes the resulting auth ID back to app_users, so
AUTH_MODE=supabase can resolve a verified token to a business.

    DB_TARGET=supabase python scripts/provision_supabase_users.py
    DB_TARGET=supabase python scripts/provision_supabase_users.py --verify

Idempotent: an account that already exists is looked up and relinked rather
than recreated, so it is safe to re-run after a reseed.

--verify additionally signs in as one demo account and checks that the backend
accepts the resulting access token, which is the end-to-end proof that JWT
verification works against this project.

The secret key used here is an admin credential. It is read from .env, never
logged, and never sent anywhere except your own Supabase project.
"""

from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import models  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402

# A single shared password across the demo accounts. These are throwaway
# accounts in a throwaway project holding synthetic business data; the point is
# that teammates can all log in during the demo without a password manager.
DEFAULT_PASSWORD = "BitNBuild-demo-2026!"


def admin_headers(secret_key: str) -> dict[str, str]:
    return {
        "apikey": secret_key,
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }


def find_user_by_email(client: httpx.Client, base: str, headers: dict, email: str):
    """The admin list endpoint, paged, filtered client-side on email."""
    page = 1
    while page <= 20:
        response = client.get(
            f"{base}/auth/v1/admin/users",
            headers=headers,
            params={"page": page, "per_page": 200},
        )
        response.raise_for_status()
        payload = response.json()
        users = payload.get("users", payload if isinstance(payload, list) else [])
        if not users:
            return None
        for user in users:
            if (user.get("email") or "").lower() == email.lower():
                return user
        page += 1
    return None


def create_or_fetch(
    client: httpx.Client, base: str, headers: dict, email: str, password: str
) -> tuple[dict, str]:
    response = client.post(
        f"{base}/auth/v1/admin/users",
        headers=headers,
        json={
            "email": email,
            "password": password,
            # No mail is sent for these accounts, so confirm them outright;
            # otherwise sign-in would be blocked pending confirmation.
            "email_confirm": True,
        },
    )
    if response.status_code in (200, 201):
        return response.json(), "created"

    body = response.text.lower()
    if response.status_code in (400, 409, 422) and (
        "already" in body or "exists" in body or "registered" in body
    ):
        existing = find_user_by_email(client, base, headers, email)
        if existing is None:
            raise RuntimeError(f"{email} reported as existing but could not be found.")
        # Reset the password so a re-run leaves every account usable with the
        # password this script prints.
        client.put(
            f"{base}/auth/v1/admin/users/{existing['id']}",
            headers=headers,
            json={"password": password, "email_confirm": True},
        ).raise_for_status()
        return existing, "existing"

    raise RuntimeError(f"{email}: {response.status_code} {response.text[:200]}")


def provision(password: str) -> int:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_secret_key:
        print("SUPABASE_URL and SUPABASE_SECRET_KEY must be set in backend/.env.")
        return 1

    base = settings.supabase_url.rstrip("/")
    headers = admin_headers(settings.supabase_secret_key)

    db = SessionLocal()
    try:
        users = list(db.scalars(select(models.AppUser).order_by(models.AppUser.email)))
        if not users:
            print("No app_users rows. Run the seed first.")
            return 1

        print(f"Provisioning {len(users)} demo account(s) in {base}\n")
        with httpx.Client(timeout=30) as client:
            for user in users:
                auth_user, how = create_or_fetch(
                    client, base, headers, user.email, password
                )
                user.supabase_user_id = auth_user["id"]
                business = db.get(models.Business, user.business_id)
                print(
                    f"  {how:<9} {user.email:<34} -> {business.name[:34] if business else '?'}"
                )
        db.commit()

        print("\nAll accounts share this password:")
        print(f"    {password}")
        print(
            "\nSwitch AUTH_MODE=supabase in backend/.env to use real logins.\n"
            "Give B the publishable key plus any of these emails."
        )
        return 0
    finally:
        db.close()


def verify(password: str) -> int:
    """Sign in for real, then check the backend accepts the token."""
    settings = get_settings()
    base = settings.supabase_url.rstrip("/")

    db = SessionLocal()
    try:
        user = db.scalar(
            select(models.AppUser)
            .where(models.AppUser.email.like("buyer1@%"))
            .limit(1)
        ) or db.scalar(select(models.AppUser).limit(1))
        if user is None:
            print("No app_users rows to verify with.")
            return 1
        email = user.email
        expected_business_id = user.business_id
    finally:
        db.close()

    print(f"Signing in as {email} ...")
    with httpx.Client(timeout=30) as client:
        response = client.post(
            f"{base}/auth/v1/token",
            params={"grant_type": "password"},
            headers={
                "apikey": settings.supabase_secret_key,
                "Content-Type": "application/json",
            },
            json={"email": email, "password": password},
        )
        if response.status_code != 200:
            print(f"  sign-in FAILED: {response.status_code} {response.text[:200]}")
            return 1

        token = response.json()["access_token"]
        print(f"  got an access token ({len(token)} chars)")

    # Decode the header only, to report which algorithm the project signs with.
    import jwt

    header = jwt.get_unverified_header(token)
    print(f"  token algorithm: {header.get('alg')} (kid={header.get('kid', '-')})")
    if str(header.get("alg", "")).startswith(("RS", "ES")):
        print("  -> asymmetric signing key; the backend verifies via JWKS.")
    else:
        print("  -> legacy HS256; SUPABASE_JWT_SECRET must be set in .env.")

    # Now verify through the real code path.
    from app.auth.tokens import verify_token

    supabase_settings = settings.model_copy(update={"auth_mode": "supabase"})
    try:
        claims = verify_token(token, supabase_settings)
    except Exception as exc:  # noqa: BLE001
        print(f"  backend verification FAILED: {type(exc).__name__}: {exc}")
        return 1

    print(f"  backend verified the token. subject={claims.subject[:12]}...")

    db = SessionLocal()
    try:
        resolved = db.scalar(
            select(models.AppUser).where(models.AppUser.supabase_user_id == claims.subject)
        )
        if resolved is None:
            print("  but no app_users row matches that subject - run provisioning.")
            return 1
        ok = resolved.business_id == expected_business_id
        print(f"  resolved to the expected business: {ok}")
        return 0 if ok else 1
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(prog="provision_supabase_users")
    parser.add_argument(
        "--password",
        default=DEFAULT_PASSWORD,
        help="password to set on every demo account",
    )
    parser.add_argument(
        "--random-password",
        action="store_true",
        help="generate one instead of using the shared default",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="also sign in and check the backend accepts the token",
    )
    args = parser.parse_args()

    password = (
        f"BnB-{secrets.token_urlsafe(12)}!" if args.random_password else args.password
    )

    code = provision(password)
    if code or not args.verify:
        return code
    print()
    return verify(password)


if __name__ == "__main__":
    raise SystemExit(main())
