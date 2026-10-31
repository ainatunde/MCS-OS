"""Explicit schema migration and scoped identity provisioning; never logs secrets."""
import argparse
import json
import os

from services.control.security import DEPARTMENTS
from services.control.store import Identity, configured_store, token_hash


def provision(store):
    operators = json.loads(os.environ.get("MCS_OPERATOR_ROLES", "{}"))
    with store.transaction() as s:
        for username, role in operators.items():
            if role not in DEPARTMENTS:
                raise RuntimeError("Unknown operator role")
            key = "operator:" + ("Administrator" if username.lower() == "administrator" else username.lower())
            row = s.get(Identity, key)
            if row is None:
                row = Identity(identity_id=key, role=role, kind="operator", scopes={})
                s.add(row)
            row.role, row.enabled = role, True
        token, secret = os.environ.get("MCS_PULZZ_SERVICE_TOKEN", ""), os.environ.get("MCS_PULZZ_SIGNING_SECRET", "")
        if len(token) < 32 or len(secret) < 32:
            raise RuntimeError("Pulzz service credentials must be at least 32 characters")
        row = s.get(Identity, "service:tv-insights")
        if row is None:
            row = Identity(identity_id="service:tv-insights", role="producer", kind="service", scopes={})
            s.add(row)
        row.enabled, row.token_hash = True, token_hash(token)
        row.scopes = {"producer": "tv-insights", "product_slug": "tv-insights", "read_health": True}
        row.secret_env, row.secret_hash = "MCS_PULZZ_SIGNING_SECRET", token_hash(secret)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["migrate", "provision"])
    args = parser.parse_args()
    store = configured_store()
    if args.operation == "migrate":
        store.migrate()
    else:
        provision(store)
    print(args.operation + " complete (no credentials logged)")
