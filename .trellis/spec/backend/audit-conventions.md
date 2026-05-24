# Audit Conventions

Project rule. Every backend change that touches user data or administrative
actions must comply.

## Why

Administrators can access user-owned business data for support and risk review.
Every such access must be auditable. Session revocation and destructive
moderation actions must remain attributable so support actions do not become
silent data loss.

## What Must Be Audited

1. **Admin user-content access.** Any time a principal whose `kind == "admin"`
   reads or mutates a row that has an `owner_user_id` belonging to a real
   end-user.
2. **Admin gallery moderation.** Public gallery reads are not audited, but
   admin destructive/moderation actions on another user's gallery content are.
3. **Admin session revocation.** Revoke/demote operations that immediately
   remove access are audited like other cross-user destructive actions.
4. **Future: tenant-scoping mutations.** When admins re-attribute resources
   (move products to a different owner), that mutation is auditable per (1).

What is **not** audited:

- Normal user actions on their own data. Use business event logs for those.
- Admin `GET /api/gallery` and `GET /api/gallery/{id}` reads. Gallery rows are
  public to authenticated users once shared.
- Admin deleting their own gallery entry. Treat it like a normal owner action.
- Health checks and unauthenticated requests.
- Password-admin login is gone; there is no HTTP login attempt to audit.

## The Audit Helpers

`application/audit_logs.py` exposes:

```python
def record_admin_user_content_access(
    session, *, principal, target_user_id, action,
    resource_type, resource_id, request_context,
) -> None:
    ...
```

That helper:

- Commits independently of the surrounding business transaction so a business
  rollback does not erase the audit trail.
- Truncates over-long fields to fit column widths.
- Uses the authenticated principal's `new_api_user_id` when present and
  falls back to `emergency-admin` only for CLI/bootstrap-style admin actors
  that do not have a user id.

## Action Naming

Stable, lowercase, underscore-separated. The contract: `<verb>_<noun>` or
`admin_<event>`. Examples:

- `read_product`, `update_product`, `delete_product`
- `read_image_session`, `retry_image_generation_task`
- `delete_gallery_entry`, `resolve_gallery_report`, `revoke_auth_session`

Do not embed dynamic data in the action string (no `delete_product_42`); put
the id in `resource_id`.

## Outcome Field

`audit_logs.outcome` was added so admin access can be recorded at multiple
moments:

- `intent` (default): "admin reached the route". Acceptable for read paths.
- `success`: business action completed and committed.
- `denied`: authorization rejected the action after the audit context was
  established (rare; usually 403 is raised earlier).
- `error`: business action raised after intent was recorded.
- `legacy_access` (reserved): admin touched a record whose owner predates the
  tenant rollout. Not used at `image.aync.cc.cd` because the deploy was fresh.

For read-only paths, recording `intent` at the entry point is enough. For
mutating paths, prefer recording the final `outcome` so audit reflects
actual behavior. The Wave 2 `audit_action` context manager wraps this:

```python
with audit_action(session, principal, action="update_product",
                  resource_type="product", resource_id=pid,
                  request_context=ctx) as audit:
    do_business_logic()
    audit.mark_success(details={"changed_fields": [...]})
```

## Where Calls Live

- Routes layer (`presentation/routes/*.py`) initiates audit calls.
- Application layer does not call audit directly; it raises or returns; the
  route decides whether the outcome warrants `success`/`error`.
- Background workers do not write admin audit; their actions belong to the
  user who enqueued the task.

## Reviewing New Code

When reviewing a route change:

1. Is the route admin-accessible? If yes, does it call
   `record_admin_user_content_access` (or `audit_action`) for the path that
   touches user data?
2. Is the action name stable and verb_noun shaped?
3. Is `target_user_id` correctly populated from the resource's owner, not the
   admin's id?
4. Are `client_address` and `user_agent` passed via `AuditRequestContext`?

Gallery-specific review rule:

- Do not audit admin `GET` reads of public gallery content.
- Do audit admin deleting another user's gallery entry, resolving/dismissing a
  report, or revoking a session for immediate demotion.
- Do not audit an admin deleting a gallery entry they authored themselves.

## Anti-Patterns (Do Not Reintroduce)

```python
# WRONG: admin action with no audit
@router.delete("/admin/products/{pid}")
def admin_delete_product(pid, principal=Depends(require_admin_audit_principal)):
    delete_product(pid)
    return Ok()

# WRONG: audit recorded after business commit, so a crash between them loses the
# audit trail entirely
def admin_route(...):
    result = do_business()
    session.commit()
    record_admin_user_content_access(...)   # may never run

# WRONG: action string embedding dynamic data
action="delete_product_" + pid

# WRONG: admin action audit attributing to the wrong user
record_admin_user_content_access(..., target_user_id=principal.new_api_user_id, ...)
# target_user_id is the resource owner, not the admin
```

## Retention

Audit rows are not truncated by the application; deletion is an operations
decision. Plan to add a retention job once table size exceeds operational
comfort (currently no concern at fresh deploy).
