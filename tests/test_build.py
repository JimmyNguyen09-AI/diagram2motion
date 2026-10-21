import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('builder', ROOT / 'scripts/build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.graph = builder.load_graph(ROOT / 'examples/cache.mmd')
        self.story = json.loads((ROOT / 'examples/cache.story.json').read_text(encoding='utf-8'))

    def test_flowchart_preserves_topology_shapes_and_unicode(self):
        graph = builder.parse_mermaid('flowchart LR\n A("Client \u2603") -->|request| B{Ready?}\n B -.-> A\n')
        self.assertEqual(graph['nodes'][0]['label'], 'Client \u2603')
        self.assertEqual(graph['nodes'][1]['shape'], 'diamond')
        self.assertEqual([(e['from'], e['to']) for e in graph['edges']], [('A', 'B'), ('B', 'A')])
        self.assertEqual(graph['edges'][1]['style'], 'dashed')

    def test_sequence_keeps_self_and_return_messages(self):
        graph = builder.load_graph(ROOT / 'examples/sequence.mmd')
        self.assertEqual(graph['edges'][2]['from'], graph['edges'][2]['to'])
        self.assertEqual(graph['edges'][-1]['to'], 'Client')
        self.assertEqual(graph['edges'][-1]['style'], 'dashed')

    def test_unsupported_syntax_is_not_silently_dropped(self):
        for source in ['flowchart LR\nA --> B --> C', 'sequenceDiagram\nalt failure\nA->>B: Hi\nend',
                       'sequenceDiagram\npar parallel\nA->>B: Hi\nend']:
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, 'Line'):
                builder.parse_mermaid(source)

    def test_subgraphs_and_developer_shapes_supported(self):
        source = (
            "%%{init: {}}%%\n"
            "flowchart LR\n"
            "subgraph Storage [\"Database Tier\"]\n"
            "  db[(\"Postgres Database\")]\n"
            "  q([\"Kafka Stream\"])\n"
            "  ev((Event))\n"
            "end\n"
            "web-app --> |GET /items| db\n"
            "db -.-> |replicate| q\n"
        )
        graph = builder.parse_mermaid(source)
        self.assertEqual(len(graph['subgraphs']), 1)
        self.assertEqual(graph['subgraphs'][0]['label'], 'Database Tier')
        shapes = {n['id']: n['shape'] for n in graph['nodes']}
        self.assertEqual(shapes['db'], 'cylinder')
        self.assertEqual(shapes['q'], 'stadium')
        self.assertEqual(shapes['ev'], 'circle')
        self.assertIn('web-app', shapes)

    def test_scaffold_and_developer_context(self):
        scaffold = builder.scaffold_story(self.graph)
        # Verify unedited scaffold with TODO is rejected
        with self.assertRaisesRegex(ValueError, 'TODO'):
            builder.validate_story(self.graph, scaffold)

        # Fill in placeholders with valid content
        scaffold['scenarios'][0]['description'] = 'Standard flow without errors'
        scaffold['scenarios'][0]['preconditions'] = ['Cache and DB are online']
        scaffold['scenarios'][0]['outcome'] = 'Response delivered'
        for step in scaffold['scenarios'][0]['steps']:
            step['detail'] = 'Valid step detail explanation'
            step['predicate'] = 'cache_miss == True'
            step['evidence'] = ['app/cache.py:10 · get_cached']
            step['dev_context'] = {'protocol': 'REST / HTTP'}
        builder.validate_story(self.graph, scaffold)

    def test_advanced_mermaid_syntax(self):
        source = (
            'flowchart LR\n'
            'A["pre-auth -> check"] -- calls --> B\n'
            'B --- C\n'
            'C & D --> E & F\n'
        )
        graph = builder.parse_mermaid(source)
        self.assertEqual(graph['nodes'][0]['label'], 'pre-auth -> check')
        # Check -- calls --> edge
        self.assertEqual(graph['edges'][0]['label'], 'calls')
        self.assertEqual(graph['edges'][0]['style'], 'solid')
        # Check undirected link ---
        self.assertEqual(graph['edges'][1]['directed'], False)
        # Check fan-out/fan-in C & D --> E & F (4 edges)
        fan_edges = [(e['from'], e['to']) for e in graph['edges'][2:]]
        self.assertEqual(fan_edges, [('C', 'E'), ('C', 'F'), ('D', 'E'), ('D', 'F')])

    def test_only_explicit_edges_can_be_animated(self):
        self.story['scenarios'][0]['steps'][0]['edge'] = 'invented_return_path'
        with self.assertRaisesRegex(ValueError, 'Unknown step edge'):
            builder.validate_story(self.graph, self.story)

    def test_alternative_paths_use_different_edges(self):
        builder.validate_story(self.graph, self.story)
        hit, miss = self.story['scenarios']
        self.assertNotIn('e4', [s['edge'] for s in hit['steps']])
        self.assertIn('e4', [s['edge'] for s in miss['steps']])

    def test_invalid_graph_and_story_contracts(self):
        for mutate in [lambda g: g['nodes'].append(copy.deepcopy(g['nodes'][0])),
                       lambda g: g['edges'][0].update(to='absent'),
                       lambda g: g['nodes'][0].update(x=100),
                       lambda g: g['edges'][0].update(style='unknown')]:
            graph = copy.deepcopy(self.graph)
            mutate(graph)
            with self.assertRaises(ValueError):
                builder.validate_graph(graph)
        for duration in [0, -1, 20000, True, '1800']:
            story = copy.deepcopy(self.story)
            story['scenarios'][0]['steps'][0]['duration_ms'] = duration
            with self.assertRaises(ValueError):
                builder.validate_story(self.graph, story)

    def test_coordinates_do_not_create_invalid_paths(self):
        self.story['positions']['API'] = self.story['positions']['Client']
        with self.assertRaisesRegex(ValueError, 'distinct'):
            builder.validate_story(self.graph, self.story)

    def test_json_embedding_is_inert_and_lossless(self):
        attack = '</script><script>window.pwned=true</script> __PAYLOAD__ & Unicode \u2603'
        self.story['title'] = attack
        self.graph['nodes'][0]['label'] = attack
        output = builder.render(self.graph, self.story)
        self.assertNotIn('</script><script>window.pwned', output)
        data = output.split('<script id="data" type="application/json">')[1].split('</script>')[0]
        self.assertEqual(json.loads(data)['story']['title'], attack)
        self.assertIn('&lt;/script&gt;', output)

    def test_repeated_edges_allowed_for_explicit_retries(self):
        self.story['scenarios'][0]['steps'].append(copy.deepcopy(self.story['scenarios'][0]['steps'][0]))
        builder.validate_story(self.graph, self.story)

    def test_inspect_emits_unicode_on_legacy_windows_code_page(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/build.py'), 'inspect', str(ROOT / 'examples/cache.mmd')],
                                env={**os.environ, 'PYTHONIOENCODING': 'cp1252'}, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout.decode('utf-8'))['nodes'][0]['label'], 'Client')

    def test_cli_refuses_overwrite_and_accepts_normalized_graph(self):
        with tempfile.TemporaryDirectory() as directory:
            graph_path = Path(directory) / 'graph.json'
            out = Path(directory) / 'walkthrough.html'
            graph_path.write_text(json.dumps(self.graph), encoding='utf-8')
            cmd = [sys.executable, str(ROOT / 'scripts/build.py'), 'build', str(graph_path), '--story', str(ROOT / 'examples/cache.story.json'), '--out', str(out)]
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            original = out.read_bytes()
            self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            self.assertEqual(out.read_bytes(), original)
            self.assertEqual(subprocess.run(cmd + ['--force'], capture_output=True).returncode, 0)


if __name__ == '__main__':
    unittest.main()
