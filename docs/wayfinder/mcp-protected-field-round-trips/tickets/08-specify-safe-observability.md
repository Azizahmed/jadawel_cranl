---
title: "Specify safe MCP errors, auditing, and observability"
labels:
  - "wayfinder:research"
status: closed
assignee: safe-observability-research-agent
parent: ../map.md
blocked_by: []
research_branch: research/mcp-safe-observability
research_note: ../research/safe-observability.md
---

## Question

Which metadata may safely appear in logs, traces, metrics, user errors, and audit
events while protecting plaintext and tokens; which current debug paths must change;
and what primary-source guidance defines adequate redaction, retention, and alerting?

## Resolution

Make every sink outside request processing content-blind: never emit protected
plaintext, mask tokens, endpoint keys, raw MCP messages, caller-controlled values,
or exception text. Use fixed safe error codes with correlation IDs and MCP tool
errors marked as errors. Keep an unsampled, allowlisted, append-only audit trail of
endpoint database ID, workspace/user IDs, registered tool, operation class, target
IDs, protected field IDs, policy revision, outcome, safe reason, and duration.
Treat access logs, proxies, telemetry, analytics, and DEBUG output as part of the
same boundary, and require canary-based leakage tests before release.

Research context: branch `research/mcp-safe-observability`, commit
`29ba9a2639ee08bfbd8e63c46a0ac3ce35a88980`, note
`docs/wayfinder/mcp-protected-field-round-trips/research/safe-observability.md`.
