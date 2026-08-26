# Copilot Instructions for ESOLogsPerformanceReport

## Purpose
This repository contains a lightweight, downloadable ESO Logs GraphQL client and a schema knowledge base for agent use. The main runtime is a static browser UI; the development and refresh tooling is local and script-based.

## What the app does
- Loads local credentials from `config.local.js`.
- Runs GraphQL queries against `https://www.esologs.com/api/v2/client`.
- Defaults the sandbox query input to an introspection query.
- Can acquire an OAuth access token from local client credentials when needed, then reuse/cache that token locally.

## Important files
- `sandbox/index.html`: Minimal browser UI for entering and running GraphQL queries.
- `sandbox/app.js`: Browser-side logic for loading config, acquiring tokens when needed, and executing GraphQL requests.
- `config.local.js`: Local-only credentials/config. May contain `clientId`, `clientSecret`, `accessToken`, `apiUrl`, `oauthUrl`, and `tokenType`.
- `config.example.js`: Template version of the local config.
- `scripts/refresh_graphql_kb.py`: Primary refresh script for rebuilding the knowledge base. Uses `config.local.js` and will mint a token from client credentials if a valid `accessToken` is not already present.
- `knowledge-base/graphql/`: Generated schema documentation and raw introspection artifacts.

## Current auth model
- `accessToken` is the preferred runtime value when present.
- If `accessToken` is missing or placeholder text, the refresh script can use `clientId` + `clientSecret` to mint a new token.
- When the refresh script mints a token, it writes the updated token back into `config.local.js`.
- `.apikeys` exists only as legacy credential storage and is not used by the current runtime flow.

## Knowledge base contents
The `knowledge-base/` folder contains the application-level summary and the generated GraphQL schema knowledge base.

The `knowledge-base/README.md` file contains:
- A description of what the application does.
- The runtime flow.
- The refresh flow.
- The key files to edit.

The `knowledge-base/graphql/` folder contains:
- `README.md`: Human-readable schema summary.
- `introspection-full.json`: Full schema introspection response.
- `root-schema-summary.json`: Root query/directives summary.
- `core-types-summary.json`: Focused snapshots of the main top-level domain types.

## Editing rules
- Keep the browser client simple and static.
- Preserve the current config contract in `config.local.js` unless the change explicitly updates the auth model.
- Do not remove or overwrite local secrets unless the user explicitly asks.
- Prefer small, focused edits over broad refactors.
- If changing auth or refresh behavior, update both `sandbox/app.js` and `scripts/refresh_graphql_kb.py` together.
- If the schema knowledge base changes, refresh the generated files under `knowledge-base/graphql/` instead of editing them by hand.

## Operational notes
- The browser client may encounter CORS or connectivity issues when calling the ESO Logs endpoint directly.
- The Python refresh script is the authoritative way to rebuild the knowledge base in this repo.
- Use UTF-8 text output and keep generated documentation deterministic where practical.
