"""Acceptance for the Vimeo VSL route, separate from the existing sales page."""
from html.parser import HTMLParser
from pathlib import Path
import json
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
VIDEO_SRC = 'https://player.vimeo.com/video/1244806219?badge=0&autopause=0&player_id=0&app_id=58479&autoplay=1&muted=1'
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
        frames = [a for t, a in tags.items if t == 'iframe']
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0]['src'], VIDEO_SRC)
        self.assertEqual(frames[0]['width'], '540')
        self.assertEqual(frames[0]['height'], '666')
        self.assertEqual(frames[0]['title'], 'VSL 1 - LumiVelle [47_31]')
        for permission in ['autoplay', 'fullscreen', 'picture-in-picture', 'clipboard-write', 'encrypted-media', 'web-share']:
            self.assertIn(permission, frames[0]['allow'])
        for cls in ['vsl-headline', 'vsl-video', 'vsl-cta__button', 'press__logos']:
            self.assertIn(cls, html)
        for old in ['vturb-smartplayer', 'converteai.net', 'cdn.nlabs.cloud', 'buygoods', 'assetsPath']:
            self.assertNotIn(old, html)
        buys = [a['href'] for t, a in tags.items if t == 'a' and 'buylink' in a.get('class', '')]
        self.assertEqual(buys, [CHECKOUT])
        for t, a in tags.items:
            if t == 'img':
                self.assertTrue(a['src'].endswith('.webp'))
            ref = a.get('src') if t in ['img', 'script'] else a.get('href') if t == 'link' and a.get('rel') == 'stylesheet' else None
            if ref and ref.startswith('/assets/'):
                self.assertTrue((ROOT / ref.lstrip('/')).is_file(), ref)
        config = json.loads((ROOT / 'vercel.json').read_text(encoding='utf-8'))
        self.assertTrue(config['cleanUrls'])
        csp = next(h['value'] for rule in config['headers'] if rule['source'] == '/(.*)' for h in rule['headers'] if h['key'] == 'Content-Security-Policy')
        directives = {part.strip().split()[0]: part.strip().split()[1:] for part in csp.split(';') if part.strip()}
        self.assertIn('https://player.vimeo.com', directives.get('frame-src', []))
        self.assertTrue(any(s.startswith('https://player.vimeo.com') for s in directives.get('script-src', [])))
        result = subprocess.run(['node', 'scripts/build.mjs'], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((ROOT / 'dist/vsl.html').read_bytes(), page.read_bytes())
        self.assertTrue((ROOT / 'dist/assets/vsl').is_dir())

if __name__ == '__main__':
    unittest.main()
