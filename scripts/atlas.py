#!/usr/bin/env python3
"""Build a source-backed collection of offline walkthroughs."""
import argparse
import html
import json
import re
import sys
from pathlib import Path
from build import load_graph, render, require, validate_story


def local_file(root, name):
    require(isinstance(name, str) and bool(name), 'Input file must be a relative path.')
    path = (root / name).resolve()
    require(path.is_relative_to(root.resolve()), 'Input path must stay within the manifest directory.')
    require(path.is_file(), f'Missing input: {name}')
    return path


def build_atlas(manifest_path, out, force=False):
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    require(isinstance(manifest, dict), 'Manifest must be an object.')
    for key in ('title', 'summary', 'scope'):
        require(isinstance(manifest.get(key), str) and manifest[key].strip(), f'Manifest needs {key}.')
    limitations = manifest.get('limitations', [])
    require(isinstance(limitations, list) and all(isinstance(x, str) for x in limitations), 'Limitations must be strings.')
    demos = manifest.get('demos')
    require(isinstance(demos, list) and bool(demos), 'Manifest needs demos.')
    pages, ids, inputs, cards = {}, set(), {manifest_path.resolve()}, []
    scenario_count = 0
    bundle_items = [{'id': 'index', 'title': 'All walkthroughs'}]
    esc = html.escape
    for item in demos:
        require(isinstance(item, dict), 'Each demo must be an object.')
        ident = item.get('id')
        require(isinstance(ident, str) and re.fullmatch(r'[a-z][a-z0-9-]*', ident) and ident not in ('index', 'all-in-one') and ident not in ids, 'Demo IDs must be unique slugs other than index or all-in-one.')
        ids.add(ident)
        diagram = local_file(manifest_path.parent, item.get('diagram'))
        story_path = local_file(manifest_path.parent, item.get('story'))
        inputs.update((diagram, story_path))
        graph = load_graph(diagram)
        story = json.loads(story_path.read_text(encoding='utf-8-sig'))
        validate_story(graph, story)
        require(story.get('language', 'en') == 'en', f'{ident}: project atlas content must be English.')
        for scenario in story['scenarios']:
            require(scenario.get('preconditions') and scenario.get('outcome'), f'{ident}: each scenario needs preconditions and outcome.')
            require(all(step.get('evidence') for step in scenario['steps']), f'{ident}: each step needs source evidence.')
        story['atlas'] = True
        pages[f'{ident}.html'] = render(graph, story)
        bundle_items.append({'id': ident, 'title': story['title']})
        scenario_count += len(story['scenarios'])
        summary = item.get('summary', story.get('subtitle', ''))
        require(isinstance(summary, str), 'Demo summary must be text.')
        labels = ''.join(f'<li>{esc(s["label"])}</li>' for s in story['scenarios'])
        cards.append(f'<article><span class="number">{len(cards)+1:02d} / WALKTHROUGH</span><h2><a href="{ident}.html">{esc(story["title"])}</a></h2><p>{esc(summary)}</p><ul>{labels}</ul><a class="open" href="{ident}.html">Explore {len(story["scenarios"])} scenarios →</a></article>')
    notes = ''.join(f'<li>{esc(note)}</li>' for note in limitations)
    pages['index.html'] = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>''' + esc(manifest['title']) + '''</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{background:#101517;color:#eff4ef;font:15px/1.7 system-ui,sans-serif;margin:0}main{max-width:1220px;margin:auto;padding:35px 28px}header{border-bottom:1px solid #35423f;padding-bottom:22px;display:flex;justify-content:space-between;color:#c6f27c}h1{font-size:clamp(32px,5vw,58px);letter-spacing:-2px;line-height:1.15;margin:40px 0 20px}h2{font-size:22px;line-height:1.4}p,li{color:#a9bcbc}a{color:inherit;text-decoration:none}a:hover{text-decoration:underline}a:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid #c6f27c;outline-offset:5px}.intro{max-width:850px;font-size:18px}.stats{display:flex;gap:32px;margin:25px 0;color:#c6f27c}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px;margin-top:25px}article{background:#182124;border:1px solid #344447;border-radius:14px;padding:25px;display:flex;flex-direction:column;min-width:0}article[hidden]{display:none}article ul{padding-left:18px;font-size:13px}.number{font:11px ui-monospace,monospace;letter-spacing:2px;color:#c6f27c}.open{color:#c6f27c;margin-top:auto;padding-top:18px}input{width:100%;background:#1a2528;border:1px solid #465b60;border-radius:9px;padding:13px 15px;color:#fff;font:inherit}details{margin:30px 0;color:#a9bcbc}summary{cursor:pointer}footer{border-top:1px solid #35423f;margin-top:35px;padding-top:20px;color:#a9bcbc;font-size:12px}@media(max-width:450px){main{padding:22px 16px}.grid{grid-template-columns:1fr}.stats{gap:16px;flex-wrap:wrap}header{font-size:12px}}
</style></head><body><main><header><span>↗ diagram to motion</span><span>PROJECT EXECUTION ATLAS</span></header><h1>''' + esc(manifest['title']) + '''</h1><p class="intro">''' + esc(manifest['summary']) + f'''</p><div class="stats"><span>{len(demos)} walkthroughs</span><span>{scenario_count} scenarios</span><span>Offline · source-backed</span></div><label for="search">Find a flow or scenario</label><input id="search" type="search" placeholder="Try: MCP, retry, research, cancel…"><p id="matches" aria-live="polite"></p><section class="grid">''' + ''.join(cards) + '''</section><details open><summary>Scope and limitations</summary><p>''' + esc(manifest['scope']) + '''</p><ul>''' + notes + '''</ul></details><footer>Static source walkthroughs, not live execution traces. Animation speed is presentation pacing.</footer></main><script>const input=document.getElementById('search'),cards=[...document.querySelectorAll('article')];function filter(){const q=input.value.toLowerCase().trim();let count=0;for(const card of cards){card.hidden=!card.textContent.toLowerCase().includes(q);if(!card.hidden)count++;}document.getElementById('matches').textContent=count+' walkthroughs shown';}input.addEventListener('input',filter);filter();</script></body></html>'''
    # Embed complete pages so the bundle works when copied away from its source folder.
    payload = json.dumps({'title': manifest['title'], 'count': scenario_count,
                          'items': bundle_items,
                          'pages': {name[:-5]: page for name, page in pages.items()}}, ensure_ascii=True)
    payload = payload.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    template = (Path(__file__).resolve().parents[1] / 'assets/atlas-bundle.html').read_text(encoding='utf-8')
    pages['all-in-one.html'] = template.replace('__BUNDLE__', payload)
    # Validate every page and collision before writing any output.
    for name in pages:
        target = (out / name).resolve()
        require(target not in inputs, 'Output cannot overwrite a manifest input.')
        require(force or not target.exists(), f'{target.name} exists; use --force to rebuild.')
    out.mkdir(parents=True, exist_ok=True)
    for name, content in pages.items():
        (out / name).write_text(content, encoding='utf-8')
    return len(demos), scenario_count


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    try:
        count, scenarios = build_atlas(args.manifest, args.out, args.force)
        print(f'Built {count} walkthroughs / {scenarios} scenarios: {args.out / "index.html"}')
    except (ValueError, OSError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(1)
