# Diagram to Motion

[![CI](https://github.com/JimmyNguyen09-AI/diagram2motion/actions/workflows/ci.yml/badge.svg)](https://github.com/JimmyNguyen09-AI/diagram2motion/actions/workflows/ci.yml)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-GitHub%20Pages-brightgreen?logo=githubpages&logoColor=white)](https://jimmynguyen09-ai.github.io/diagram2motion/)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Turn architecture diagrams into living, narrated execution walkthroughs for developers.**

A portable agent skill and CLI for interactive, animated architecture and runtime walkthroughs. Mermaid in; a standalone offline HTML file out. Explore request routes, inspect data payloads, SQL queries, and branch conditions step by step.

**Try it online:** [Live Interactive Walkthrough (GitHub Pages)](https://jimmynguyen09-ai.github.io/diagram2motion/) or inspect local [`demo.html`](demo.html) and [`sequence-demo.html`](sequence-demo.html). Explore the [Synthetic Microservices Atlas](tests/fixtures/dev-atlas/site/index.html).

---

## What it does

- **Developer Execution Inspector**: Inspect request payloads, response data, SQL/Redis operations, headers, and code references (`file:line`) on each step.
- **Branch Predicates & Conditions**: Explicitly explains *why* a specific branch executed (e.g. `user.is_authenticated == True && cache.miss == True`).
- **Subgraphs & Architecture Boundaries**: Supports `subgraph ... end` to visualize service tiers (Client, Gateway, Worker, Database).
- **Automatic DAG Layered Layout**: Generates clean, well-spaced diagrams automatically without requiring manual Cartesian pixel coordinates.
- **Rich Mermaid Shapes**: Supports rectangles, rounded pills, diamonds, databases `[(Postgres)]`, queues/topics `([Kafka])`, and events `((Signal))`.
- **Fault-Tolerant Parsing**: Resilient to whitespace around edge labels (`A --> |label| B`), hyphens and dots in node IDs (`api-gateway`), and gracefully skips directives (`autonumber`, `title`, `Note`).
- **Interactive Offline HTML**: Zero CDN, zero build server, zero font downloads. Works completely offline.
- **Voice Narration (TTS) & Themes**: Built-in Web Speech API voiceover and Light/Dark mode toggle.
- **Scaffold Command**: Instantly scaffold valid story JSON from any diagram to eliminate agent hallucinations.

---

## Quickstart

Requires Python 3.10+; standard library only (no pip dependencies for building).

### 1. Scaffold a Story from Mermaid

```sh
python scripts/build.py scaffold examples/cache.mmd --out my-story.json
```

### 2. Build the Interactive Walkthrough

```sh
python scripts/build.py build examples/cache.mmd --story examples/cache.story.json --out walkthrough.html
```

Open `walkthrough.html` directly in any web browser.

---

## Use with AI Coding Agents

`diagram-to-motion` is designed as a standardized Agent Skill. It is compatible with:
- **Anthropic Claude Code**: Copy to `.claude/skills/` or reference `SKILL.md`.
- **Google Antigravity / Gemini**: Place in `.agents/skills/diagram-to-motion/`.
- **Cursor / Windsurf / Codex**: Add to `.cursor/rules` or prompt with `SKILL.md`.

Prompt template for your agent:

> Read `diagram-to-motion/SKILL.md`. Turn this Mermaid architecture diagram into an interactive developer execution walkthrough with cache hit and cache miss scenarios. Include request payloads, database queries, branch predicates, and source code line evidence.

---

## Supported Mermaid Features

| Category | Syntax | Description |
| :--- | :--- | :--- |
| **Flowchart** | `flowchart LR`, `TD`, `RL`, `BT`, `graph` | Directed graphs with automatic layered layout |
| **Subgraphs** | `subgraph Tier ["Label"] ... end` | Boundary boxes clustering related nodes |
| **Node Shapes** | `A[Rect]`, `A(Round)`, `A{Decision}` | Standard flowchart shapes |
| **Data Shapes** | `db[(Database)]`, `q([Queue/Topic])`, `e((Event))` | Specialized developer storage & streaming shapes |
| **Edges & Labels** | `-->`, `->`, `-.->` (dashed), `==>` (thick), `---` | With optional labels `\|label\|` or `\| label \|` |
| **Sequence** | `sequenceDiagram`, `participant`, `actor` | Messages: `->>`, `->`, `-->>`, `-->` |
| **Directives** | `autonumber`, `title`, `Note`, `%%{...}%%` | Safely ignored or processed without crashing |

See [references/format.md](references/format.md) for full syntax and JSON schemas.

---

## Development & Testing

Run unit tests:
```sh
python -m unittest discover -s tests -v
```

Run Playwright browser integration checks:
```sh
npm install
npm run test:browser
```

Rebuild demo artifacts:
```sh
python scripts/build.py build examples/cache.mmd --story examples/cache.story.json --out demo.html --force
python scripts/build.py build examples/sequence.mmd --story examples/sequence.story.json --out sequence-demo.html --force
```

---

## License

MIT License. Includes viewer, scripts, skills, and synthetic examples.
