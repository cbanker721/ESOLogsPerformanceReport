from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
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

FULL_QUERY = """
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    subscriptionType { name }
    types {
      kind
      name
      description
      fields(includeDeprecated: true) {
        name
        description
        args {
          name
          description
          defaultValue
          type {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
                ofType {
                  kind
                  name
                }
              }
            }
          }
        }
        type {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
              }
            }
          }
        }
        isDeprecated
        deprecationReason
      }
      inputFields {
        name
        description
        defaultValue
        type {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
              }
            }
          }
        }
      }
      interfaces {
        kind
        name
      }
      enumValues(includeDeprecated: true) {
        name
        description
        isDeprecated
        deprecationReason
      }
      possibleTypes {
        kind
        name
      }
    }
    directives {
      name
      description
      locations
      args {
        name
        description
        defaultValue
        type {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
            }
          }
        }
      }
    }
  }
}
""".strip()

ROOT_QUERY = (
    "{ __schema { queryType { name fields { name description args { name description "
    "defaultValue type { kind name ofType { kind name ofType { kind name } } } } type "
    "{ kind name ofType { kind name ofType { kind name } } } } } mutationType { name "
    "fields { name description } } subscriptionType { name } directives { name description "
    "locations } } }"
)

TYPE_QUERY = (
    '{ reportData: __type(name: "ReportData") { name description fields { name description args '
    '{ name description type { kind name ofType { kind name ofType { kind name } } } } type '
    '{ kind name ofType { kind name ofType { kind name } } } } } '
    'characterData: __type(name: "CharacterData") { name description fields { name description args '
    '{ name description type { kind name ofType { kind name ofType { kind name } } } } type '
    '{ kind name ofType { kind name ofType { kind name } } } } } '
    'guildData: __type(name: "GuildData") { name description fields { name description args '
    '{ name description type { kind name ofType { kind name ofType { kind name } } } } type '
    '{ kind name ofType { kind name ofType { kind name } } } } } '
    'worldData: __type(name: "WorldData") { name description fields { name description args '
    '{ name description type { kind name ofType { kind name ofType { kind name } } } } type '
    '{ kind name ofType { kind name ofType { kind name } } } } } '
    'rateLimitData: __type(name: "RateLimitData") { name description fields { name description args '
    '{ name description type { kind name ofType { kind name ofType { kind name } } } } type '
    '{ kind name ofType { kind name ofType { kind name } } } } } '
    'userData: __type(name: "UserData") { name description fields { name description args '
    '{ name description type { kind name ofType { kind name ofType { kind name } } } } type '
    '{ kind name ofType { kind name ofType { kind name } } } } } }'
)


def get_config_value(config_text: str, key: str) -> str:
    pattern = rf"{re.escape(key)}\s*:\s*\"([^\"]+)\""
    match = re.search(pattern, config_text)
    return match.group(1) if match else ""


def graphql_post(api_url: str, authorization: str, query: str) -> dict[str, Any]:
    payload = json.dumps({"query": query, "variables": {}}).encode("utf-8")
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

    if "errors" in parsed and parsed["errors"]:
        raise RuntimeError(f"GraphQL errors returned: {json.dumps(parsed['errors'], indent=2)}")

    return parsed


def oauth_token(oauth_url: str, client_id: str, client_secret: str) -> dict[str, Any]:
    payload = (
        f"grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}"
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


def write_config_value(config_text: str, key: str, value: str) -> str:
    pattern = rf"({re.escape(key)}\s*:\s*\")([^\"]*)(\")"
    replacement = rf"\g<1>{value}\g<3>"
    if re.search(pattern, config_text):
        return re.sub(pattern, replacement, config_text, count=1)
    return config_text


def normalize_description(text: str | None) -> str:
    if not text:
        return "No description available."
    return re.sub(r"\s+", " ", text).strip()


def format_type_section(type_info: dict[str, Any] | None) -> list[str]:
    if not type_info:
        return ["- Type not found."]

    lines: list[str] = []
    lines.append(f"- Description: {normalize_description(type_info.get('description'))}")
    lines.append("- Fields:")

    for field in type_info.get("fields", []):
        args = field.get("args") or []
        arg_names = ", ".join(a.get("name", "") for a in args if a.get("name")) or "none"
        field_desc = normalize_description(field.get("description"))
        lines.append(f"  - {field.get('name')} (args: {arg_names}): {field_desc}")

    return lines


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    config_path = repo_root / "config.local.js"
    kb_dir = repo_root / "knowledge-base" / "graphql"

    if not config_path.exists():
        print(f"Missing config file: {config_path}", file=sys.stderr)
        return 1

    config_text = config_path.read_text(encoding="utf-8")

    client_id = get_config_value(config_text, "clientId")
    client_secret = get_config_value(config_text, "clientSecret")
    access_token = get_config_value(config_text, "accessToken")
    api_url = get_config_value(config_text, "apiUrl") or DEFAULT_API_URL
    oauth_url = get_config_value(config_text, "oauthUrl") or DEFAULT_OAUTH_URL
    token_type = get_config_value(config_text, "tokenType") or "Bearer"

    has_access_token = bool(access_token) and access_token not in PLACEHOLDER_TOKENS
    has_client_credentials = (
      bool(client_id)
      and bool(client_secret)
      and client_id not in PLACEHOLDER_CLIENTS
      and client_secret not in PLACEHOLDER_CLIENTS
    )

    if not has_access_token and not has_client_credentials:
      print(
        "config.local.js must contain either accessToken or both clientId and clientSecret.",
        file=sys.stderr,
      )
      return 1

    token_source = "config.local.js accessToken"
    if not has_access_token:
      try:
        oauth_result = oauth_token(oauth_url, client_id, client_secret)
      except RuntimeError as exc:
        print(f"OAuth request failed. Ensure clientId/clientSecret are valid. Details: {exc}", file=sys.stderr)
        return 1

      access_token = oauth_result["access_token"]
      token_type = oauth_result.get("token_type") or token_type or "Bearer"
      config_text = write_config_value(config_text, "accessToken", access_token)
      config_text = write_config_value(config_text, "tokenType", token_type)
      config_path.write_text(config_text, encoding="utf-8")
      token_source = "config.local.js client credentials"

    authorization = f"{token_type} {access_token}"

    try:
        full_result = graphql_post(api_url, authorization, FULL_QUERY)
        root_result = graphql_post(api_url, authorization, ROOT_QUERY)
        type_result = graphql_post(api_url, authorization, TYPE_QUERY)
    except RuntimeError as exc:
        print(f"GraphQL request failed. Ensure token is valid and not expired. Details: {exc}", file=sys.stderr)
        return 1

    kb_dir.mkdir(parents=True, exist_ok=True)

    (kb_dir / "introspection-full.json").write_text(
        json.dumps(full_result, indent=2),
        encoding="utf-8",
    )
    (kb_dir / "root-schema-summary.json").write_text(
        json.dumps(root_result, indent=2),
        encoding="utf-8",
    )
    (kb_dir / "core-types-summary.json").write_text(
        json.dumps(type_result, indent=2),
        encoding="utf-8",
    )

    types = (full_result.get("data") or {}).get("__schema", {}).get("types", [])

    kind_counts = {
        "OBJECT": 0,
        "INPUT_OBJECT": 0,
        "ENUM": 0,
        "SCALAR": 0,
        "INTERFACE": 0,
        "UNION": 0,
    }
    for t in types:
        kind = t.get("kind")
        if kind in kind_counts:
            kind_counts[kind] += 1

    schema = (root_result.get("data") or {}).get("__schema", {})
    query_type = (schema.get("queryType") or {}).get("name") or "unknown"
    mutation_type = (schema.get("mutationType") or {}).get("name") or "none"
    subscription_type = (schema.get("subscriptionType") or {}).get("name") or "none"
    directives = schema.get("directives") or []
    root_fields = (schema.get("queryType") or {}).get("fields") or []

    root_field_lines = [
        f"- {field.get('name')}: {normalize_description(field.get('description'))}"
        for field in root_fields
    ]

    refreshed_at = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %z")

    md: list[str] = []
    md.append("# ESO Logs GraphQL Knowledge Base")
    md.append("")
    md.append(f"Last refreshed: {refreshed_at}")
    md.append(f"Endpoint: {api_url}")
    md.append(f"Token source: {token_source}")
    md.append("")
    md.append("## Schema Overview")
    md.append("")
    md.append(f"- Query root type: {query_type}")
    md.append(f"- Mutation root type: {mutation_type}")
    md.append(f"- Subscription root type: {subscription_type}")
    md.append(f"- Total types: {len(types)}")
    md.append(f"- OBJECT types: {kind_counts['OBJECT']}")
    md.append(f"- INPUT_OBJECT types: {kind_counts['INPUT_OBJECT']}")
    md.append(f"- ENUM types: {kind_counts['ENUM']}")
    md.append(f"- SCALAR types: {kind_counts['SCALAR']}")
    md.append(f"- INTERFACE types: {kind_counts['INTERFACE']}")
    md.append(f"- UNION types: {kind_counts['UNION']}")
    md.append(f"- Directives: {len(directives)}")
    md.append("")
    md.append("## Root Query Fields")
    md.append("")
    md.extend(root_field_lines)
    md.append("")
    md.append("## Core Domain Type Snapshots")
    md.append("")

    core_data = (type_result.get("data") or {})
    for title, key in [
        ("ReportData", "reportData"),
        ("CharacterData", "characterData"),
        ("GuildData", "guildData"),
        ("WorldData", "worldData"),
        ("RateLimitData", "rateLimitData"),
        ("UserData", "userData"),
    ]:
        md.append(f"### {title}")
        md.extend(format_type_section(core_data.get(key)))
        md.append("")

    md.append("## Source Artifacts")
    md.append("")
    md.append("- introspection-full.json: Full schema introspection result.")
    md.append("- root-schema-summary.json: Query root and directives summary.")
    md.append("- core-types-summary.json: Focused summary of key top-level data objects.")

    (kb_dir / "README.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"Knowledge base refreshed in {kb_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
