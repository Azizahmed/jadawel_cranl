import { performance } from "node:perf_hooks";

const frontendBaseUrl =
  process.env.LOAD_BASE_URL ||
  process.env.PUBLIC_WEB_FRONTEND_URL ||
  "http://localhost:3000";
const backendBaseUrl =
  process.env.LOAD_BACKEND_URL ||
  process.env.PUBLIC_BACKEND_URL ||
  "http://localhost:8000";
const authEmail = process.env.LOAD_AUTH_EMAIL;
const authPassword = process.env.LOAD_AUTH_PASSWORD;
let bearerToken = process.env.LOAD_BEARER_TOKEN;

if ((authEmail && !authPassword) || (!authEmail && authPassword)) {
  throw new Error(
    "LOAD_AUTH_EMAIL and LOAD_AUTH_PASSWORD must be provided together.",
  );
}
if (!bearerToken && authEmail && authPassword) {
  const response = await fetch(
    new URL("/api/user/token-auth/", backendBaseUrl),
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email: authEmail, password: authPassword }),
      signal: AbortSignal.timeout(10_000),
    },
  );
  if (!response.ok) {
    throw new Error(
      `Load-test authentication failed with HTTP ${response.status}.`,
    );
  }
  const data = await response.json();
  bearerToken = data.access_token;
  if (!bearerToken) {
    throw new Error("Load-test authentication returned no access token.");
  }
}

const configuredTargets = process.env.LOAD_URLS || process.env.LOAD_PATHS;
const targets = configuredTargets
  ? configuredTargets
      .split(",")
      .map((target) => target.trim())
      .filter(Boolean)
      .map((target) => ({
        url: new URL(target, frontendBaseUrl),
        authenticated: Boolean(bearerToken),
      }))
  : [
      { url: new URL("/_health", frontendBaseUrl), authenticated: false },
      { url: new URL("/login", frontendBaseUrl), authenticated: false },
      {
        url: new URL("/api/settings/", backendBaseUrl),
        authenticated: false,
      },
      ...(bearerToken
        ? [
            {
              url: new URL("/api/workspaces/", backendBaseUrl),
              authenticated: true,
            },
          ]
        : []),
    ];
const total = Number(process.env.LOAD_TOTAL || 600);
const concurrency = Number(process.env.LOAD_CONCURRENCY || 60);
const timeoutMs = Number(process.env.LOAD_TIMEOUT_MS || 10_000);
const maxErrorRate = Number(process.env.LOAD_MAX_ERROR_RATE || 0);
const maxP95Ms = Number(process.env.LOAD_MAX_P95_MS || 1_500);

if (!Number.isInteger(total) || total < 1) {
  throw new Error("LOAD_TOTAL must be a positive integer.");
}
if (!Number.isInteger(concurrency) || concurrency < 1) {
  throw new Error("LOAD_CONCURRENCY must be a positive integer.");
}

let nextRequest = 0;
const durations = [];
const failures = [];
const startedAt = performance.now();

async function worker() {
  while (true) {
    const requestIndex = nextRequest++;
    if (requestIndex >= total) {
      return;
    }

    const target = targets[requestIndex % targets.length];
    const { url } = target;
    const requestStartedAt = performance.now();

    try {
      const response = await fetch(url, {
        headers:
          target.authenticated && bearerToken
            ? { authorization: `JWT ${bearerToken}` }
            : undefined,
        redirect: "error",
        signal: AbortSignal.timeout(timeoutMs),
      });
      await response.arrayBuffer();
      durations.push(performance.now() - requestStartedAt);
      if (!response.ok) {
        failures.push(`${response.status} ${url}`);
      }
    } catch (error) {
      durations.push(performance.now() - requestStartedAt);
      failures.push(`${error.name}: ${url}`);
    }
  }
}

await Promise.all(
  Array.from({ length: Math.min(concurrency, total) }, () => worker()),
);

durations.sort((left, right) => left - right);
const percentile = (value) =>
  durations[
    Math.min(durations.length - 1, Math.ceil(value * durations.length) - 1)
  ];
const elapsedMs = performance.now() - startedAt;
const errorRate = failures.length / total;
const summary = {
  targets: targets.map(({ url, authenticated }) => ({
    url: url.toString(),
    authenticated,
  })),
  total,
  concurrency,
  succeeded: total - failures.length,
  failed: failures.length,
  errorRate,
  requestsPerSecond: Number((total / (elapsedMs / 1000)).toFixed(1)),
  p50Ms: Number(percentile(0.5).toFixed(1)),
  p95Ms: Number(percentile(0.95).toFixed(1)),
  p99Ms: Number(percentile(0.99).toFixed(1)),
};

console.log(JSON.stringify(summary, null, 2));

if (errorRate > maxErrorRate) {
  console.error(`Error rate ${errorRate} exceeded ${maxErrorRate}.`);
  console.error(failures.slice(0, 10).join("\n"));
  process.exitCode = 1;
}
if (summary.p95Ms > maxP95Ms) {
  console.error(`p95 ${summary.p95Ms}ms exceeded ${maxP95Ms}ms.`);
  process.exitCode = 1;
}
