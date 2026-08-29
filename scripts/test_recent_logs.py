from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

DEFAULT_API_URL = "https://www.esologs.com/api/v2/client"
DEFAULT_OAUTH_URL = "https://www.esologs.com/oauth/token"
PLACEHOLDER_TOKENS = {"REPLACE_WITH_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN"}
PLACEHOLDER_CLIENTS = {
    "REPLACE_WITH_CLIENT_ID",
    "YOUR_CLIENT_ID",
    "REPLACE_WITH_CLIENT_SECRET",
    "YOUR_CLIENT_SECRET",
}

USER_ID = 34336
LIMIT = 50

RECENT_LOGS_QUERY = """
query RecentLogs($userID: Int!, $limit: Int!, $page: Int!) {
  reportData {
    reports(userID: $userID, limit: $limit, page: $page) {
      total
      current_page
      per_page
      has_more_pages
      data {
        code
        title
        startTime
        endTime
      }
    }
  }
}
""".strip()


def get_config_value(config_text: str, key: str) -> str:
    pattern = rf"{re.escape(key)}\s*:\s*\"([^\"]+)\""
    match = re.search(pattern, config_text)
    return match.group(1) if match else ""


def oauth_token(oauth_url: str, client_id: str, client_secret: str) -> dict[str, Any]:
    payload = (
        f"grant_type=client_credentials&client_id={quote_plus(client_id)}&client_secret={quote_plus(client_secret)}"
    ).encode("utf-8")
    req = Request(
        oauth_url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from OAuth endpoint: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error calling OAuth endpoint: {exc}") from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from OAuth endpoint: {body[:500]}") from exc

    if not parsed.get("access_token"):
        raise RuntimeError(f"OAuth response did not include access_token: {json.dumps(parsed, indent=2)}")

    return parsed


def graphql_post(api_url: str, authorization: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = Request(
        api_url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": authorization,
        },
    )

    try:
        with urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from GraphQL endpoint: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error calling GraphQL endpoint: {exc}") from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from GraphQL endpoint: {body[:500]}") from exc

    if parsed.get("errors"):
        raise RuntimeError(f"GraphQL errors returned: {json.dumps(parsed['errors'], indent=2)}")

    return parsed


def resolve_auth_from_config(config_text: str) -> tuple[str, str]:
    client_id = get_config_value(config_text, "clientId")
    client_secret = get_config_value(config_text, "clientSecret")
    access_token = get_config_value(config_text, "accessToken")
    oauth_url = get_config_value(config_text, "oauthUrl") or DEFAULT_OAUTH_URL
    token_type = get_config_value(config_text, "tokenType") or "Bearer"

    has_access_token = bool(access_token) and access_token not in PLACEHOLDER_TOKENS
    has_client_credentials = (
        bool(client_id)
        and bool(client_secret)
        and client_id not in PLACEHOLDER_CLIENTS
        and client_secret not in PLACEHOLDER_CLIENTS
    )

    if has_access_token:
        return token_type, access_token

    if not has_client_credentials:
        raise RuntimeError("config.local.js must contain either accessToken or both clientId and clientSecret.")

    oauth_result = oauth_token(oauth_url, client_id, client_secret)
    return oauth_result.get("token_type") or token_type, oauth_result["access_token"]


def format_timestamp(ms: Any) -> str:
    if not isinstance(ms, (int, float)):
        return "-"

    dt = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).astimezone()
    return dt.strftime("%Y-%m-%d %H:%M")


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    config_path = repo_root / "config.local.js"

    if not config_path.exists():
        print(f"Missing config file: {config_path}", file=sys.stderr)
        return 1

    config_text = config_path.read_text(encoding="utf-8")
    api_url = get_config_value(config_text, "apiUrl") or DEFAULT_API_URL

    try:
        token_type, access_token = resolve_auth_from_config(config_text)
    except RuntimeError as exc:
        print(f"Auth error: {exc}", file=sys.stderr)
        return 1

    variables = {"userID": USER_ID, "limit": LIMIT, "page": 1}

    try:
        result = graphql_post(api_url, f"{token_type} {access_token}", RECENT_LOGS_QUERY, variables)
    except RuntimeError as exc:
        print(f"Query failed: {exc}", file=sys.stderr)
        return 1

    reports_block = ((result.get("data") or {}).get("reportData") or {}).get("reports") or {}
    reports = reports_block.get("data") or []

    reports_sorted = sorted(
        reports,
        key=lambda r: (r.get("startTime") or 0),
        reverse=True,
    )

    print(f"Recent logs for user {USER_ID} (requested {LIMIT}, returned {len(reports_sorted)})")
    print("=" * 96)
    print(f"{'Start':16} {'End':16} {'Code':18} Title")
    print("-" * 96)

    for report in reports_sorted:
        start_s = format_timestamp(report.get("startTime"))
        end_s = format_timestamp(report.get("endTime"))
        code = (report.get("code") or "-")[:18]
        title = report.get("title") or "-"
        print(f"{start_s:16} {end_s:16} {code:18} {title}")

    total = reports_block.get("total")
    current_page = reports_block.get("current_page")
    per_page = reports_block.get("per_page")
    has_more = reports_block.get("has_more_pages")
    print("-" * 96)
    print(f"total={total} page={current_page} per_page={per_page} has_more_pages={has_more}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
