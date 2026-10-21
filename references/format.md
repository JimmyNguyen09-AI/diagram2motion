# Source and story format

## CLI

Python 3.10+, standard library only. Paths may be absolute or relative to the invocation directory. Existing output is refused unless `--force` is supplied.

```sh
python scripts/build.py inspect examples/cache.mmd
python scripts/build.py build examples/cache.mmd --story examples/cache.story.json --out demo.html
python scripts/build.py validate examples/cache.mmd --story examples/cache.story.json
```

## Mermaid subset

This is a focused, robust importer for architectural diagrams. One statement per line, optional trailing semicolon; blank lines and full-line `%%` comments are supported. IDs can contain ASCII letters, digits, underscores, and hyphens (`[a-zA-Z0-9_-]+`). Labels are plain text; quote node labels that contain brackets, braces, parentheses, or arrows (e.g. `A["Cache (Redis) -> fast"]`). Mermaid `%%{...}%%` directives, `title`, and `autonumber` are safely ignored.

Flowcharts: `flowchart LR`, `graph TD`, and directions LR/RL/TD/TB/BT.
- **Nodes**: `A`, `A[Label]` (rect), `A(Label)` (rounded rect), `A{Decision}` (diamond), `A[(Database)]` (cylinder), `A([Queue/Topic])` (stadium), `A((Event))` (circle).
- **Edges**: `A --> B`, `A -->|Label| B`, `A -- Label --> B`, `A -.-> B`, `A ==>|Label| B`, `A --- B` (undirected link), `A <--> B` (bidirectional), and fan-out/fan-in statements like `A & B --> C & D`. Node declarations can be inline at either endpoint.
- **Subgraphs**: `subgraph ID [Label]` ... `end` blocks with optional `direction LR/TB`. Subgraph boundaries group contained nodes cleanly.
- Node shapes, labels, and edge IDs `e1`, `e2`, ... follow source order. Edges are not deduplicated; two arrows between the same actors can represent distinct flows or steps.

Sequence diagrams: `sequenceDiagram`, `participant A as Alice`, `actor B as Bob`, messages `A->>B: Request` and `B-->>A: Response`, including self messages. Implicit participants are supported. The renderer retains participant order, message order, and solid/dashed arrows. Actor declarations are drawn as labeled lanes.

Not imported: chained multi-target edges in sequence diagrams, custom CSS styling directives, click/href callbacks, Mermaid frontmatter, activation bars, `alt`/`opt`/`loop`/`par` blocks. If complex branch logic or loops occur, translate them into explicit scenarios with disclosed preconditions and outcomes.

Syntax references: [Mermaid flowcharts](https://mermaid.js.org/syntax/flowchart.html) and [sequence diagrams](https://mermaid.js.org/syntax/sequenceDiagram.html).

## Normalized graph (escape hatch)

Pass a `.json` file as the diagram argument:

```json
{
  "kind": "flowchart",
  "direction": "LR",
  "source": "Original source text or an honest description of its origin",
  "nodes": [
    {"id": "A", "label": "Client", "shape": "round", "x": 150, "y": 130},
    {"id": "B", "label": "API", "shape": "rect", "x": 450, "y": 130}
  ],
  "edges": [{"id": "e1", "from": "A", "to": "B", "label": "GET /items", "style": "solid"}]
}
```

`kind`: `flowchart` or `sequence`; `direction` defaults to LR. Shapes: rect, round, diamond. Edge styles: solid, dashed, thick. Coordinates are optional positive SVG units (node centers); set both x and y for every node or for none. Sequence diagrams compute their own lanes. Default flowchart layout is a simple grid oriented by direction, not a graph optimizer; provide positions for complex graphs. Keep labels short (roughly 32 characters). IDs must be unique within nodes/edges; edge endpoints must exist.

## Story JSON

```json
{
  "title": "Follow a request",
  "subtitle": "A narrated architecture walkthrough",
  "language": "en",
  "assumptions": ["This is a teaching model; step duration is not actual latency."],
  "scenarios": [{
    "id": "success",
    "label": "Successful request",
    "description": "The client receives a successful response.",
    "steps": [{
      "edge": "e1",
      "title": "Request arrives",
      "detail": "The client asks the API for the current list.",
      "duration_ms": 1800
    }]
  }]
}
```

Required: nonempty title; nonempty scenarios; unique scenario IDs; nonempty scenario labels and steps; each step references an existing edge and has a nonempty title and detail. Duration defaults to 1800 ms; integer range 300–15000. Subtitle, language, assumptions and scenario description are optional. Language defaults to en; controls currently remain English, while titles and explanations accept Unicode.

The `positions` object in a story can override all flowchart node coordinates: `"positions": {"A": [150,130], "B": [450,130]}`. The keys must exactly match all node IDs.

A scenario can traverse an edge repeatedly (e.g. an explicitly documented retry). There is no automatic path inference or invented reverse edge. Separate scenarios express alternatives, not concurrency. The timeline is sequential; simultaneous events require another renderer or a clearly disclosed teaching simplification.

The initial viewer shows the full topology and no active step. Next selects step 1; Play advances from the current step, and replays from the start after completion. Switching scenarios resets playback. Reduced-motion preferences suppress the moving particle and smooth scrolling; step playback remains available.

## Project atlas extensions

Write authored content in English (`language: "en"`). Each scenario can include `preconditions` (a list of English statements), `outcome` (text), and its own `graph` (the normalized graph schema above). A scenario-specific graph is useful when alternatives would otherwise make a giant unreadable union graph. Step edge IDs resolve against that scenario's graph when present. Coordinates should be embedded in those graphs, not in the global story positions.

Each step can include `evidence` (a list of source path/symbol/line references) and `kind`: call, return, decision, retry, parallel, persist, stream, or failure. The kind appears in the step caption; it describes the teaching stage, not a measurement or a scheduler. A parallel stage represents a grouped batch, not multiple simultaneously animated threads. Atlas mode requires scenario preconditions/outcomes and evidence on every step. The standalone builder keeps these fields optional for diagram-only requests.
