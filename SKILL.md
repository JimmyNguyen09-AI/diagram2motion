---
name: diagram-to-motion
description: Analyze a codebase or diagram and create an interactive developer execution atlas with animated scenario walkthroughs, branch predicates, data payloads, database queries, and code evidence. Supports Mermaid flowcharts, subgraphs, sequence diagrams, and offline HTML viewing. Use to explain how software actually executes under the hood.
---

# Diagram to Motion (Developer-Grade Architecture Engine)

Make the diagram explain software execution: let the engineer follow a request's runtime path, inspect payloads, database operations, and compare outcome branches. Deliver a standalone HTML file plus editable source and scenario JSON. The bundled renderer works offline and requires only Python 3.10+ to build.

## Output language and scope

Write all authored documentation, HTML, diagram labels, scenarios, navigation, and explanations in English (unless the user explicitly requests another language). Keep source identifiers and protocol tokens unchanged.

For a repository request, use **project atlas mode**: read [references/project-analysis.md](references/project-analysis.md), inventory the project, follow entrypoints through their implementation, build a branch coverage matrix, and produce several focused demos linked from an index.

Find the actual predicates: flags, route decisions, feature configuration, budgets, attachments, authentication, and model/tool outputs. Distinguish active call paths from unused classes and tests. Verify whether a tool is an in-process call, HTTP API, SDK call, or actual MCP transport.

## Developer-grade detail requirements

Do not produce superficial or purely decorative walkthroughs. Make the diagram truly valuable to developers:
- **Subgraphs & Boundaries**: Use `subgraph` in Mermaid to clearly partition tiers (e.g. `Client Tier`, `API Gateway Ingress`, `Worker Pool`, `Persistence Tier`).
- **Branch Predicates**: On decision steps, provide the exact code predicate in `predicate` (e.g., `user.is_authenticated == True && cache.miss == True`).
- **Developer Context & Payloads**: Include `dev_context` on meaningful steps showing:
  - `protocol`: REST / HTTPS, gRPC, WebSocket, Redis RESP, PostgreSQL Wire, etc.
  - `request_payload` / `response_payload`: Representative JSON bodies, parameters, or return status codes.
  - `database_operation`: Exact SQL query, ORM method, or Redis command.
  - `headers`: Pertinent authentication tokens or tracing IDs (`X-Request-Id`).
- **Source Code Evidence**: Reference exact file paths, line ranges, and symbols in `evidence` (e.g. `app/services/auth.py:42-58 · verify_token`).

## Build the walkthrough

1. Read [references/format.md](references/format.md) for the supported Mermaid subset and scenario contract.
2. Inspect or scaffold the diagram:
   ```sh
   python <skill-dir>/scripts/build.py inspect diagram.mmd
   python <skill-dir>/scripts/build.py scaffold diagram.mmd --out story.json
   ```
   Or use the packaged CLI if installed: `diagram-to-motion scaffold diagram.mmd --out story.json`.
3. Author the scenario JSON with meaningful scenarios (e.g., cache hit vs cache miss, authenticated vs unauthorized, success vs fallback retry). Fill in titles, technical details, `predicate`, `dev_context`, and `evidence`.
4. Build the walkthrough:
   ```sh
   python <skill-dir>/scripts/build.py build diagram.mmd --story story.json --out walkthrough.html
   ```
5. Inspect the generated walkthrough in a browser. Check play/pause, step stepping, inspector tabs (Overview, Dev Context, Evidence), Light/Dark themes, and Voice narration.

## Supported Mermaid features

- **Flowcharts**: `flowchart LR/TD/RL/BT`, `graph TD/LR`.
- **Subgraphs**: `subgraph ID ["Label"] ... end` for architecture boundary boxes.
- **Node Shapes**: `A["Rect"]`, `A("Round")`, `A{"Decision"}`, `db[("Database")]`, `queue(["Topic/Queue"])`, `event(("Signal/State"))`.
- **Edges**: `-->`, `->`, `-.->` (dashed), `==>` (thick), `---`. Edge labels: `--> |label|` and `-->|label|`.
- **Sequence Diagrams**: `sequenceDiagram`, `participant`, `actor`, messages `->>`, `->`, `-->>`, `-->`.
- **Fault-Tolerant Directives**: Gracefully ignores `autonumber`, `title`, `Note`, `%%{init:...}%%`, `classDef`, `style` without crashing.

For complete references and schemas, see `schema/story.schema.json`, `schema/graph.schema.json`, `examples/cache.mmd`, and `tests/fixtures/dev-atlas/`.
