import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { createServer } from "node:http";
import { fileURLToPath } from "node:url";
import test from "node:test";

const scriptPath = fileURLToPath(
  new URL("./production-load-smoke.mjs", import.meta.url),
);

async function runLoadGate(environment) {
  const child = spawn(process.execPath, [scriptPath], {
    env: {
      ...process.env,
      LOAD_CONCURRENCY: "3",
      LOAD_MAX_ERROR_RATE: "0",
      LOAD_MAX_P95_MS: "2000",
      LOAD_MIN_RPS: "0",
      LOAD_TOTAL: "12",
      LOAD_WARMUP_ROUNDS: "0",
      ...environment,
    },
    stdio: ["ignore", "pipe", "pipe"],
  });
  let stdout = "";
  let stderr = "";
  child.stdout.setEncoding("utf8");
  child.stderr.setEncoding("utf8");
  child.stdout.on("data", (chunk) => {
    stdout += chunk;
  });
  child.stderr.on("data", (chunk) => {
    stderr += chunk;
  });
  const [exitCode] = await once(child, "exit");
  return { exitCode, stderr, stdout };
}

test("passes a healthy target and reports its gate label", async (context) => {
  const server = createServer((_request, response) => {
    response.writeHead(200, { "content-type": "application/json" });
    response.end("{}");
  });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  context.after(() => server.close());
  const { port } = server.address();

  const result = await runLoadGate({
    LOAD_BASE_URL: `http://127.0.0.1:${port}`,
    LOAD_LABEL: "test-capacity",
    LOAD_URLS: "/_health",
  });

  assert.equal(result.exitCode, 0, result.stderr);
  const summary = JSON.parse(result.stdout);
  assert.equal(summary.label, "test-capacity");
  assert.equal(summary.failed, 0);
  assert.equal(summary.total, 12);
});

test("fails when measured throughput is below the configured minimum", async (context) => {
  const server = createServer((_request, response) => {
    setTimeout(() => {
      response.writeHead(200, { "content-type": "application/json" });
      response.end("{}");
    }, 50);
  });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  context.after(() => server.close());
  const { port } = server.address();

  const result = await runLoadGate({
    LOAD_BASE_URL: `http://127.0.0.1:${port}`,
    LOAD_CONCURRENCY: "1",
    LOAD_MIN_RPS: "100",
    LOAD_TOTAL: "4",
    LOAD_URLS: "/_health",
  });

  assert.equal(result.exitCode, 1);
  assert.match(result.stderr, /Throughput .* was below 100/);
});

test("rejects a negative minimum throughput", async () => {
  const result = await runLoadGate({ LOAD_MIN_RPS: "-1" });

  assert.equal(result.exitCode, 1);
  assert.match(result.stderr, /LOAD_MIN_RPS must be a non-negative number/);
});
