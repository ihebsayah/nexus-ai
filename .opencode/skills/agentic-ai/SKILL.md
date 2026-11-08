---
name: agentic-ai
description: Use when designing or implementing NEXUS AI runtime agent workflows with LangGraph, RAG over pgvector, local Ollama models, tool calling, guardrails, or evaluations. Triggers on LangGraph, agent graph, RAG, retrieval, embedding, Ollama, prompt, tool schema, or evaluation.
license: MIT
compatibility: opencode
metadata:
  audience: ai-engineers
  version: "1.0"
---

# Agentic AI

## When to use

Use for NEXUS AI runtime agent behavior: graph design, retrieval, local model integration, tool calling, structured outputs, guardrails, and evaluations. This skill is about the product's runtime agents, not the OpenCode development agents.

## Instructions

1. Define the workflow state, inputs, outputs, tools, and stopping conditions before writing graph code.
2. Choose the simplest graph that satisfies the task. Avoid cycles unless they have an explicit exit condition.
3. Keep model calls behind a small interface so the local model can be swapped without rewriting the graph.
4. For RAG, define chunking, embedding model, embedding dimension, distance metric, retrieval count, and citation behavior.
5. Store embeddings in pgvector with an explicit dimension. Do not mix embedding models in one index.
6. Treat model output as untrusted input. Validate structured outputs and tool arguments before acting on them.
7. Add timeouts, retries, and fallbacks for model and tool failures.
8. Budget for 16 GB unified memory: prefer smaller local models, limit concurrent model calls, and document the trade-off.
9. Build a small evaluation set with expected outcomes. Record actual results; never estimate accuracy.
10. Distinguish deterministic tests from model-dependent evaluations.

## Checklist

- [ ] Graph state and transitions are documented.
- [ ] Tool schemas are explicit and validated.
- [ ] Retrieval configuration is explicit and reproducible.
- [ ] Embedding dimension and index type are consistent.
- [ ] Model output is validated before use.
- [ ] Failure modes have timeouts or fallbacks.
- [ ] Resource budget is documented.
- [ ] Evaluation cases exist and were actually run.
- [ ] No paid model or cloud API is used.
- [ ] Runtime agents are clearly distinguished from OpenCode development agents.

## Expected output

Graph or workflow specification, prompts, tool schemas, retrieval configuration, tests, and an evaluation report with actual results.

## Verification

- The evaluation or test command was executed and its output reported.
- Metrics are measured, not invented.
- The workflow stops or escalates on failure.
- The design fits the documented local resource budget.
