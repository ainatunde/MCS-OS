# Console security release

This patch does not enable corporate integration workers, adapters or database migrations.

The console signs individual users in through the existing ERPNext identity provider. Its opaque session cookie is HttpOnly, Secure in production, SameSite=Lax and scoped to the API host. Every protected user request validates that session against ERPNext again; caller role headers and body fields cannot grant authority. Logout invalidates the ERP session.

Set `MCS_ROLE_BINDINGS` to a JSON mapping of ERP usernames to existing executive roles. The account must be enabled in ERPNext and present in that server-controlled map. Missing configuration denies sign-in. `MCS_CORS_ORIGINS` must contain the exact console origin; browser mutations reject other origins.

The existing shared control token permits reads only. It cannot propose actions, approve, change directives or control halts. Existing in-memory execution and display scaffolding remains outside this release; it is not integration acceptance.

Credential values and password-copy controls were removed from the console and team response. Previously exposed passwords and keys were separately rotated; removing source values does not revoke credentials. Bootstrap/seeding code must obtain secrets explicitly.

Verification: the Python regression suite includes forged actor/header requests, cross-department actions/approvals, rejected and modified payloads, revoked identities, CSRF origins and API credential exposure. Build the console with the committed lockfile, audit its dependencies and inspect public assets after deployment. Verify real login, role-bound rejection and logout on production without releasing any business action.
