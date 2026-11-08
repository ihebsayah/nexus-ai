---
name: mcp-development
description: Use when building or reviewing MCP servers, MCP clients, tool schemas, resources, prompts, or local stdio transport for NEXUS AI. Triggers on MCP, Model Context Protocol, MCP server, MCP client, tool schema, resource, stdio, or tool invocation.
license: MIT
compatibility: opencode
metadata:
  audience: ai-engineers
  version: "1.0"
---

# MCP Development

## When to use

Use for MCP server or client work: exposing tools, resources, or prompts, defining schemas, handling transport, and testing local integration. Do not use for general REST API design.

## Instructions

1. Define the MCP surface first: tools, resources, prompts, and their schemas.
2. Keep tool names and descriptions precise. The model chooses tools from the description.
3. Validate every tool argument on the server. Never trust the client or the model.
4. Return structured, bounded results. Avoid dumping unbounded data into a tool response.
5. Use local stdio transport by default for NEXUS AI. Do not expose an MCP server on a public interface without explicit review.
6. Do not put credentials in tool schemas, logs, or error messages.
7. Make side effects explicit and idempotent where possible.
8. Add timeouts and clear error responses.
9. Test with a local MCP client and verify the tool list and a representative invocation.
10. Document the server's capabilities, transport, and security boundary.

## Checklist

- [ ] Tools, resources, and prompts are documented.
- [ ] Input schemas are strict and validated server-side.
- [ ] Outputs are structured and bounded.
- [ ] Transport is local by default.
- [ ] No credentials are exposed.
- [ ] Side effects are explicit.
- [ ] Errors are actionable and do not leak internals.
- [ ] Local client test covers tool discovery and invocation.
- [ ] Security boundary is documented.

## Expected output

MCP server or client change, schema definitions, local test, and documentation of capabilities and boundaries.

## Verification

- The server starts locally and the tool list is observed.
- A representative tool call was executed and its result reported.
- Invalid input was rejected with a clear error.
- No paid service or public network exposure was introduced.
