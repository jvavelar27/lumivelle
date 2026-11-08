"""Acceptance for the Wistia VSL route, separate from the existing sales page."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import json
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
MEDIA_ID = 'dr4rq15xr1'
CHECKOUT = 'https://order.wealthpay.io/qo52qotcz7vr?hid=b2lkPW9mZl82NDcxMDc5JmFpZD1hZmZfMjg3NzUxNCZ1aWQ9YmxfODY3NTQxMQ%3D%3D&affid=aff_2877514'

class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
    def handle_starttag(self, tag, attrs):
        self.items.append((tag, dict(attrs)))

class VslRouteAcceptance(unittest.TestCase):
    def test_published_vsl_uses_requested_video_and_original_layout(self):
        page = ROOT / 'vsl.html'
        self.assertTrue(page.is_file(), 'The /vsl route must have its own vsl.html, not replace index.html')
        html = page.read_text(encoding='utf-8')
        tags = Tags()
        tags.feed(html)
        players = [a for t, a in tags.items if t == 'wistia-player']
        self.assertEqual(len(players), 1, 'Use the supplied Wistia player instead of the Vimeo iframe')
        self.assertEqual(players[0]['media-id'], MEDIA_ID)
        self.assertEqual(players[0]['aspect'], '0.8126410835214447')
        self.assertEqual(players[0]['play-bar-control'], 'false')
        self.assertNotEqual(players[0].get('play-pause-control'), 'false')
        self.assertNotEqual(players[0].get('volume-control'), 'false')
        scripts = {a.get('src') for t, a in tags.items if t == 'script'}
        self.assertIn('https://fast.wistia.com/player.js', scripts)
        self.assertIn('https://fast.wistia.com/embed/dr4rq15xr1.js', scripts)
        self.assertIn('data-vdelay="2834"', html)
        for cls in ['vsl-headline', 'vsl-video', 'vsl-cta__button', 'press__logos']:
            self.assertIn(cls, html)
        for old in ['vturb-smartplayer', 'converteai.net', 'cdn.nlabs.cloud', 'buygoods', 'assetsPath', 'player.vimeo.com']:
            self.assertNotIn(old, html)
        buys = [a['href'] for t, a in tags.items if t == 'a' and 'buylink' in a.get('class', '')]
        self.assertEqual(buys, [CHECKOUT])
        for t, a in tags.items:
            if t == 'img':
                self.assertTrue(a['src'].endswith('.webp'))
            ref = a.get('src') if t in ['img', 'script'] else a.get('href') if t == 'link' and a.get('rel') == 'stylesheet' else None
            if ref and ref.startswith('/assets/'):
                self.assertTrue((ROOT / urlsplit(ref).path.lstrip('/')).is_file(), ref)
        config = json.loads((ROOT / 'vercel.json').read_text(encoding='utf-8'))
        self.assertTrue(config['cleanUrls'])
        csp = next(h['value'] for rule in config['headers'] if rule['source'] == '/(.*)' for h in rule['headers'] if h['key'] == 'Content-Security-Policy')
        directives = {part.strip().split()[0]: part.strip().split()[1:] for part in csp.split(';') if part.strip()}
        self.assertTrue(any(s.startswith('https://fast.wistia.com') for s in directives.get('script-src', [])))
        self.assertIn('https://embed-ssl.wistia.com', directives.get('media-src', []))
        self.assertIn('https://embed-ssl.wistia.com', directives.get('connect-src', []))
        result = subprocess.run(['node', 'scripts/build.mjs'], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((ROOT / 'dist/vsl.html').read_bytes(), page.read_bytes())
        self.assertTrue((ROOT / 'dist/assets/vsl').is_dir())

if __name__ == '__main__':
    unittest.main()
