"""Regression checks for the editorial image refresh."""
from html.parser import HTMLParser
from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
    def handle_starttag(self, name, attrs):
        self.items.append((name, dict(attrs)))

class EditorialImageAcceptance(unittest.TestCase):
    def setUp(self):
        self.html = (ROOT / 'index.html').read_text(encoding='utf-8')
        self.manifest = json.loads((ROOT / 'asset-manifest.json').read_text(encoding='utf-8'))
        self.tags = Tags()
        self.tags.feed(self.html)
    def test_new_editorial_assets_are_used_and_old_images_removed(self):
        expected = ['hero-editorial-v2.webp', 'lifestyle-editorial-v2.webp', 'pink-gelatin-editorial-v2.webp', 'kit-1-editorial-v2.webp', 'kit-2-editorial-v2.webp', 'kit-3-editorial-v2.webp']
        for filename in expected:
            self.assertIn('assets/' + filename, self.html)
            self.assertTrue((ROOT / 'assets' / filename).is_file())
        for filename in ['hero.webp', 'lifestyle.webp', 'pink-gelatin.webp', 'kit-2.webp', 'kit-3.webp', 'og-lumivelle.webp']:
            self.assertNotIn('assets/' + filename, self.html)
            self.assertFalse((ROOT / 'assets' / filename).exists(), f'Unused old image remains: {filename}')
    def test_generation_provenance_is_recoverable(self):
        self.assertEqual(self.manifest.get('generation_version'), 2)
        self.assertEqual(self.manifest.get('generator'), 'agent-image-generation / Luxin')
        generations = self.manifest.get('generations', [])
        self.assertEqual(len(generations), 4)
        for generation in generations:
            self.assertTrue(generation.get('job_id', '').startswith('job_'))
            self.assertTrue(generation.get('asset_id', '').startswith('image_'))
            self.assertIn(generation.get('model'), ['fal.nano-banana-pro-edit', 'openai.gpt-image-2'])
    def test_dimensions_and_files_match_manifest(self):
        by_path = {a['file']: a for a in self.manifest['assets']}
        for tag, a in self.tags.items:
            if tag != 'img':
                continue
            self.assertIn(a['src'], by_path)
            entry = by_path[a['src']]
            self.assertEqual(int(a['width']), entry['width'])
            self.assertEqual(int(a['height']), entry['height'])
            self.assertEqual((ROOT / entry['file']).stat().st_size, entry['bytes'])
        self.assertLessEqual(sum(a['bytes'] for a in by_path.values()), 1500000)
    def test_alt_text_matches_replacement_scene(self):
        lifestyle = [a for t, a in self.tags.items if t == 'img' and 'lifestyle-editorial-v2' in a.get('src', '')]
        self.assertEqual(len(lifestyle), 1)
        self.assertIn('window', lifestyle[0]['alt'].lower())
        self.assertNotIn('mirror', lifestyle[0]['alt'].lower())

if __name__ == '__main__':
    unittest.main()
