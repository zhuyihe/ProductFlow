# Secret Storage

Project rule. Every backend change that handles secrets (API tokens, shared
secrets, encryption keys) must comply.

## What This Covers

- New API per-user tokens stored in `auth_sessions`, `workflow_runs`,
  `image_session_generation_tasks`.
- The new-api SSO shared secret stored in admin runtime settings.
- The token master key sourced from `PRODUCTFLOW_TOKEN_KEY`.
- Any future secret that hits Atelier's database or logs.

## Token-at-Rest Encryption

All `new_api_token` columns hold AES-GCM ciphertext, base64-encoded. The
canonical helpers live in `infrastructure/crypto/token_cipher.py`:

```python
def encrypt_token(plaintext: str) -> str: ...
def decrypt_token(blob: str) -> str: ...
def mask_token(t: str | None) -> str: ...
```

Rules:

- Every write to a `new_api_token` column must call `encrypt_token` first.
- Every read that yields a usable token must call `decrypt_token` at the
  application-layer boundary (typically `load_principal` or one of the
  `provider_execution_context_from_*` helpers).
- A tampered ciphertext must raise on decrypt; never recover with a fallback
  value or with a request that proceeds anyway.

## Master Key Lifecycle

`PRODUCTFLOW_TOKEN_KEY` is a base64-encoded 32-byte key, supplied via the
process environment.

- Production: required. The container must refuse to start without it
  (`config.py` validator). Source of the key in production is the deployment
  secret store (Docker secret, systemd credential, or KMS-managed env
  injection).
- Development: same env variable; developers may generate a personal key with
  `openssl rand -base64 32` and store it in their personal `.env`.

Never:

- Hardcode a default key for development convenience.
- Log the key, even at debug level.
- Commit the key to source control.

The key is held in module state (`_KEY` in `token_cipher.py`). Rotation
requires either re-encrypting all stored tokens or accepting that all
sessions/tasks created under the old key become unreadable on next access.
Rotation procedure is intentionally out of scope for the initial deploy; see
Wave 3 work for KMS-backed rotation.

## Shared Secrets

The new-api SSO shared secret (`new_api_sso_shared_secret`) is stored in
Atelier's `app_settings` table, not in environment. The bootstrap secrets
(`SESSION_SECRET`, `PRODUCTFLOW_TOKEN_KEY`, `SETTINGS_ACCESS_TOKEN`) stay in
env because they are needed before the database can be read.

Comparison rules:

- Comparing a user-supplied secret to a stored secret must use
  `secrets.compare_digest`. Plain `==` introduces a timing side channel.
- Failure responses must not contain a hint about which character matched
  (this is a corollary of constant-time comparison).

## Log Masking

Anywhere a token or shared secret might surface in a log, JSON response, or
exception message, route it through `mask_token` first or omit the field
entirely.

- Logs must never contain `sk-` prefixed material in plaintext.
- API response payloads must never include the raw `new_api_token` field; the
  client only needs the session cookie.
- Dataclasses or Pydantic schemas that wrap principal or token data must not
  expose the raw token in `__repr__`; use `field(repr=False)` or an explicit
  masked representation for any token-bearing field.

## Cookie Hygiene

The session cookie that carries the opaque session id:

- `HttpOnly=True`, `SameSite=Lax`, `Secure=True` in production.
- `Secure` is enforced by the production-mode validator
  (`SESSION_COOKIE_SECURE=true` required when `APP_ENV=production`).
- The cookie must remain opaque - no encoded principal data, no token data, no
  user id. Anything sensitive lives server-side in `auth_sessions`.

## Reverse Proxy Trust

`uvicorn` runs with `--proxy-headers --forwarded-allow-ips='*'` in production
so that `X-Forwarded-Proto: https` is honored. Without it `request.url.scheme`
is `http`, the framework thinks the request is plain HTTP, and the `Secure`
cookie attribute is silently dropped at write time, causing logged-in users to
lose their session on the next request.

The reverse proxy (Caddy on `image.aync.cc.cd`) must forward at least:

- `X-Forwarded-Proto: https`
- `X-Forwarded-For: <client_ip>`
- `Host: image.aync.cc.cd`

## New API Relay Credential Use

Interactive provider calls use the current SSO principal's New API token as the relay credential. This applies to both
ordinary users and Atelier admins. Admin status grants Atelier authorization, moderation, and settings access; it
must not bypass New API token billing, token model limits, quota, or usage attribution.

Rules:

- `ProviderExecutionContext` may carry `new_api_user_id`, token metadata, and the decrypted `new_api_token`; the token
  field must stay `repr=False` and must never be returned through API responses.
- Atelier provider profiles supply fallback model names and provider-specific settings. For interactive SSO image
  generation, the API key and base URL must be overridden with `new_api_token` and the configured New API relay URL; when
  the SSO session carries a New API-selected image model, that model is the effective image model.
- Durable `workflow_runs` and `image_session_generation_tasks` store the token snapshot chosen at submit time so retries
  keep the original billing identity.
- A CLI/bootstrap admin session has no New API token. It may be used to recover settings, but it must not silently fall
  back to Atelier shared provider credentials for user-initiated generation.
- A missing token in an interactive relay path is an expected safe failure, not permission to use a shared provider key.

## Reviewing New Code

A change that touches secrets is in scope. Ask:

1. Does any new database column hold a secret? If yes, is the write path
   wrapped in `encrypt_token`?
2. Does any new function return or log a token field? If yes, is `mask_token`
   applied?
3. Does any new comparison check a user-supplied secret? If yes, is it
   `secrets.compare_digest`?
4. Does any new environment variable hold a secret? If yes, is it required by
   the production-mode validator?
5. Does an interactive provider call have an SSO principal? If yes, does it use
   that principal's New API token rather than Atelier's shared provider key?
6. For SSO image generation, does the effective image model come from the SSO
   session claim when present rather than a stale local provider binding?

## Anti-Patterns (Do Not Reintroduce)

```python
# WRONG: plaintext token in DB
auth_session.new_api_token = claims.token

# WRONG: timing side channel
if payload.admin_key != settings.admin_access_key:
    raise HTTPException(401)

# WRONG: token leaking into a log line
logger.info("loaded session for user=%s token=%s", uid, principal.new_api_token)

# WRONG: admin status bypasses the relay billing identity
if principal.is_admin:
    return None

# WRONG: HTTPS-only cookie without trusting the proxy header
# (uvicorn launched without --proxy-headers -> Secure cookie never sticks)
```
