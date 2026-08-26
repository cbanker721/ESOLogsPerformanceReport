# ESOLogsPerformanceReport Application Knowledge Base

## Purpose
This repository contains a lightweight, downloadable ESO Logs client and a generated GraphQL schema knowledge base for agent use.

## What the application does
- Provides a static browser sandbox for entering and running GraphQL queries.
- Uses `sandbox/index.html` and `sandbox/app.js` for the runtime UI and request flow.
- Loads local config from `config.local.js` at the repository root.
- Supports either a cached `accessToken` or local `clientId` + `clientSecret` to acquire one on demand.
- Sends GraphQL requests to `https://www.esologs.com/api/v2/client`.
- Defaults the query textbox to an introspection query so the user can inspect the API immediately.

## Runtime flow
1. Load `config.local.js` in the browser.
2. Read config from `window.ESOLOGS_LOCAL_CONFIG`.
3. If an access token exists, use it directly.
4. Otherwise, mint a token from `clientId` + `clientSecret` and cache it in memory for the session.
5. Submit the GraphQL query and render the response in the page.

## Refresh flow
- `scripts/refresh_graphql_kb.py` is the authoritative refresh path.
- The script reads `config.local.js`.
- If `accessToken` is present, it uses that directly.
- If not, it uses `clientId` + `clientSecret` to mint a token and writes the token back to `config.local.js`.
- The script refreshes the generated GraphQL schema artifacts in `knowledge-base/graphql/`.

## Important files
- `config.local.js`: Local auth/config used by the app and refresh script.
- `config.example.js`: Template version of the local config.
- `sandbox/index.html`: Minimal browser UI for GraphQL queries.
- `sandbox/app.js`: Browser-side query execution and token handling.
- `scripts/refresh_graphql_kb.py`: Python refresh script for schema docs.
- `knowledge-base/graphql/README.md`: Human-readable schema summary.
- `knowledge-base/graphql/introspection-full.json`: Full introspection response.
- `knowledge-base/graphql/root-schema-summary.json`: Root query/directives summary.
- `knowledge-base/graphql/core-types-summary.json`: Focused snapshots of core types.

## Editing guidance for agents
- Keep the user-facing runtime simple and static.
- Prefer small focused edits.
- Update both `sandbox/app.js` and `scripts/refresh_graphql_kb.py` when changing auth behavior.
- Regenerate schema artifacts instead of hand-editing generated GraphQL files.

## Relation to the GraphQL knowledge base
- `knowledge-base/graphql/` is generated from live schema introspection.
- `knowledge-base/README.md` describes the application itself, not the API schema.
