from __future__ import annotations

import argparse
import getpass
import sys

from sqlmodel import Session

from app.auth import get_user_by_email, sync_admin_account_state
from app.database import engine
from app.utils.security import ADMIN_PASSWORD_POLICY_MESSAGE, get_password_hash, password_meets_admin_policy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reset a local RouteWeather account password directly in the development database."
    )
    parser.add_argument("--email", required=True, help="The account email to update.")
    parser.add_argument(
        "--password",
        help="The new password to set. If omitted, you will be prompted securely.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    email = args.email.strip().lower()
    password = args.password or getpass.getpass("New password: ")
    confirm_password = getpass.getpass("Confirm new password: ")

    if password != confirm_password:
        print("Passwords do not match.", file=sys.stderr)
        return 1

    with Session(engine) as session:
        user = get_user_by_email(session, email)
        if not user:
            print(f"No account found for {email}.", file=sys.stderr)
            return 1

        user = sync_admin_account_state(session, user)
        if user.is_admin and not password_meets_admin_policy(password):
            print(ADMIN_PASSWORD_POLICY_MESSAGE, file=sys.stderr)
            return 1

        user.password_hash = get_password_hash(password)
        user.admin_password_compliant = password_meets_admin_policy(password)
        user.must_change_password = False
        session.add(user)
        session.commit()

    print(f"Password updated successfully for {email}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
