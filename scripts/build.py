#!/usr/bin/env python3
"""Strict diagram importer and offline walkthrough builder. Python stdlib only."""
import argparse
import html
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ID = r"[A-Za-z_](?:[A-Za-z0-9_\-\.]*[A-Za-z0-9_])?"

CYLINDER = r'\[\(("[^"\n]*"|[^\[\](){{}}"\n]+)\)\]'
STADIUM = r'\(\[("[^"\n]*"|[^\[\](){{}}"\n]+)\]\)'
CIRCLE = r'\(\(("[^"\n]*"|[^\[\](){{}}"\n]+)\)\)'
RECT = r'\[("[^"\n]*"|[^\[\](){{}}"\n]+)\]'
ROUND = r'\(("[^"\n]*"|[^\[\](){{}}"\n]+)\)'
DIAMOND = r'\{("[^"\n]*"|[^\[\](){{}}"\n]+)\}'

NODE_SHAPES = rf'(?:{CYLINDER}|{STADIUM}|{CIRCLE}|{RECT}|{ROUND}|{DIAMOND})'
NODE = rf'({ID})(?:{NODE_SHAPES})?'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def plain_label(value):
    value = value.strip()
    return value[1:-1] if value.startswith('"') and value.endswith('"') else value


def parse_node_token(token):
    match = re.fullmatch(NODE, token.strip())
    require(match is not None, f'Unsupported node: {token}')
    ident, cylinder, stadium, circle, rect, rounded, diamond = match.groups()
    if cylinder is not None:
        shape, raw = 'cylinder', cylinder
    elif stadium is not None:
        shape, raw = 'stadium', stadium
    elif circle is not None:
        shape, raw = 'circle', circle
    elif rect is not None:
        shape, raw = 'rect', rect
    elif rounded is not None:
        shape, raw = 'round', rounded
    elif diamond is not None:
        shape, raw = 'diamond', diamond
    else:
        shape, raw = 'rect', ident
    return ident, plain_label(raw), shape


def split_edge_line(line):
    """Quote-aware arrow scanner supporting standard and labeled arrows."""
    in_quotes = False
    i = 0
    n = len(line)
    arrows = ['-.->', '==>', '<-->', '-->', '---', '->']
    arrow_pos = -1
    matched_arrow = None
    arrow_label = ""
    arrow_len = 0

    while i < n:
        ch = line[i]
        if ch == '"':
            in_quotes = not in_quotes
            i += 1
            continue
        if not in_quotes:
            if line[i:i+2] == '--' and line[i:i+3] not in ('-->', '---'):
                j = i + 2
                j_quotes = False
                found_end = False
                while j < n:
                    if line[j] == '"':
                        j_quotes = not j_quotes
                    elif not j_quotes:
                        if line[j:j+3] == '-->':
                            matched_arrow = '-->'
                            arrow_label = line[i+2:j].strip()
                            arrow_pos = i
                            arrow_len = (j + 3) - i
                            found_end = True
                            break
                        elif line[j:j+3] == '---':
                            matched_arrow = '---'
                            arrow_label = line[i+2:j].strip()
                            arrow_pos = i
                            arrow_len = (j + 3) - i
                            found_end = True
                            break
                    j += 1
                if found_end:
                    break

            for arr in arrows:
                if line[i:i+len(arr)] == arr:
                    matched_arrow = arr
                    arrow_pos = i
                    arrow_len = len(arr)
                    break
            if matched_arrow:
                break
        i += 1

    if not matched_arrow:
        return None

    left_part = line[:arrow_pos].strip()
    right_part = line[arrow_pos + arrow_len:].strip()

    if not arrow_label and right_part.startswith('|'):
        pipe_end = right_part.find('|', 1)
        if pipe_end != -1:
            arrow_label = right_part[1:pipe_end].strip()
            right_part = right_part[pipe_end + 1:].strip()

    return left_part, matched_arrow, arrow_label, right_part


def parse_nodes_list(part):
    """Split comma or & separated nodes outside of quotes."""
    tokens = []
    curr = []
    in_quotes = False
    for ch in part:
        if ch == '"':
            in_quotes = not in_quotes
            curr.append(ch)
        elif ch == '&' and not in_quotes:
            tokens.append(''.join(curr).strip())
            curr = []
        else:
            curr.append(ch)
    if curr:
        tokens.append(''.join(curr).strip())
    return [t for t in tokens if t]


def parse_mermaid(source):
    lines = []
    for i, line in enumerate(source.splitlines(), 1):
        s = line.strip().removesuffix(';').strip()
        if not s or s.startswith('%%'):
            continue
        if s.startswith('%%{') or s.startswith('classDef ') or s.startswith('class ') or s.startswith('style '):
            continue
        lines.append((i, s))

    require(bool(lines), 'Diagram is empty.')
    header = lines.pop(0)[1]
    flow = re.fullmatch(r'(?:flowchart|graph)\s+(LR|RL|TD|TB|BT)', header)
    require(flow or header == 'sequenceDiagram', 'Expected flowchart LR/TD/... or sequenceDiagram header.')
    direction = flow[1] if flow else 'LR'
    graph = dict(kind='flowchart' if flow else 'sequence', direction=direction,
                 source=source, nodes=[], edges=[], subgraphs=[])
    nodes = {}
    subgraphs = []
    subgraph_stack = []

    def register_node(token):
        ident, label, shape = parse_node_token(token)
        if ident not in nodes:
            nodes[ident] = dict(id=ident, label=ident, shape='rect')
        if label != ident or shape != 'rect':
            nodes[ident].update(label=label, shape=shape)
        if subgraph_stack:
            sub = subgraph_stack[-1]
            if ident not in sub['nodes']:
                sub['nodes'].append(ident)
        return ident

    for line_no, line in lines:
        try:
            if flow:
                if line.startswith('subgraph'):
                    sub_m = re.fullmatch(rf'subgraph\s+({ID})(?:\s*\[("[^"\n]*"|[^\[\]\n]+)\])?', line)
                    if sub_m:
                        sub_id = sub_m.group(1)
                        sub_lbl = plain_label(sub_m.group(2)) if sub_m.group(2) else sub_id
                    else:
                        sub_m2 = re.fullmatch(r'subgraph\s+("[^"\n]*"|[^\[\]\n]+)', line)
                        sub_id = f"sub_{len(subgraphs)+1}"
                        sub_lbl = plain_label(sub_m2.group(1)) if sub_m2 else line.removeprefix('subgraph').strip()
                    sub_obj = dict(id=sub_id, label=sub_lbl, nodes=[])
                    subgraphs.append(sub_obj)
                    subgraph_stack.append(sub_obj)
                    continue
                if line == 'end':
                    if subgraph_stack:
                        subgraph_stack.pop()
                    continue
                if line.startswith('direction '):
                    # Direction inside subgraph
                    continue

                edge_split = split_edge_line(line)
                if edge_split:
                    left_str, arrow, label, right_str = edge_split
                    left_tokens = parse_nodes_list(left_str)
                    right_tokens = parse_nodes_list(right_str)
                    style = 'dashed' if arrow == '-.->' else 'thick' if arrow == '==>' else 'solid'
                    is_undirected = arrow == '---'
                    for lt in left_tokens:
                        u = register_node(lt)
                        for rt in right_tokens:
                            v = register_node(rt)
                            edge_dict = dict(id=f"e{len(graph['edges'])+1}", **{'from': u, 'to': v},
                                             label=plain_label(label) if label else '', style=style)
                            if is_undirected:
                                edge_dict['directed'] = False
                            graph['edges'].append(edge_dict)
                else:
                    register_node(line)
            else:
                if line.startswith('autonumber') or line.startswith('title'):
                    continue
                if line.startswith('Note '):
                    graph.setdefault('notes', []).append(line)
                    continue
                participant = re.fullmatch(rf'(participant|actor)\s+({ID})(?:\s+as\s+(.+))?', line)
                message = re.fullmatch(rf'({ID})\s*(-->>|->>|-->|->)\s*({ID})\s*:\s*(.+)', line)
                if participant:
                    ident = register_node(participant[2])
                    nodes[ident]['label'] = plain_label(participant[3] or ident)
                elif message:
                    u, arrow, v, text = message.groups()
                    style = 'dashed' if arrow in ('-->>', '-->') else 'solid'
                    graph['edges'].append(dict(id=f"e{len(graph['edges'])+1}", **{'from': register_node(u), 'to': register_node(v)},
                                               label=text.strip(), style=style))
                else:
                    raise ValueError(f'Unsupported sequence statement: {line}')
        except ValueError as exc:
            raise ValueError(f'Line {line_no}: {exc}. See references/format.md.') from exc

    graph['nodes'] = list(nodes.values())
    if subgraphs:
        graph['subgraphs'] = subgraphs
    validate_graph(graph)
    return graph


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def auto_layout(graph):
    """Compute layered DAG topological positions for flowchart nodes."""
    if graph.get('kind') != 'flowchart':
        return
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    if not nodes:
        return
    if all('x' in n and 'y' in n for n in nodes):
        return

    node_ids = [n['id'] for n in nodes]
    succ = {nid: [] for nid in node_ids}
    pred = {nid: [] for nid in node_ids}
    for e in edges:
        u, v = e.get('from'), e.get('to')
        if u and v and u != v and u in succ and v in pred:
            succ[u].append(v)
            pred[v].append(u)

    roots = [nid for nid in node_ids if len(pred[nid]) == 0]
    if not roots:
        roots = [node_ids[0]]

    ranks = {nid: 0 for nid in roots}
    queue = list(roots)
    visited_edges = set()
    while queue:
        u = queue.pop(0)
        curr_rank = ranks[u]
        for v in succ[u]:
            edge_key = (u, v)
            if edge_key in visited_edges:
                continue
            visited_edges.add(edge_key)
            if v not in ranks:
                ranks[v] = curr_rank + 1
                queue.append(v)
            elif ranks[v] < curr_rank + 1 and ranks[v] != 0:
                ranks[v] = curr_rank + 1
                queue.append(v)

    for nid in node_ids:
        if nid not in ranks:
            ranks[nid] = 0

    max_rank = max(ranks.values()) if ranks else 0
    layers = [[] for _ in range(max_rank + 1)]
    for n in nodes:
        layers[ranks[n['id']]].append(n)

    direction = graph.get('direction', 'LR')
    is_vertical = direction in ('TD', 'TB', 'BT')
    is_reverse = direction in ('RL', 'BT')
    max_layer_size = max(len(layer) for layer in layers) if layers else 1

    for r_idx, layer in enumerate(layers):
        effective_rank = (max_rank - r_idx) if is_reverse else r_idx
        layer_size = len(layer)
        for i, n in enumerate(layer):
            offset = (max_layer_size - layer_size) * 0.5
            pos_in_layer = (i + offset)
            if is_vertical:
                n['x'] = int(160 + pos_in_layer * 260)
                n['y'] = int(120 + effective_rank * 180)
            else:
                n['x'] = int(160 + effective_rank * 320)
                n['y'] = int(120 + pos_in_layer * 160)


def validate_graph(graph):
    require(isinstance(graph, dict), 'Graph must be an object.')
    require(graph.get('kind') in ('flowchart', 'sequence'), 'Graph kind must be flowchart or sequence.')
    require(graph.get('direction', 'LR') in ('LR', 'RL', 'TD', 'TB', 'BT'), 'Invalid direction.')
    require(isinstance(graph.get('source', ''), str), 'Graph source must be text.')
    nodes, edges = graph.get('nodes'), graph.get('edges')
    require(isinstance(nodes, list) and bool(nodes), 'Graph needs nodes.')
    require(isinstance(edges, list) and bool(edges), 'Graph needs at least one edge.')
    require(all(isinstance(n, dict) for n in nodes + edges), 'Nodes and edges must be objects.')
    for items, name in ((nodes, 'node'), (edges, 'edge')):
        ids = [item.get('id') for item in items]
        require(all(isinstance(i, str) and re.fullmatch(ID, i) for i in ids), f'Invalid {name} ID.')
        require(len(ids) == len(set(ids)), f'Duplicate {name} IDs.')
    ids = {n['id'] for n in nodes}
    for n in nodes:
        require(nonempty(n.get('label')), f"Node {n['id']} needs a label.")
        require(n.get('shape', 'rect') in ('rect', 'round', 'diamond', 'cylinder', 'stadium', 'circle'), 'Invalid node shape.')
    coords = [k in n for n in nodes for k in ('x', 'y')]
    require(all(coords) or not any(coords), 'Supply both x/y for every node, or no coordinates.')
    if any(coords):
        for n in nodes:
            require(all(type(n[k]) in (int, float) and math.isfinite(n[k]) and 100 <= n[k] <= 20000 for k in ('x', 'y')),
                    'Coordinates must be finite numbers between 100 and 20000.')
    for e in edges:
        require(isinstance(e.get('from'), str) and e['from'] in ids and isinstance(e.get('to'), str) and e['to'] in ids,
                f"Edge {e['id']} references a missing node.")
        require(isinstance(e.get('label', ''), str), 'Edge labels must be text.')
        require(e.get('style', 'solid') in ('solid', 'dashed', 'thick'), 'Invalid edge style.')
    if 'subgraphs' in graph:
        require(isinstance(graph['subgraphs'], list), 'Subgraphs must be a list.')
        for sub in graph['subgraphs']:
            require(isinstance(sub, dict) and nonempty(sub.get('id')) and nonempty(sub.get('label')), 'Subgraph needs id and label.')
            require(isinstance(sub.get('nodes', []), list), 'Subgraph nodes must be a list of node IDs.')


def validate_story(graph, story):
    require(isinstance(story, dict) and nonempty(story.get('title')), 'Story needs a title.')
    require('TODO' not in story.get('title', ''), 'Story title contains unedited placeholder TODO.')
    for key in ('subtitle', 'language'):
        require(isinstance(story.get(key, ''), str), f'{key} must be text.')
    require(isinstance(story.get('assumptions', []), list) and all(nonempty(a) for a in story.get('assumptions', [])),
            'Assumptions must be a list of nonempty strings.')
    scenarios = story.get('scenarios')
    require(isinstance(scenarios, list) and bool(scenarios), 'Story needs scenarios.')
    seen = set()
    for s_idx, scenario in enumerate(scenarios):
        require(isinstance(scenario, dict), f"Scenario {s_idx+1} must be an object.")
        scenario_graph = scenario.get('graph', graph)
        validate_graph(scenario_graph)
        edge_ids = {e['id'] for e in scenario_graph['edges']}
        ident = scenario.get('id')
        require(nonempty(ident) and ident not in seen, f"Scenario {s_idx+1}: ID must be nonempty and unique.")
        seen.add(ident)
        require(nonempty(scenario.get('label')), f"Scenario '{ident}': label must be nonempty.")
        require('TODO' not in str(scenario.get('label', '')), f"Scenario '{ident}': label contains unedited placeholder TODO.")
        require(isinstance(scenario.get('description', ''), str), f"Scenario '{ident}': description must be text.")
        require('TODO' not in str(scenario.get('description', '')), f"Scenario '{ident}': description contains unedited placeholder TODO.")
        if 'preconditions' in scenario:
            require(isinstance(scenario['preconditions'], list), f"Scenario '{ident}': preconditions must be a list.")
            for p in scenario['preconditions']:
                require(nonempty(p), f"Scenario '{ident}': precondition must be nonempty.")
                require('TODO' not in p, f"Scenario '{ident}': precondition contains unedited placeholder TODO.")
        if 'outcome' in scenario:
            require(isinstance(scenario['outcome'], str), f"Scenario '{ident}': outcome must be text.")
            require('TODO' not in scenario['outcome'], f"Scenario '{ident}': outcome contains unedited placeholder TODO.")
        steps = scenario.get('steps')
        require(isinstance(steps, list) and bool(steps), f"Scenario '{ident}' needs steps.")
        for step_idx, step in enumerate(steps):
            require(isinstance(step, dict), f"Scenario '{ident}', step {step_idx+1} must be an object.")
            require(isinstance(step.get('edge'), str) and step['edge'] in edge_ids,
                    f"Scenario '{ident}', step {step_idx+1}: Unknown step edge '{step.get('edge')}'.")
            require(nonempty(step.get('title')), f"Scenario '{ident}', step {step_idx+1}: step needs a title.")
            require('TODO' not in step['title'], f"Scenario '{ident}', step {step_idx+1}: title contains unedited placeholder TODO.")
            require(nonempty(step.get('detail')), f"Scenario '{ident}', step {step_idx+1}: step needs detail.")
            require('TODO' not in step['detail'], f"Scenario '{ident}', step {step_idx+1}: detail contains unedited placeholder TODO.")
            if 'evidence' in step:
                require(isinstance(step['evidence'], list), f"Scenario '{ident}', step {step_idx+1}: step evidence must be a list.")
                for e in step['evidence']:
                    if isinstance(e, dict):
                        require(nonempty(e.get('file')) and nonempty(e.get('symbol')),
                                f"Scenario '{ident}', step {step_idx+1}: evidence object needs file and symbol.")
                        require('TODO' not in str(e.get('file')) and 'TODO' not in str(e.get('symbol')),
                                f"Scenario '{ident}', step {step_idx+1}: evidence contains unedited placeholder TODO.")
                    else:
                        require(nonempty(e), f"Scenario '{ident}', step {step_idx+1}: step evidence must be nonempty strings or objects.")
                        require('TODO' not in e, f"Scenario '{ident}', step {step_idx+1}: evidence contains unedited placeholder TODO.")
            if 'predicate' in step:
                require(isinstance(step['predicate'], str), f"Scenario '{ident}', step {step_idx+1}: predicate must be text.")
                require('TODO' not in step['predicate'], f"Scenario '{ident}', step {step_idx+1}: predicate contains unedited placeholder TODO.")
            if 'dev_context' in step:
                require(isinstance(step['dev_context'], dict), f"Scenario '{ident}', step {step_idx+1}: dev_context must be an object.")
            require(step.get('kind', 'call') in (
                'call', 'return', 'decision', 'retry', 'parallel', 'persist',
                'stream', 'failure', 'db_query', 'mcp_tool', 'event_publish', 'error'
            ), f"Scenario '{ident}', step {step_idx+1}: invalid step kind '{step.get('kind')}'.")
            duration = step.get('duration_ms', 1800)
            require(type(duration) is int and 300 <= duration <= 15000,
                    f"Scenario '{ident}', step {step_idx+1}: duration_ms must be an integer from 300 to 15000.")
    if 'positions' in story:
        positions = story['positions']
        require(isinstance(positions, dict) and set(positions) == {n['id'] for n in graph['nodes']}, 'Positions must cover exactly all node IDs.')
        for n in graph['nodes']:
            xy = positions[n['id']]
            require(isinstance(xy, list) and len(xy) == 2, 'Each position must be [x,y].')
            n['x'], n['y'] = xy
        validate_graph(graph)
    if graph['kind'] == 'flowchart' and all('x' in n for n in graph['nodes']):
        positions = {(n['x'], n['y']) for n in graph['nodes']}
        require(len(positions) == len(graph['nodes']), 'Flowchart node centers must be distinct.')


def load_graph(path):
    source = path.read_text(encoding='utf-8-sig')
    graph = json.loads(source) if path.suffix.lower() == '.json' else parse_mermaid(source)
    validate_graph(graph)
    return graph


def render(graph, story):
    validate_graph(graph)
    validate_story(graph, story)
    auto_layout(graph)
    for s in story.get('scenarios', []):
        if 'graph' in s:
            auto_layout(s['graph'])
    payload = json.dumps(dict(graph=graph, story=story), ensure_ascii=False).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    template = (ROOT / 'assets' / 'viewer.html').read_text(encoding='utf-8')
    replacements = {'__PAGE_TITLE__': html.escape(story['title']), '__LANG__': html.escape(story.get('language') or 'en', quote=True), '__PAYLOAD__': payload}
    return re.sub(r'__PAGE_TITLE__|__LANG__|__PAYLOAD__', lambda match: replacements[match[0]], template)


def scaffold_story(graph):
    """Generate a starter developer-grade story template with explicit TODO placeholders."""
    edges = graph.get('edges', [])
    happy_steps = []
    for e in edges:
        happy_steps.append({
            "edge": e['id'],
            "title": f"Traverse {e.get('from')} → {e.get('to')}",
            "detail": "TODO: describe the mechanism and why this step occurs",
            "kind": "call",
            "predicate": "TODO: specify exact branch condition",
            "dev_context": {
                "protocol": "TODO: REST / gRPC / SQL / Redis / etc.",
                "request_payload": {},
                "response_payload": {}
            },
            "evidence": ["TODO: <file_path>:<line_number> · <symbol_name>"]
        })
    return {
        "title": "Architecture Walkthrough",
        "subtitle": "Interactive developer execution atlas",
        "language": "en",
        "assumptions": ["Pacing illustrates logical order, not measured latency."],
        "scenarios": [
            {
                "id": "happy-path",
                "label": "Standard Request Flow",
                "description": "TODO: summarize what this scenario accomplishes.",
                "preconditions": ["TODO: specify request preconditions."],
                "outcome": "TODO: describe terminal outcome.",
                "steps": happy_steps
            }
        ]
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('inspect', 'validate', 'build', 'scaffold'):
        cmd = sub.add_parser(name)
        cmd.add_argument('diagram', type=Path)
        if name in ('validate', 'build'):
            cmd.add_argument('--story', type=Path, required=True)
        if name in ('build', 'scaffold'):
            cmd.add_argument('--out', type=Path, required=True)
            cmd.add_argument('--force', action='store_true')
    args = parser.parse_args(argv)
    try:
        graph = load_graph(args.diagram)
        if args.command == 'inspect':
            auto_layout(graph)
            print(json.dumps(graph, ensure_ascii=False, indent=2))
            return 0
        if args.command == 'scaffold':
            scaffold = scaffold_story(graph)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open('w' if args.force else 'x', encoding='utf-8') as f:
                json.dump(scaffold, f, indent=2, ensure_ascii=False)
            print(f'Scaffolded story template to {args.out}.')
            return 0
        story = json.loads(args.story.read_text(encoding='utf-8-sig'))
        validate_story(graph, story)
        if args.command == 'build':
            require(args.out.resolve() not in (args.diagram.resolve(), args.story.resolve()), 'Output cannot overwrite an input file.')
            output = render(graph, story)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open('w' if args.force else 'x', encoding='utf-8') as file:
                file.write(output)
            print(f'Built {args.out} ({len(story["scenarios"])} scenarios).')
        else:
            print(f'Valid: {len(graph["nodes"])} nodes, {len(graph["edges"])} edges, {len(story["scenarios"])} scenarios.')
        return 0
    except (ValueError, OSError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    # Emit consistent UTF-8 JSON even when Windows pipes use a legacy code page.
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    sys.exit(main())
