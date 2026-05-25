# Multi-Tenant Isolation

Project rule. Every backend change that touches user data must comply.

## Why

Atelier runs as a public multi-tenant workspace at `image.aync.cc.cd`.
Users authenticate through new-api SSO; each user owns a disjoint slice of
business data (products, image sessions, canvas templates, and everything that
hangs off them). A single bypass anywhere collapses the tenant boundary for
the whole instance, and silent fall-through is more dangerous than an explicit
500.

## The Viewer Type

```python
@dataclass(frozen=True, slots=True)
class Viewer:
    kind: Literal["admin", "user"]
    user_id: str            # admin -> session id; user -> new_api_user_id (non-empty)
    principal: Principal    # for audit metadata
```

`Viewer` is the **only** acceptable owner-context parameter for
application-layer query and mutation helpers. Functions that previously took
`owner_user_id: str | None` must be migrated.

`build_viewer(principal)` raises `PrincipalIntegrityError` when:

- `principal.kind` is not in `{"admin", "user"}`, or
- `principal.kind == "user"` but `new_api_user_id` is empty or whitespace.

The global FastAPI exception handler converts `PrincipalIntegrityError` to
HTTP 500. **Never** convert it to 200 + empty data, and **never** demote it to
admin behavior.

## Query Predicate

The single sanctioned shape:

```python
if viewer.kind == "user":
    stmt = stmt.where(Model.owner_user_id == viewer.user_id)
# admin viewer: no owner filter (explicit, intentional)
```

Do not introduce other shapes (no `if owner_user_id is not None:`, no
`Optional[str]` parameter resurrecting the legacy contract).

## Child Resource Access

Direct lookup by child id is **never** safe in isolation. Resolve the parent
first under the viewer:

```python
def get_image_session_asset_or_raise(session, viewer, asset_id):
    parent = _get_image_session_or_raise(session, asset.session_id, viewer)
    # then return the asset
```

Even when the parent FK is `NOT NULL`, an attacker who can guess child ids
must not be able to read or mutate child data without passing the parent owner
check.

## List Endpoints With Parent Id Filters

`list_X(parent_id=...)` shapes must validate the parent's ownership before
filtering children:

```python
def list_image_sessions(viewer, product_id):
    _get_product_or_raise(viewer, product_id)   # 404 if cross-owner
    return _image_session_query(viewer).where(ImageSession.product_id == product_id).all()
```

Returning an empty list to a foreign-product request is an information leak
(confirms the product does not belong to the caller); raise 404 instead.

## Database-Level Tenant Guards

- Owner-bearing tables (`products`, `image_sessions`, `user_canvas_templates`)
  must carry `CHECK owner_user_id IS NOT NULL`. Application-layer enforcement is
  not sufficient; a future code path that forgets to populate the owner column
  must be caught at insert time.
- Unique constraints on user-namespaced columns must be composite with
  `owner_user_id`. Example: `UNIQUE (owner_user_id, key)` on
  `user_canvas_templates`, never plain `UNIQUE (key)`. Global uniqueness
  leaks cross-user existence through 409 responses.
- Hot list queries need `(owner_user_id, updated_at DESC)` composite indexes.
  Single-column owner indexes degrade to a sort on every list once the table
  is non-trivial.

## Reviewing New Code

When reviewing a change that touches an owner-bearing table or any table
reachable through one:

1. Does every new application-layer function accept `viewer: Viewer`?
2. Are child lookups gated by a parent fetch under the viewer?
3. If the change adds a unique constraint, is it composite with `owner_user_id`?
4. If the change adds an index, does it include `owner_user_id` as the first
   column when the workload is owner-scoped?
5. If the change introduces a query shape, does it use the sanctioned
   `if viewer.kind == "user": ... .where(...)` predicate?

A "no" anywhere is a blocking review comment.

## Gallery Scenario

Gallery list/detail endpoints expose already-shared public rows to every
authenticated SSO principal. `viewer.kind` does not add an owner filter for
these reads because the share action is the publication boundary.

Owner-sensitive gallery mutations still use `Viewer`:

- sharing a generated asset owned by an SSO user must verify
  `viewer.kind == "user"` and `viewer.user_id == image_session.owner_user_id`;
- current legacy/admin-created unowned rows may keep `shared_by_user_id ==
  NULL`, but new SSO user shares must store the SSO user id;
- admin moderation delete/report-resolution endpoints must check
  `viewer.kind == "admin"` explicitly and audit cross-user destructive
  actions;
- direct child-id lookups such as `image_session_asset_id` must resolve the
  asset's parent image session before accepting the mutation.

## Anti-Patterns (Do Not Reintroduce)

```python
# WRONG: legacy "None means admin" overload reappearing
def get_product(session, product_id, owner_user_id: str | None = None):
    if owner_user_id is not None:
        stmt = stmt.where(Product.owner_user_id == owner_user_id)
    ...

# WRONG: returning empty list for cross-owner access
def list_sessions(viewer, product_id):
    return _query(viewer).where(ImageSession.product_id == product_id).all()
    # leaks "this product is not mine"

# WRONG: silent owner-fallback
def principal_owner_user_id(principal):
    if principal is None or not principal.is_user:
        return None    # admin reads everything; bad data reads everything too
```
