# Project atlas workflow

## Inspect before narrating

1. Enumerate the project and read applicable repository instructions. Exclude secrets, credentials, generated bundles, dependencies, binaries and build artifacts. Use `scripts/inventory.py ROOT --out inventory.json` for Python/JS/TS source metadata. This script indexes files; it does not understand or verify their behavior.
2. Read the application bootstrap, route registration, public request schemas, feature configuration names/defaults, and all relevant entrypoints. Follow each entrypoint into services, routers, tool adapters, persistence, streaming, cancellation, and error handling. Read tests to identify intended boundary cases. Prefer implementation over stale README claims.
3. Record which files were semantically inspected, which were only indexed, and what remains out of scope. Never claim to have read or covered every behavior merely because the inventory enumerated every file. For large repositories, work subsystem by subsystem and keep a coverage ledger.
4. Build a matrix with: trigger/example input, exact route predicates, ordered stages, external dependencies, success/alternate/failure outcomes, evidence, and demo assignment. Similar questions can take different paths due to flags and state. An example question alone cannot prove what a stochastic router will select.

## Branch checklist (investigate, do not invent)

- Ordinary question with no tool; complex question without special mode; explicit deep/research mode.
- Router/model failures and uncertain routing; fallback behavior.
- Local computation vs remote tool call; transport; success, invalid payload, timeout, retries and fallback provider.
- Attachment absent/present; text extraction vs image OCR; retrieval empty or failed.
- Auth/ownership/schema/quota rejection, before vs after stream start.
- Versioned request protocols, admission, duplicate keys, replay, conflicts.
- Review pass/revise/exhaustion; deadline and token/call budgets; partial results.
- Cancellation, disconnect, expired workers; publication and persistence races.
- Specialized media/background jobs, polling, and failed jobs.

Mark a case `not present`, `not reachable from the inspected entrypoint`, `not inspected`, or `illustrative assumption` when applicable. A generic checklist is not evidence that a project implements each feature.

## Compose an atlas

Create a routing overview and focused demos by mechanism, normally 4–8 actors each. Use multiple scenarios per demo for alternative outcomes. Avoid a single giant sequence diagram that shrinks every message into unreadable text.

Every scenario needs English `preconditions`, an `outcome`, and source `evidence` on its steps. Cite relative source path, symbol, and line number. The source ledger should include content hashes so readers know which snapshot was inspected. Never package secret values or unrequested source dumps.

Match visual explanation to behavior: branch highlighting for decisions, moving messages for calls/returns, repeated edge traversal for retries, a named grouped stage for parallel work, explicit commit/publication stages for persistence, and a distinct terminal explanation for failure. The bundled player is sequential. Represent concurrent work as a single labeled batch with explicit disclosure; do not falsely animate workers as sequential executions. Timing is educational pacing, not telemetry.

Create `atlas.json` beside each diagram/story pair:

```json
{
  "title": "Project execution atlas",
  "summary": "Source-backed walkthroughs of the main request paths.",
  "scope": "Static inspection of the API and its reachable services; no live calls.",
  "limitations": ["Deployment configuration was not inspected."],
  "demos": [{
    "id": "routing",
    "diagram": "routing.mmd",
    "story": "routing.story.json",
    "summary": "How request flags select the pipeline."
  }]
}
```

Build the complete collection with:

```sh
python <skill-dir>/scripts/atlas.py atlas.json --out site
```

The builder validates all diagrams/stories first, requires evidence and scenario contracts, then creates offline pages, a searchable index, and `all-in-one.html`. Prefer delivering the single-file bundle: it embeds the complete atlas and supports switching walkthroughs without opening separate files. Source files remain next to the manifest. Existing generated pages require `--force`. Keep `SOURCES.md` and a coverage ledger beside the manifest.

## Verify and report

Inspect every generated scenario, not only the first page. Verify evidence references, branch conditions, arrow direction, terminal outcomes and omitted steps against code. Browser-check all pages for errors, scenario switching, controls, keyboard access, mobile overflow and offline behavior. Report static source verification separately from executing the actual backend. A passing animation test does not validate production behavior or LLM decisions.
