(function () {
  const PLACEHOLDER_TOKENS = new Set(["REPLACE_WITH_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN"]);
  const PLACEHOLDER_CLIENTS = new Set([
    "REPLACE_WITH_CLIENT_ID",
    "YOUR_CLIENT_ID",
    "REPLACE_WITH_CLIENT_SECRET",
    "YOUR_CLIENT_SECRET"
  ]);

  const DEFAULT_API_URL = "https://www.esologs.com/api/v2/client";
  const DEFAULT_OAUTH_URL = "https://www.esologs.com/oauth/token";

  function loadConfig() {
    const config = window.ESOLOGS_LOCAL_CONFIG;
    if (!config) {
      throw new Error("Missing window.ESOLOGS_LOCAL_CONFIG. Check config.local.js");
    }

    config.apiUrl = config.apiUrl || DEFAULT_API_URL;
    config.oauthUrl = config.oauthUrl || DEFAULT_OAUTH_URL;
    config.tokenType = config.tokenType || "Bearer";

    const hasAccessToken = Boolean(config.accessToken) && !PLACEHOLDER_TOKENS.has(config.accessToken);
    const hasClientCredentials = Boolean(config.clientId)
      && Boolean(config.clientSecret)
      && !PLACEHOLDER_CLIENTS.has(config.clientId)
      && !PLACEHOLDER_CLIENTS.has(config.clientSecret);

    if (!hasAccessToken && !hasClientCredentials) {
      throw new Error("Provide either accessToken or both clientId and clientSecret in config.local.js");
    }

    config.hasAccessToken = hasAccessToken;
    config.hasClientCredentials = hasClientCredentials;

    return config;
  }

  async function fetchAccessToken(config) {
    const body = new URLSearchParams({
      grant_type: "client_credentials",
      client_id: config.clientId,
      client_secret: config.clientSecret
    });

    const response = await fetch(config.oauthUrl, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body
    });

    const raw = await response.text();
    let data;

    try {
      data = JSON.parse(raw);
    } catch {
      data = { raw };
    }

    if (!response.ok || !data.access_token) {
      throw new Error(`OAuth request failed (${response.status}): ${JSON.stringify(data, null, 2)}`);
    }

    config.accessToken = data.access_token;
    config.tokenType = data.token_type || config.tokenType || "Bearer";
    config.hasAccessToken = true;
    return config.accessToken;
  }

  async function resolveAccessToken(config, onStatus) {
    if (config.hasAccessToken) {
      return config.accessToken;
    }

    if (!config.hasClientCredentials) {
      throw new Error("No usable access token or client credentials available.");
    }

    if (typeof onStatus === "function") {
      onStatus("Acquiring access token...");
    }

    return fetchAccessToken(config);
  }

  async function query(config, graphqlQuery, variables, onStatus) {
    const accessToken = await resolveAccessToken(config, onStatus);

    const response = await fetch(config.apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `${config.tokenType} ${accessToken}`
      },
      body: JSON.stringify({
        query: graphqlQuery,
        variables: variables || {}
      })
    });

    const raw = await response.text();
    let payload;

    try {
      payload = JSON.parse(raw);
    } catch {
      payload = { raw };
    }

    if (!response.ok || payload.errors) {
      throw new Error(`GraphQL request failed (${response.status}): ${JSON.stringify(payload, null, 2)}`);
    }

    return payload;
  }

  window.ESOLogsClient = {
    loadConfig,
    query
  };
})();
