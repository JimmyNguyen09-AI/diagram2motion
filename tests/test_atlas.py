import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from atlas import build_atlas
from build import load_graph, validate_story
from inventory import inventory


class AtlasTests(unittest.TestCase):
    def setUp(self):
        self.graph = load_graph(ROOT / 'examples/sequence.mmd')
        self.story = json.loads((ROOT / 'examples/sequence.story.json').read_text(encoding='utf-8'))
        for scenario in self.story['scenarios']:
            scenario.update(preconditions=['A valid request arrives.'], outcome='The result is returned.')
            for step in scenario['steps']:
                step['evidence'] = ['example.py:10 · handle_request']

    def write_inputs(self, path):
        (path / 'graph.json').write_text(json.dumps(self.graph), encoding='utf-8')
        (path / 'story.json').write_text(json.dumps(self.story), encoding='utf-8')
        manifest = {'title': 'Test atlas', 'summary': 'Two paths', 'scope': 'Synthetic fixture',
                    'demos': [{'id': 'example', 'diagram': 'graph.json', 'story': 'story.json'}]}
        (path / 'atlas.json').write_text(json.dumps(manifest), encoding='utf-8')
        return path / 'atlas.json'

    def test_alternative_graph_uses_its_own_edge_ids(self):
        variant = copy.deepcopy(self.graph)
        variant['edges'][0]['id'] = 'alternative'
        self.story['scenarios'][0]['graph'] = variant
        self.story['scenarios'][0]['steps'][0]['edge'] = 'alternative'
        validate_story(self.graph, self.story)
        del self.story['scenarios'][0]['graph']
        with self.assertRaisesRegex(ValueError, 'Unknown step edge'):
            validate_story(self.graph, self.story)

    def test_builds_index_and_evidenced_demo(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            manifest = self.write_inputs(path)
            self.assertEqual(build_atlas(manifest, path / 'site'), (1, 1))
            page = (path / 'site/example.html').read_text(encoding='utf-8')
            self.assertIn('example.py:10', page)
            self.assertIn('example.html', (path / 'site/index.html').read_text(encoding='utf-8'))
            with self.assertRaisesRegex(ValueError, 'exists'):
                build_atlas(manifest, path / 'site')

    def test_missing_evidence_fails_before_output(self):
        del self.story['scenarios'][0]['steps'][0]['evidence']
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            manifest = self.write_inputs(path)
            with self.assertRaisesRegex(ValueError, 'evidence'):
                build_atlas(manifest, path / 'site')
            self.assertFalse((path / 'site').exists())

    def test_rejects_escaping_input_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            manifest = self.write_inputs(path)
            data = json.loads(manifest.read_text())
            data['demos'][0]['diagram'] = '../outside.json'
            manifest.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'within'):
                build_atlas(manifest, path / 'site')

    def test_inventory_does_not_execute_or_read_dependencies(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / 'main.py').write_text('raise RuntimeError("Never execute me")\ndef handle():\n    pass\n')
            (path / '.env').write_text('SECRET=not-for-inventory')
            (path / 'node_modules').mkdir()
            (path / 'node_modules/a.py').write_text('def dependency(): pass')
            records = inventory(path)['files']
            self.assertEqual([r['file'] for r in records], ['main.py'])
            self.assertEqual(records[0]['symbols'][0]['name'], 'handle')


if __name__ == '__main__':
    unittest.main()
