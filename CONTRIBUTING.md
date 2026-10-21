# Contributing to Diagram to Motion

Thank you for your interest in contributing to Diagram to Motion! This project is an agent skill and developer tool for turning Mermaid architecture diagrams into interactive, animated walkthroughs.

## Development Setup

### Requirements
- Python 3.10+ (Standard library only; zero pip dependencies for core build)
- Node.js 18+ (Development dependency only, for Playwright browser checks)

### Getting Started

1. Clone the repository:
   ```sh
   git clone https://github.com/JimmyNguyen09-AI/diagram2motion.git
   cd diagram2motion
   ```

2. Run Python unit tests:
   ```sh
   python -m unittest discover -s tests -v
   ```

3. (Optional) Run browser automated checks:
   ```sh
   npm install
   npx playwright install chromium
   npm run test:browser
   ```

## Adding Features

- **Mermaid Parser Extensions**: Add new shape or arrow support in `scripts/build.py`. Always ensure unsupported or ambiguous statements fail clearly rather than dropping semantics silently. Add matching unit tests in `tests/test_build.py`.
- **Viewer Improvements**: Edit `assets/viewer.html`. Keep it completely self-contained with no external CDN or font dependencies so it functions 100% offline. Rebuild `demo.html` after modifying `viewer.html`:
  ```sh
  python scripts/build.py build examples/cache.mmd --story examples/cache.story.json --out demo.html --force
  ```
- **Developer Context & Payloads**: Ensure `schema/story.schema.json` and `schema/graph.schema.json` are updated if introducing new properties.

## Pull Request Checklist

- [ ] All unit tests pass: `python -m unittest discover -s tests -v`
- [ ] Browser tests pass: `npm run test:browser`
- [ ] No extraneous build files or proprietary artifacts committed
- [ ] Code follows existing style and formatting
