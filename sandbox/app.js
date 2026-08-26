const statusEl = document.getElementById("status");
const queryInputEl = document.getElementById("queryInput");
const variablesInputEl = document.getElementById("variablesInput");
const runButtonEl = document.getElementById("runButton");
const responseEl = document.getElementById("response");
const PLACEHOLDER_TOKENS = new Set(["REPLACE_WITH_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN"]);
const PLACEHOLDER_CLIENTS = new Set(["REPLACE_WITH_CLIENT_ID", "YOUR_CLIENT_ID", "REPLACE_WITH_CLIENT_SECRET", "YOUR_CLIENT_SECRET"]);
const DEFAULT_OAUTH_URL = "https://www.esologs.com/oauth/token";

if (!statusEl || !queryInputEl || !variablesInputEl || !runButtonEl || !responseEl) {
  throw new Error("Required UI elements were not found in sandbox/index.html");
}

function setStatus(message) {
  statusEl.textContent = message;
}

function setResponse(message) {
  responseEl.textContent = message;
}

function loadConfig() {
  const config = window.ESOLOGS_LOCAL_CONFIG;
  if (!config) {
    throw new Error("Missing window.ESOLOGS_LOCAL_CONFIG. Check config.local.js");
  }

  if (!config.apiUrl) {
    throw new Error("Missing config value: apiUrl");
  }

  if (!config.oauthUrl) {
    config.oauthUrl = DEFAULT_OAUTH_URL;
  }

  const hasAccessToken = Boolean(config.accessToken) && !PLACEHOLDER_TOKENS.has(config.accessToken);
  const hasClientCredentials = Boolean(config.clientId) && Boolean(config.clientSecret)
    && !PLACEHOLDER_CLIENTS.has(config.clientId)
    && !PLACEHOLDER_CLIENTS.has(config.clientSecret);

  if (!hasAccessToken && !hasClientCredentials) {
    throw new Error("Provide either accessToken or both clientId and clientSecret in config.local.js");
  }

  config.hasAccessToken = hasAccessToken;
  config.hasClientCredentials = hasClientCredentials;

  return config;
}

function redact(value) {
  if (!value || value.length < 8) {
    return "[set]";
  }

  return `${value.slice(0, 4)}...${value.slice(-4)}`;
}

function parseVariables(variablesText) {
  if (!variablesText.trim()) {
    return {};
  }

  return JSON.parse(variablesText);
}

async function fetchAccessToken(config) {
  const body = new URLSearchParams({
    grant_type: "client_credentials",
    client_id: config.clientId,
    client_secret: config.clientSecret
  });

  let response;
  try {
    response = await fetch(config.oauthUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded"
      },
      body
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`OAuth network error: ${message}`);
  }

  const rawResponse = await response.text();
  let responseData;

  try {
    responseData = JSON.parse(rawResponse);
  } catch {
    responseData = { raw: rawResponse };
  }

  if (!response.ok || !responseData.access_token) {
    throw new Error(`OAuth request failed (${response.status}): ${JSON.stringify(responseData, null, 2)}`);
  }

  config.accessToken = responseData.access_token;
  config.tokenType = responseData.token_type || config.tokenType || "Bearer";
  config.hasAccessToken = true;
  return config.accessToken;
}

async function resolveAccessToken(config) {
  if (config.hasAccessToken) {
    return config.accessToken;
  }

  if (!config.hasClientCredentials) {
    throw new Error("No usable access token or client credentials available.");
  }

  setStatus("Acquiring access token...");
  return fetchAccessToken(config);
}

async function executeQuery(config) {
  const query = queryInputEl.value.trim();
  if (!query) {
    throw new Error("Query cannot be empty.");
  }

  const variables = parseVariables(variablesInputEl.value);
  const accessToken = await resolveAccessToken(config);

  let graphqlResponse;
  try {
    graphqlResponse = await fetch(config.apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `${config.tokenType || "Bearer"} ${accessToken}`
      },
      body: JSON.stringify({
        query,
        variables
      })
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(
      `GraphQL network error: ${message}. This is commonly a CORS or connectivity issue when calling the API from browser local/static origins.`
    );
  }

  const rawGraphql = await graphqlResponse.text();
  let graphqlData;

  try {
    graphqlData = JSON.parse(rawGraphql);
  } catch {
    graphqlData = { raw: rawGraphql };
  }

  if (!graphqlResponse.ok) {
    throw new Error(`GraphQL request failed (${graphqlResponse.status}): ${JSON.stringify(graphqlData, null, 2)}`);
  }

  return graphqlData;
}

function attachHandlers(config) {
  runButtonEl.addEventListener("click", async () => {
    runButtonEl.disabled = true;
    setStatus("Running request...");

    try {
      const data = await executeQuery(config);
      setResponse(JSON.stringify(data, null, 2));
      setStatus("Request completed.");
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setResponse(message);
      setStatus("Request failed.");
    } finally {
      runButtonEl.disabled = false;
    }
  });
}

function run() {
  try {
    const config = loadConfig();

    setStatus([
      "Configuration loaded.",
      `clientId: ${config.hasClientCredentials ? redact(config.clientId) : "[not set]"}`,
      `clientSecret: ${config.hasClientCredentials ? redact(config.clientSecret) : "[not set]"}`,
      `accessToken: ${config.hasAccessToken ? redact(config.accessToken) : "[will acquire on demand]"}`,
      `apiUrl: ${config.apiUrl}`,
      `oauthUrl: ${config.oauthUrl}`,
      `tokenType: ${config.tokenType || "Bearer"}`
    ].join("\n"));
    attachHandlers(config);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    setStatus(`Config error: ${message}`);
    runButtonEl.disabled = true;
  }
}

try {
  run();
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  setStatus(`Startup error: ${message}`);
}
