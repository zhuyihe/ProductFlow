# New API SSO Deployment

This deployment path runs ProductFlow as the New API image workspace on a server.

## Images

The GHCR workflow publishes:

- `ghcr.io/zhuyihe/productflow-backend:new-api-sso`
- `ghcr.io/zhuyihe/productflow-web:new-api-sso`
- `ghcr.io/zhuyihe/productflow-backend:new-api-sso-<short-sha>`
- `ghcr.io/zhuyihe/productflow-web:new-api-sso-<short-sha>`

Use the short-sha tags when you want a pinned rollout. Use `new-api-sso` for the latest pushed branch build.

## ProductFlow Server Env

Copy `.env.example` to `.env` beside `docker-compose.prod.yml`, then set at least:

```env
BACKEND_CORS_ORIGINS=https://image.example.com
SESSION_COOKIE_SECURE=true

NEW_API_BASE_URL=https://api.example.com
NEW_API_RELAY_BASE_URL=https://api.example.com/v1
NEW_API_SSO_START_URL=https://api.example.com/api/productflow/sso/start
NEW_API_SSO_VERIFY_PATH=/api/productflow/sso/verify
NEW_API_SSO_SHARED_SECRET=replace-with-the-same-secret-used-by-new-api
```

`NEW_API_SSO_SHARED_SECRET` must match the New API `PRODUCTFLOW_SSO_SECRET`.

## New API Env

Set the matching values in the New API deployment:

```env
PRODUCTFLOW_BASE_URL=https://image.example.com
PRODUCTFLOW_SSO_SECRET=replace-with-the-same-secret-used-by-productflow
```

The New API sidebar entry should open ProductFlow in a new browser tab.

## Start ProductFlow

```bash
docker login ghcr.io -u <github-user>
mkdir -p /opt/productflow
cd /opt/productflow
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
curl -fsS http://127.0.0.1:29281/healthz
curl -fsS http://127.0.0.1:29281/api/healthz
```

If the GHCR packages are private, use a GitHub classic PAT or fine-grained token with package read access for `docker login`.

## Caddy

Host-level Caddy can proxy to the loopback web port:

```caddyfile
image.example.com {
    reverse_proxy 127.0.0.1:29281
}
```

Keep public ports `80` and `443` on Caddy. ProductFlow binds only `127.0.0.1:29281` by default.
